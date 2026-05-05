"""
store.py — local JSON storage + migration for old meso formats
Data lives at ~/.workout_data.json
"""
import json
from pathlib import Path

DATA_PATH = Path.home() / ".workout_data.json"


def _migrate(data):
    """Patch saved data from older versions of the tracker."""
    meso = data.get("current_meso")
    if meso is None:
        return data

    # v1 PPL → v2 Upper/Lower: add missing day_index
    if "day_index" not in meso:
        sn = meso.get("session_number", meso.get("next_day_index", 0))
        meso["day_index"] = sn % 4

    # old RIR plans started at 3 — bump to cut protocol starting at 4
    if meso.get("rir_plan") and meso["rir_plan"][0] < 4:
        from workout import get_rir_plan
        meso["rir_plan"] = get_rir_plan(meso.get("total_weeks", 3))

    # ensure all exercise keys from the new split exist
    try:
        from workout import _build_exercise_state
        defaults = _build_exercise_state()
        es = meso.setdefault("exercise_state", {})
        for key, val in defaults.items():
            if key not in es:
                es[key] = val
    except Exception:
        pass

    return data


def load_data():
    if DATA_PATH.exists():
        with open(DATA_PATH) as f:
            data = json.load(f)
        return _migrate(data)
    return {"sessions": [], "current_meso": None}


def save_data(data):
    with open(DATA_PATH, "w") as f:
        json.dump(data, f, indent=2)
    return True
