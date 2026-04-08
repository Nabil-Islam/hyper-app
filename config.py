"""
config.py — manages local config stored at ~/.workout_tracker_config.json
"""
import json
from pathlib import Path

CONFIG_PATH = Path.home() / ".workout_tracker_config.json"


def load_config():
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH) as f:
            return json.load(f)
    return None


def save_config(cfg):
    with open(CONFIG_PATH, "w") as f:
        json.dump(cfg, f, indent=2)


def setup_config():
    _hr()
    print("  FIRST-TIME SETUP")
    _hr()
    print("  You need a GitHub repo to store workout data,")
    print("  and a Personal Access Token with 'repo' scope.")
    print()
    print("  Create token at: https://github.com/settings/tokens")
    print()

    cfg = {}
    cfg["github_username"] = input("  GitHub username: ").strip()
    cfg["github_token"]    = input("  Personal access token: ").strip()
    cfg["github_repo"]     = input("  Repo name (e.g. my-workouts): ").strip()
    cfg["data_file"]       = "workout_data.json"

    save_config(cfg)
    print(f"\n  ✓ Config saved to {CONFIG_PATH}")
    _hr()
    return cfg


def _hr(char="─", width=50):
    print(char * width)
