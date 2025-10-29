import json

from types import SimpleNamespace

class SettingsReader():
    def __init__(self, path, to_merge = None):
        self.settings = self.read_and_set_settings(path)

        if to_merge:
            self.settings = self.merge_settings(to_merge, self.settings)

    def read_and_set_settings(self, path):
        with open(path, 'r', encoding='utf-8') as f:
            settings = json.load(f)
            settings = {item["key"]: item["value"] for item in settings}
            settings = SimpleNamespace(**settings)

        return settings   

    def merge_settings(self, ollama, module):
        ollama_dict = vars(ollama)
        dictmodule_dict = vars(module)

        merged = {**ollama_dict, **dictmodule_dict}

        return SimpleNamespace(**merged)
    
    def get_settings(self):
        return self.settings