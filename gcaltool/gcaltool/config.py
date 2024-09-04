import os
import json

def get_config_file():
    if os.name == 'nt':  # Windows
        config_path = os.path.join(os.getenv('APPDATA'), 'gcaltool')
    else:  # Linux/Unix
        config_path = os.path.expanduser('~/.config/gcaltool')
    
    os.makedirs(config_path, exist_ok=True)
    return os.path.join(config_path, 'config.json')

def load_config():
    config_file = get_config_file()
    if os.path.exists(config_file):
        with open(config_file, 'r') as file:
            return json.load(file)
    return {}

def save_config(config):
    config_file = get_config_file()
    with open(config_file, 'w') as file:
        json.dump(config, file)
