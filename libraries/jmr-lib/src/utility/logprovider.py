from logging import Logger
import os
import logging.config
import yaml

def Setup(config_file):
    with open(config_file, 'r') as file:
         config = yaml.safe_load(file)
         logging.config.dictConfig(config)

def get_logger() -> Logger:
     return logging.getLogger('core_logger')

# get path of the script folder
script_dir = os.path.dirname(os.path.abspath(__file__))
print(f"Script dir: {script_dir}")
full_path = os.path.join(script_dir, './config.yaml')

Setup(full_path)
    