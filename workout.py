"""
workout.py — mesocycle logic, PPL templates, biofeedback, set/weight progression
"""
from datetime import date

# ── PPL day sequence ─────────────────────────────────────────────────────────

DAY_SEQUENCE = ["Push1", "Pull1", "Legs1", "Push2", "Pull2", "Legs2"]

# ── Exercise templates ────────────────────────────────────────────────────────
# size:  "large" → start at 2 sets | "small" → start at 3 sets
# myo:   True → run as myo-rep-match set
# incr:  kg to suggest adding each session for that exercise

WORKOUT_TEMPLATE = {
    "Push1": {
        "name": "Push 1 — Chest · Triceps · Shoulder",
        "exercises": [
            {
                "slot": "Chest",
                "default": "Barbell Bench Press",
                "muscle": "chest",
                "size": "large",
                "myo": False,
                "rep_range": "6-10",
                "incr": 2.5,
            },
            {
                "slot": "Triceps",
                "default": "Overhead Tricep Extension",
                "muscle": "triceps",
                "size": "small",
                "myo": True,
                "rep_range": "10-15",
                "incr": 1.25,
            },
            {
                "slot": "Shoulder",
                "default": "Lateral Raise",
                "muscle": "shoulders",
                "size": "small",
                "myo": True,
                "rep_range": "12-20",
                "incr": 1.25,
            },
        ],
    },
    "Pull1": {
        "name": "Pull 1 — Horizontal Back · Biceps · Shoulder",
        "exercises": [
            {
                "slot": "Back (Horizontal)",
                "default": "Barbell Row",
                "muscle": "back",
                "size": "large",
                "myo": False,
                "rep_range": "6-10",
                "incr": 2.5,
            },
            {
                "slot": "Biceps",
                "default": "Barbell Curl",
                "muscle": "biceps",
                "size": "small",
                "myo": True,
                "rep_range": "10-15",
                "incr": 1.25,
            },
            {
                "slot": "Shoulder (Rear)",
                "default": "Face Pull",
                "muscle": "shoulders",
                "size": "small",
                "myo": True,
                "rep_range": "12-20",
                "incr": 1.25,
            },
        ],
    },
    "Legs1": {
        "name": "Legs 1 — Quad Focus",
        "exercises": [
            {
                "slot": "Quads (Heavy Compound)",
                "default": "Squat",
                "muscle": "quads",
                "size": "large",
                "myo": False,
                "rep_range": "4-8",
                "incr": 2.5,
            },
            {
                "slot": "Hamstrings (Light / High-Rep)",
                "default": "Leg Curl",
                "muscle": "hamstrings",
                "size": "large",
                "myo": False,
                "rep_range": "12-20",
                "incr": 2.5,
            },
            {
                "slot": "Glutes",
                "default": "Hip Thrust",
                "muscle": "glutes",
                "size": "small",
                "myo": True,
                "rep_range": "10-15",
                "incr": 2.5,
            },
        ],
    },
    "Push2": {
        "name": "Push 2 — Incline Chest · Triceps · Shoulder",
        "exercises": [
            {
                "slot": "Chest (Incline)",
                "default": "Incline Barbell Press",
                "muscle": "chest",
                "size": "large",
                "myo": False,
                "rep_range": "8-12",
                "incr": 2.5,
            },
            {
                "slot": "Triceps",
                "default": "Tricep Pushdown",
                "muscle": "triceps",
                "size": "small",
                "myo": True,
                "rep_range": "10-15",
                "incr": 1.25,
            },
            {
                "slot": "Shoulder",
                "default": "Rear Delt Fly",
                "muscle": "shoulders",
                "size": "small",
                "myo": True,
                "rep_range": "12-20",
                "incr": 1.25,
            },
        ],
    },
    "Pull2": {
        "name": "Pull 2 — Vertical Back · Biceps · Shoulder",
        "exercises": [
            {
                "slot": "Back (Vertical)",
                "default": "Lat Pulldown",
                "muscle": "back",
                "size": "large",
                "myo": False,
                "rep_range": "6-12",
                "incr": 2.5,
            },
            {
                "slot": "Biceps",
                "default": "Incline Dumbbell Curl",
                "muscle": "biceps",
                "size": "small",
                "myo": True,
                "rep_range": "10-15",
                "incr": 1.25,
            },
            {
                "slot": "Shoulder (Rear)",
                "default": "Band Pull-Apart",
                "muscle": "shoulders",
                "size": "small",
                "myo": True,
                "rep_range": "12-20",
                "incr": 1.25,
            },
        ],
    },
    "Legs2": {
        "name": "Legs 2 — Hamstring Focus",
        "exercises": [
            {
                "slot": "Hamstrings (SLDL)",
                "default": "Stiff-Leg Deadlift",
                "muscle": "hamstrings",
                "size": "large",
                "myo": False,
                "rep_range": "6-10",
                "incr": 2.5,
            },
            {
                "slot": "Quads (Light / High-Rep)",
                "default": "Leg Extension",
                "muscle": "quads",
                "size": "large",
                "myo": False,
                "rep_range": "15-20",
                "incr": 2.5,
            },
            {
                "slot": "Glutes",
                "default": "Romanian Deadlift",
                "muscle": "glutes",
                "size": "small",
                "myo": True,
                "rep_range": "12-15",
                "incr": 2.5,
            },
            {
                "slot": "Calves",
                "default": "Standing Calf Raise",
                "muscle": "calves",
                "size": "small",
                "myo": True,
                "rep_range": "10-15",
                "incr": 1.25,
            },
        ],
    },
}

# Starting set counts
INITIAL_SETS = {"large": 2, "small": 3}

# ── Mesocycle ─────────────────────────────────────────────────────────────────

def get_rir_plan(total_weeks):
    """RIR sequence for accumulation weeks (deload always follows)."""
    plans = {
        3: [3, 2, 1],
        4: [3, 3, 2, 1],
        5: [3, 3, 2, 2, 1],
    }
    return plans.get(total_weeks, [3, 2, 1])


def new_meso(total_weeks=4):
    rir_plan = get_rir_plan(total_weeks)

    # Build per-exercise state for every day
    exercise_state = {}
    for day_key, day_data in WORKOUT_TEMPLATE.items():
        exercise_state[day_key] = {}
        for ex in day_data["exercises"]:
            exercise_state[day_key][ex["slot"]] = {
                "name": ex["default"],
                "sets": INITIAL_SETS[ex["size"]],
                "last_weight": None,
                "last_reps": None,
            }

    return {
        "start_date": str(date.today()),
        "total_weeks": total_weeks,
        "rir_plan": rir_plan,
        "current_week": 1,
        "next_day_index": 0,
        "is_deload": False,
        "deload_done": False,
        "exercise_state": exercise_state,
    }


def get_current_rir(meso):
    """Return RIR target for the current week, or None if deload/done."""
    if meso.get("is_deload"):
        return None          # handled separately in UI
    week = meso["current_week"]
    plan = meso["rir_plan"]
    if 1 <= week <= len(plan):
        return plan[week - 1]
    return None


def get_next_day(meso):
    return DAY_SEQUENCE[meso["next_day_index"] % len(DAY_SEQUENCE)]


def advance_day(meso):
    """
    Move to the next day in the PPL cycle.
    Wrapping around 6 days = completing one week.
    After total_weeks accumulation weeks the next cycle is the deload.
    After the deload cycle deload_done is set → prompt user to start new meso.
    """
    meso["next_day_index"] = (meso["next_day_index"] + 1) % len(DAY_SEQUENCE)

    # Completed a full 6-day cycle
    if meso["next_day_index"] == 0:
        if meso.get("is_deload"):
            meso["deload_done"] = True          # deload week finished
        elif meso["current_week"] >= meso["total_weeks"]:
            meso["is_deload"] = True            # enter deload
            meso["current_week"] += 1
        else:
            meso["current_week"] += 1           # next accumulation week

    return meso


# ── Biofeedback → set adjustment ──────────────────────────────────────────────

def compute_set_adjustment(pump, soreness):
    """
    pump    : 0 = got a pump (good), 1 = no pump (bad)
    soreness: -1 = didn't recover, 0 = recovered just in time, 1 = wasn't sore

    Scoring table:
      pump_score  =  +1 if pump==0, else -1
      combined    =  pump_score + soreness  → range [-2, +2]

      +2  → add 1 set   (great stimulus, easy recovery)
      +1  → add 1 set   (good stimulus or easy recovery)
       0  → maintain    (on point)
      -1  → maintain    (borderline — keep monitoring)
      -2  → drop 1 set  (poor session AND poor recovery)
    """
    pump_score = 1 if pump == 0 else -1
    combined = pump_score + soreness
    if combined >= 1:
        return 1
    elif combined <= -2:
        return -1
    return 0


def biofeedback_message(adjustment):
    if adjustment == 1:
        return "→ Great stimulus! +1 set next session."
    elif adjustment == -1:
        return "→ Recovery was rough. -1 set next session."
    return "→ Volume on point. Maintaining."


# ── Weight suggestion ─────────────────────────────────────────────────────────

def suggest_weight(last_weight, incr):
    """Suggest last_weight + increment, or None on first session."""
    if last_weight is None:
        return None
    return round(last_weight + incr, 2)
