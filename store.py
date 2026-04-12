"""
store.py — simple local JSON storage
Data lives at ~/.workout_data.json
"""
import json
from pathlib import Path

DATA_PATH = Path.home() / ".workout_data.json"


def load_data():
    if DATA_PATH.exists():
        with open(DATA_PATH) as f:
            return json.load(f)
    return {"sessions": [], "current_meso": None}


def save_data(data):
    with open(DATA_PATH, "w") as f:
        json.dump(data, f, indent=2)
    return True
