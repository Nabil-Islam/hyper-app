"""
workout.py — mesocycle logic, session structure, biofeedback, progression

Audited against RP / hypertrophy science principles:
  - RIR-based mesocycle with deload ✓
  - Biofeedback = empirical MEV→MAV→MRV detection ✓
  - Myo-rep match for small muscles ✓
  - Synergist pairing (push+tri, pull+bi) ✓
  - Rear delt added to all shoulder sessions (health + balance) ✓
  - Deload reduces both sets AND weight (RP standard) ✓
  - Squat rep range widened to 6-12 for hypertrophy focus ✓

Session structure:
  Each session = 1 compound + 1–2 isolations
  Compounds : Push → Pull → Legs(Sq) → Push → Pull → Legs(SLDL) → repeat
  Isolations: Tricep | Bicep | Forearm rotate on even sessions
              Lateral Raise + Rear Delt paired on odd (shoulder) sessions
  → Shoulder sessions are the only 3-exercise sessions (still short)
"""
from datetime import date

# ── Volume landmarks (RP reference, sets/muscle/week) ─────────────────────────
# Used only for informational display
VOLUME_LANDMARKS = {
    "chest":      {"mev": 6,  "mav": 16, "mrv": 22},
    "back":       {"mev": 8,  "mav": 18, "mrv": 25},
    "quads":      {"mev": 6,  "mav": 16, "mrv": 20},
    "hamstrings": {"mev": 4,  "mav": 12, "mrv": 16},
    "biceps":     {"mev": 6,  "mav": 14, "mrv": 20},
    "triceps":    {"mev": 6,  "mav": 14, "mrv": 20},
    "shoulders":  {"mev": 6,  "mav": 16, "mrv": 22},
    "rear_delts": {"mev": 6,  "mav": 16, "mrv": 22},
    "forearms":   {"mev": 4,  "mav": 10, "mrv": 14},
}

# ── Set counts ────────────────────────────────────────────────────────────────
INITIAL_SETS = {"compound": 1, "isolation": 2}

# ── Compound rotation ─────────────────────────────────────────────────────────
COMPOUND_CYCLE = ["push", "pull", "legs", "push", "pull", "legs"]

COMPOUND_TEMPLATES = {
    "push": {
        "slot": "Push",
        "default": "Barbell Bench Press",
        "muscle": "chest",
        # Bench has limited chest stretch; good for overall strength driver.
        # If adding a second chest exercise later, a fly/cable cross gives
        # the stretch stimulus RP research emphasises for chest hypertrophy.
        "rep_range": "8-12",
        "incr": 2.5,
        "myo": False,
    },
    "pull": {
        "slot": "Pull",
        "default": "Barbell Row",
        "muscle": "back",
        "rep_range": "6-10",
        "incr": 2.5,
        "myo": False,
    },
    "legs_squat": {
        "slot": "Legs (Squat)",
        "default": "Squat",
        "muscle": "quads",
        # Widened from 5-8: RP recommends 8-15 for quad hypertrophy.
        # Low-rep squats skew neural/strength; more reps = more hypertrophic
        # stimulus per set with lower systemic fatigue.
        "rep_range": "6-12",
        "incr": 2.5,
        "myo": False,
    },
    "legs_sldl": {
        "slot": "Legs (SLDL)",
        "default": "Stiff-Leg Deadlift",
        "muscle": "hamstrings",
        "rep_range": "6-10",
        "incr": 2.5,
        "myo": False,
    },
}

# ── Isolation templates ───────────────────────────────────────────────────────
NON_SHOULDER_ISO_CYCLE = ["tricep", "bicep", "forearm"]

ISOLATION_TEMPLATES = {
    "tricep": {
        "slot": "Triceps",
        "default": "Overhead Tricep Extension",
        "muscle": "triceps",
        # Overhead extension = long-head stretch. RP / stretch-mediated
        # hypertrophy research shows long-head tricep responds strongly here.
        "rep_range": "10-15",
        "incr": 1.25,
        "myo": True,
    },
    "bicep": {
        "slot": "Biceps",
        "default": "Barbell Curl",
        "muscle": "biceps",
        "rep_range": "10-15",
        "incr": 1.25,
        "myo": True,
    },
    "forearm": {
        "slot": "Forearms",
        "default": "Wrist Curl",
        "muscle": "forearms",
        "rep_range": "12-20",
        "incr": 1.25,
        "myo": False,
    },
    "lateral_raise": {
        "slot": "Lateral Raise",
        "default": "Dumbbell Lateral Raise",
        "muscle": "shoulders",
        "rep_range": "15-25",
        # RP: laterals respond best to higher reps and myo-rep match.
        # Keep weight light — most people cheat with too much.
        "incr": 0.5,
        "myo": True,
    },
    "rear_delt": {
        "slot": "Rear Delt",
        "default": "Face Pull",
        # RP priority muscle: most chronically undertrained group.
        # Bench press is anterior-delt dominant — rear delt work is
        # essential to maintain shoulder health and rotator cuff balance.
        # Face pulls / reverse flies / band pull-aparts all work well.
        "muscle": "rear_delts",
        "rep_range": "15-25",
        "incr": 0.5,
        "myo": True,
    },
}

# ── Deload weight factor ──────────────────────────────────────────────────────
# RP deload = ~50 % volume AND ~10-20 % weight reduction.
DELOAD_WEIGHT_FACTOR = 0.90   # suggest 90 % of last working weight

# ── Mesocycle ─────────────────────────────────────────────────────────────────

def get_rir_plan(total_weeks):
    plans = {
        3: [3, 2, 1],
        4: [3, 3, 2, 1],
        5: [3, 3, 2, 2, 1],
    }
    return plans.get(total_weeks, [3, 2, 1])


def _build_exercise_state():
    state = {}
    for key, tmpl in COMPOUND_TEMPLATES.items():
        state[key] = {
            "name": tmpl["default"],
            "sets": INITIAL_SETS["compound"],
            "last_weight": None,
            "last_reps": None,
        }
    for key, tmpl in ISOLATION_TEMPLATES.items():
        state[key] = {
            "name": tmpl["default"],
            "sets": INITIAL_SETS["isolation"],
            "last_weight": None,
            "last_reps": None,
        }
    return state


def new_meso(total_weeks=4):
    return {
        "start_date": str(date.today()),
        "total_weeks": total_weeks,
        "rir_plan": get_rir_plan(total_weeks),
        "current_week": 1,
        "session_number": 0,
        "legs_toggle": 0,
        "non_shoulder_iso_index": 0,
        "is_deload": False,
        "deload_done": False,
        "exercise_state": _build_exercise_state(),
    }


def get_current_rir(meso):
    if meso.get("is_deload"):
        return 4
    week = meso["current_week"]
    plan = meso["rir_plan"]
    if 1 <= week <= len(plan):
        return plan[week - 1]
    return None


def get_next_session_plan(meso):
    """
    Returns (compound_key, iso_key, extra_iso_key_or_None).
    Shoulder sessions return extra_iso_key = "rear_delt".
    Does NOT advance state — call advance_session() after logging.
    """
    sn = meso["session_number"]

    compound_type = COMPOUND_CYCLE[sn % len(COMPOUND_CYCLE)]
    if compound_type == "legs":
        compound_key = "legs_squat" if meso["legs_toggle"] % 2 == 0 else "legs_sldl"
    else:
        compound_key = compound_type

    if sn % 2 == 1:   # shoulder session → lateral + rear delt
        iso_key   = "lateral_raise"
        extra_iso = "rear_delt"
    else:
        iso_key   = NON_SHOULDER_ISO_CYCLE[
            meso["non_shoulder_iso_index"] % len(NON_SHOULDER_ISO_CYCLE)
        ]
        extra_iso = None

    return compound_key, iso_key, extra_iso


def advance_session(meso):
    sn = meso["session_number"]

    compound_type = COMPOUND_CYCLE[sn % len(COMPOUND_CYCLE)]
    if compound_type == "legs":
        meso["legs_toggle"] += 1

    if sn % 2 == 0:
        meso["non_shoulder_iso_index"] += 1

    meso["session_number"] += 1
    new_sn = meso["session_number"]

    sessions_per_week = 6
    new_week = (new_sn // sessions_per_week) + 1

    if not meso.get("is_deload"):
        if new_week > meso["total_weeks"]:
            meso["is_deload"] = True
            meso["current_week"] = meso["total_weeks"] + 1
        else:
            meso["current_week"] = new_week
    else:
        deload_start_sn = meso["total_weeks"] * sessions_per_week
        if new_sn >= deload_start_sn + sessions_per_week:
            meso["deload_done"] = True

    return meso


# ── Biofeedback ───────────────────────────────────────────────────────────────

def compute_set_adjustment(pump, soreness):
    """
    Biofeedback = empirical volume-landmark detection (RP framework):
      pump    : 0=yes  → stimulus signal present (approaching MAV)
                1=no   → below MEV or exercise choice poor
      soreness: -1=didn't recover → above MRV
                 0=just in time   → near MRV
                 1=wasn't sore    → below MAV, room to add volume

    pump_score = +1 if pump==0 else -1
    combined   = pump_score + soreness  ∈ [-2, +2]
      >= +1 → +1 set (good stimulus, recovered well → below MAV)
      <= -2 → -1 set (no stimulus, poor recovery → above MRV)
       else → 0     (on target)
    """
    pump_score = 1 if pump == 0 else -1
    combined   = pump_score + soreness
    if combined >= 1:
        return 1
    elif combined <= -2:
        return -1
    return 0


def biofeedback_message(adjustment):
    if adjustment == 1:
        return "→ Good stimulus + recovered well. +1 set next time (still below MAV)."
    elif adjustment == -1:
        return "→ Recovery was rough. -1 set next time (likely above MRV)."
    return "→ Volume on point. Maintaining."


# ── Weight suggestions ────────────────────────────────────────────────────────

def suggest_weight(last_weight, incr, is_deload=False):
    if last_weight is None:
        return None
    if is_deload:
        return round(last_weight * DELOAD_WEIGHT_FACTOR, 2)
    return round(last_weight + incr, 2)
