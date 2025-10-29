from ollama import Client

import copy
import time

import re

#SQLite CACHE
import sqlite3
import hashlib
import pickle

#CLASSES
from SettingsReader import SettingsReader

class OllamaWrapper():
    def __init__(self):
        settings_reader = SettingsReader("./ollama_wrapper_settings.json")
        self.settings = settings_reader.get_settings()

        self.client = Client(host=self.settings.OLLAMA_API_URL)

        #CACHE
        self.init_cache_db()
    
    def is_contains_chinese(self, text):
        return bool(re.search(r'[\u4e00-\u9fff]', text))

    #INIT THE DATABASE
    def init_cache_db(self):
        with sqlite3.connect(self.settings.DB_CACHE_PATH) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS responses (
                    model TEXT,
                    options TEXT,
                    system TEXT,
                    prompt TEXT,
                    response TEXT,
                    is_bad_request INTEGER,
                    hash TEXT PRIMARY KEY,
                    timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
                    duration INTEGER
                )
            """)

    def make_hash(self, *args):
        return hashlib.sha256(pickle.dumps(args)).hexdigest()
        
    def get_response_from_cache(self, model, options, prompt, system):
        cleared_options = copy.deepcopy(options)

        for key in ['num_gpu', 'num_batch', 'num_thread', 'use_nmap']:
            cleared_options.pop(key, None)

        key_hash = self.make_hash(model, cleared_options, prompt, system)

        with sqlite3.connect(self.settings.DB_CACHE_PATH) as conn:
            cursor = conn.cursor()

            # CHECK THE RESPONSE IN CACHE
            cursor.execute("SELECT response, is_bad_request FROM responses WHERE hash = ?", (key_hash,))
            row = cursor.fetchone()

            if row:
                #IF FOUND – GET FROM CACHE
                response = row[0]
                is_bad_request = bool(row[1])
            else:
                response = False
                is_bad_request = False

            conn.commit()

            return key_hash, response, is_bad_request
            
    def save_response_to_cache(self, model, options, system, prompt, response, is_bad_request, key_hash, duration):
        with sqlite3.connect(self.settings.DB_CACHE_PATH) as conn:
            cursor = conn.cursor()

            cursor.execute(
                "INSERT or REPLACE INTO responses (model, options, system, prompt, response, is_bad_request, hash, duration) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (str(model), str(options), str(system), str(prompt), str(response), int(is_bad_request), key_hash, duration),
            )

            conn.commit()

    def request(self, prompt, model, system, num_ctx, options, save_to_cache = True):
        #MAKE FIRST REQUEST
        response, options, is_bad_request = self._request(prompt, model, system, num_ctx, options, save_to_cache)

        # IF BAD — REGENERATE
        while is_bad_request:
            new_options = copy.deepcopy(options)

            #MODIFY THE SEED
            new_options["seed"] = options["seed"] + 1

            response, options, is_bad_request = self._request(prompt, model, system, num_ctx, new_options, save_to_cache)

        return response
    
    def is_response_stream_have_errors(self, text):
        if self.is_contains_chinese(text):
            return True
        
    def is_all_response_have_errors(self, text):
        if len(text) == 0:
            return True

    def _request(self, prompt, model, system, num_ctx, options, save_to_cache = True):
        is_bad_request = False

        data = {
            "text" : "",
            "items" : []
        }

        #TRY GET RESPONSE FROM CACHE
        key_hash, cache_response, is_bad_request = self.get_response_from_cache(model, options, prompt, system)

        #IF IT THERE — JUST RETURN FROM CACHE
        if cache_response:
            response = self.postprocess_response(cache_response)

            data["text"] = response
            data["items"] = response.split()
        else:
            try:
                request_options = copy.deepcopy(options)
                response_start_time = time.perf_counter()

                response = self.client.generate(
                    model = model, 
                    prompt = prompt,
                    system = system,
                    options = request_options,
                    stream = True,
                    keep_alive = -1
                )

                #GET IT AS STREAM TO CHECK IT ON GOING
                for item in response:
                    if len(item["response"]) == 0:
                        continue

                    text = item["response"]

                    #COllECT RESPONSE ON GOING
                    data["text"] += text
                    data["items"].append(text)

                    # THIS IS OUR CHECKS
                    is_bad_request = self.is_response_stream_have_errors(data["text"])
            
                    if is_bad_request:
                        break
            except:
                is_bad_request = True

            response_end_time = time.perf_counter()
            response_duration = round(response_end_time - response_start_time)

            # POST CHECK RESPONSE
            if self.is_all_response_have_errors(data["text"]):
                is_bad_request = True

            #SAVE RESPONSE TO CACHE
            if (len(data["text"]) > 0 or is_bad_request) and save_to_cache:
                self.save_response_to_cache(model, options, system, prompt, data["text"], is_bad_request, key_hash, response_duration)

        return response, options, is_bad_request