"""Configuration for livecode.

The config file can be specified using envionment variable
FALCON_CONFIG_FILE.

A sample config file config_sample.yml is provided in the repo.
"""
import os
import yaml

DEFAULT_CONFIG = {
    "runtimes": {
        "python": {
            "image": "python:3.11-slim",
            "command": ["python", "/app/main.py"],
            "code_filename": "main.py"
        },

        "javascript": {
            "image": "node:20-alpine",
            "command": ["node", "/app/main.js"],
            "code_filename": "main.js"
        },

        "rust": {
            "image": "rust:latest",
            "command": ["bash", "-c", "rustc /app/main.rs && /app/main"],
            "code_filename": "main.rs"
        },

        "golang": {
            "image": "golang:1.22",
            "command": ["go", "run", "/app/main.go"],
            "code_filename": "main.go"
        },

        "c": {
            "image": "gcc:latest",
            "command": ["bash", "-c", "gcc /app/main.c -o /app/main && /app/main"],
            "code_filename": "main.c"
        },

        "cpp": {
            "image": "gcc:latest",
            "command": ["bash", "-c", "g++ /app/main.cpp -o /app/main && /app/main"],
            "code_filename": "main.cpp"
        }
    }
}

def read_config():
    config_file = os.getenv("FALCON_CONFIG_FILE")
    if config_file:
        return yaml.safe_load(open(config_file))
    else:
        return {}

CONFIG = read_config()

def _get_runtime(config, name):
    return config.get('runtimes', {}).get(name)

def get_runtime(name):
    return _get_runtime(CONFIG, name) or _get_runtime(DEFAULT_CONFIG, name)

def has_runtime(name):
    return get_runtime(name) is not None
