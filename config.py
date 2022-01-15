import json

global CONFIG

with open("settings.json") as config_file:
    CONFIG = json.load(config_file)
