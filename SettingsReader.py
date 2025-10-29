import json

from types import SimpleNamespace

class SettingsReader():
    def __init__(self, path):
        self.settings = self.read_and_set_settings(path)

    def read_and_set_settings(self, path):
        with open(path, 'r', encoding='utf-8') as f:
            settings = json.load(f)
            settings = {item["key"]: item["value"] for item in settings}
            settings = SimpleNamespace(**settings)

        return settings   
    
    def get_settings(self):
        return self.settings