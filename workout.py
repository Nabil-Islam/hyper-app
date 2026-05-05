"""
workout.py — Upper/Lower 4-day split, cut-specific mesocycle

Context:
  - Goal: body recomposition / fat loss while preserving muscle
  - GLP-1 agonist: appetite managed externally; protein targets are critical
  - 5'10", targeting 95-100kg beefy look — substantial muscle to protect
  - 4 days/week Upper/Lower gives 2x/week frequency per muscle group,
    which is the minimum RP recommends for muscle retention during a cut

Cut-specific design decisions vs a bulk:
  - 3-week mesos (shorter = deload before fatigue compounds in a deficit)
  - RIR starts at 4, not 3 (less recovery capacity in a deficit)
  - RIR plan: 4 → 3 → 2 → Deload
  - Starting sets held at minimum effective dose (compounds: 2, isolations: 2)
  - Volume target: maintain, not accumulate — biofeedback gates any additions
  - Progressive overload focus on compounds — this is the signal to retain muscle

RP volume landmarks (sets/muscle/week) — maintenance targets during cut:
  Chest:      MEV 6  MAV 16  MRV 22
  Back:       MEV 8  MAV 18  MRV 25
  Quads:      MEV 6  MAV 16  MRV 20
  Hamstrings: MEV 4  MAV 12  MRV 16
  Glutes:     MEV 0  MAV  8  MRV 12
  Biceps:     MEV 6  MAV 14  MRV 20
  Triceps:    MEV 6  MAV 14  MRV 20
  Shoulders:  MEV 6  MAV 16  MRV 22
  Rear delts: MEV 6  MAV 16  MRV 22
  Calves:     MEV 6  MAV 12  MRV 16
"""
from datetime import date

# ── Volume landmarks ──────────────────────────────────────────────────────────
VOLUME_LANDMARKS = {
    "chest":      {"mev": 6,  "mav": 16, "mrv": 22},
    "back":       {"mev": 8,  "mav": 18, "mrv": 25},
    "quads":      {"mev": 6,  "mav": 16, "mrv": 20},
    "hamstrings": {"mev": 4,  "mav": 12, "mrv": 16},
    "glutes":     {"mev": 0,  "mav":  8, "mrv": 12},
    "biceps":     {"mev": 6,  "mav": 14, "mrv": 20},
    "triceps":    {"mev": 6,  "mav": 14, "mrv": 20},
    "shoulders":  {"mev": 6,  "mav": 16, "mrv": 22},
    "rear_delts": {"mev": 6,  "mav": 16, "mrv": 22},
    "calves":     {"mev": 6,  "mav": 12, "mrv": 16},
}

# ── Starting sets ─────────────────────────────────────────────────────────────
INITIAL_SETS = {"compound": 2, "isolation": 2}

# ── Upper/Lower 4-day split ───────────────────────────────────────────────────
#
# Day A — Upper (Push focus)
#   Bench Press  — primary chest/anterior delt driver
#   Barbell Row  — horizontal back, rear delt, bicep synergist
#   Lateral Raise — side delt [myo]
#   Tricep Pushdown — long-head stretch stimulus [myo]
#
# Day B — Lower (Quad focus)
#   Squat        — quad + glute compound
#   Romanian DL  — hip hinge, hamstring + glute stretch
#   Leg Curl     — hamstring isolation
#
# Day C — Upper (Pull focus)
#   Incline Bench — chest with higher stretch angle than flat
#   Lat Pulldown  — vertical pull, lat width
#   Bicep Curl   — peak bicep [myo]
#   Face Pull    — rear delt + rotator cuff health [myo]
#
# Day D — Lower (Hinge focus)
#   Stiff-Leg DL — hamstring + glute hinge emphasis
#   Leg Press    — quad volume without spinal load
#   Hip Thrust   — glute isolation [myo]
#   Calf Raise   — calf isolation [myo]
#
# Cycle: A → B → C → D → A → B → C → D → ...

DAY_SEQUENCE = ["upper_a", "lower_b", "upper_c", "lower_d"]

SESSIONS = {
    "upper_a": {
        "name": "Upper A  —  Push Focus",
        "exercises": [
            {
                "key": "bench_press",
                "slot": "Bench Press",
                "default": "Barbell Bench Press",
                "muscle": "chest",
                "kind": "compound",
                "rep_range": "8-12",
                "incr": 2.5,
                "myo": False,
                "note": "Control the eccentric (~2s down). Full ROM — touch chest.",
            },
            {
                "key": "barbell_row",
                "slot": "Barbell Row",
                "default": "Barbell Row",
                "muscle": "back",
                "kind": "compound",
                "rep_range": "6-10",
                "incr": 2.5,
                "myo": False,
                "note": "Horizontal pull — supinated or pronated grip both fine.",
            },
            {
                "key": "lateral_raise",
                "slot": "Lateral Raise",
                "default": "Dumbbell Lateral Raise",
                "muscle": "shoulders",
                "kind": "isolation",
                "rep_range": "15-25",
                "incr": 0.5,
                "myo": True,
                "note": "Light weight, lead with elbows, slight forward lean.",
            },
            {
                "key": "tricep_pushdown",
                "slot": "Triceps",
                "default": "Overhead Tricep Extension",
                "muscle": "triceps",
                "kind": "isolation",
                "rep_range": "10-15",
                "incr": 1.25,
                "myo": True,
                "note": "Overhead = long head stretch. Best hypertrophy stimulus for tris.",
            },
        ],
    },
    "lower_b": {
        "name": "Lower B  —  Quad Focus",
        "exercises": [
            {
                "key": "squat",
                "slot": "Squat",
                "default": "Barbell Back Squat",
                "muscle": "quads",
                "kind": "compound",
                "rep_range": "8-12",
                "incr": 2.5,
                "myo": False,
                "note": "8-12 rep range keeps quad stimulus high with less systemic fatigue than lower reps.",
            },
            {
                "key": "romanian_dl",
                "slot": "Romanian DL",
                "default": "Romanian Deadlift",
                "muscle": "hamstrings",
                "kind": "compound",
                "rep_range": "10-15",
                "incr": 2.5,
                "myo": False,
                "note": "Hip hinge — feel the hamstring stretch at the bottom. Not a squat.",
            },
            {
                "key": "leg_curl",
                "slot": "Leg Curl",
                "default": "Lying Leg Curl",
                "muscle": "hamstrings",
                "kind": "isolation",
                "rep_range": "12-20",
                "incr": 2.5,
                "myo": False,
                "note": "Hamstrings respond well to higher reps and stretch (plantarflex foot if possible).",
            },
        ],
    },
    "upper_c": {
        "name": "Upper C  —  Pull Focus",
        "exercises": [
            {
                "key": "incline_bench",
                "slot": "Incline Bench",
                "default": "Incline Barbell Press",
                "muscle": "chest",
                "kind": "compound",
                "rep_range": "8-12",
                "incr": 2.5,
                "myo": False,
                "note": "30-45° incline. Hits upper chest and provides more stretch than flat.",
            },
            {
                "key": "lat_pulldown",
                "slot": "Lat Pulldown",
                "default": "Lat Pulldown",
                "muscle": "back",
                "kind": "compound",
                "rep_range": "8-12",
                "incr": 2.5,
                "myo": False,
                "note": "Full stretch at top, pull to upper chest. Don't kip.",
            },
            {
                "key": "bicep_curl",
                "slot": "Bicep Curl",
                "default": "Barbell Curl",
                "muscle": "biceps",
                "kind": "isolation",
                "rep_range": "10-15",
                "incr": 1.25,
                "myo": True,
                "note": "Full ROM — full extension at bottom is where the stretch stimulus lives.",
            },
            {
                "key": "face_pull",
                "slot": "Face Pull / Rear Delt",
                "default": "Face Pull",
                "muscle": "rear_delts",
                "kind": "isolation",
                "rep_range": "15-25",
                "incr": 0.5,
                "myo": True,
                "note": "RP priority: most undertrained group. Shoulder health insurance vs bench press.",
            },
        ],
    },
    "lower_d": {
        "name": "Lower D  —  Hinge Focus",
        "exercises": [
            {
                "key": "sldl",
                "slot": "Stiff-Leg DL",
                "default": "Stiff-Leg Deadlift",
                "muscle": "hamstrings",
                "kind": "compound",
                "rep_range": "6-10",
                "incr": 2.5,
                "myo": False,
                "note": "Hinge emphasis — stretch at bottom is the stimulus. Control the descent.",
            },
            {
                "key": "leg_press",
                "slot": "Leg Press",
                "default": "Leg Press",
                "muscle": "quads",
                "kind": "compound",
                "rep_range": "10-15",
                "incr": 5.0,
                "myo": False,
                "note": "Quad volume without spinal load — good complement to squat day.",
            },
            {
                "key": "hip_thrust",
                "slot": "Hip Thrust",
                "default": "Barbell Hip Thrust",
                "muscle": "glutes",
                "kind": "isolation",
                "rep_range": "10-15",
                "incr": 2.5,
                "myo": True,
                "note": "Squeeze at top. Glutes respond well to myo-rep match at moderate weight.",
            },
            {
                "key": "calf_raise",
                "slot": "Calf Raise",
                "default": "Standing Calf Raise",
                "muscle": "calves",
                "kind": "isolation",
                "rep_range": "10-15",
                "incr": 2.5,
                "myo": True,
                "note": "Full stretch at bottom — calves respond almost exclusively to stretch stimulus.",
            },
        ],
    },
}

# ── Mesocycle — cut specific ──────────────────────────────────────────────────
# 3-week accumulation (shorter = deload before fatigue compounds in deficit)
# RIR 4→3→2→Deload (higher start = more buffer for deficit-impaired recovery)

DEFAULT_MESO_WEEKS = 3
CUT_RIR_PLAN       = [4, 3, 2]


def get_rir_plan(total_weeks):
    plans = {
        3: [4, 3, 2],
        4: [4, 3, 3, 2],
        5: [4, 3, 3, 2, 2],
    }
    return plans.get(total_weeks, CUT_RIR_PLAN)


def _build_exercise_state():
    state = {}
    for day_data in SESSIONS.values():
        for ex in day_data["exercises"]:
            k = ex["key"]
            if k not in state:
                state[k] = {
                    "name":        ex["default"],
                    "sets":        INITIAL_SETS[ex["kind"]],
                    "last_weight": None,
                    "last_reps":   None,
                }
    return state


def new_meso(total_weeks=DEFAULT_MESO_WEEKS):
    return {
        "start_date":    str(date.today()),
        "total_weeks":   total_weeks,
        "rir_plan":      get_rir_plan(total_weeks),
        "current_week":  1,
        "session_number": 0,
        "day_index":     0,   # index into DAY_SEQUENCE
        "is_deload":     False,
        "deload_done":   False,
        "exercise_state": _build_exercise_state(),
    }


def get_current_rir(meso):
    if meso.get("is_deload"):
        return 4
    week = meso["current_week"]
    plan = meso["rir_plan"]
    return plan[week - 1] if 1 <= week <= len(plan) else plan[-1]


def get_next_session(meso):
    """Return (day_key, day_data) without advancing state."""
    day_key = DAY_SEQUENCE[meso["day_index"] % len(DAY_SEQUENCE)]
    return day_key, SESSIONS[day_key]


def advance_session(meso):
    meso["session_number"] += 1
    meso["day_index"] = (meso["day_index"] + 1) % len(DAY_SEQUENCE)

    # Every full 4-session cycle = 1 week
    if meso["session_number"] % len(DAY_SEQUENCE) == 0:
        if not meso.get("is_deload"):
            if meso["current_week"] >= meso["total_weeks"]:
                meso["is_deload"] = True
                meso["current_week"] += 1
            else:
                meso["current_week"] += 1
        else:
            meso["deload_done"] = True

    return meso


# ── Biofeedback ───────────────────────────────────────────────────────────────

def compute_set_adjustment(pump, soreness):
    """
    During a cut, bias conservative:
      Only add a set if both pump AND recovery are good.
      Drop a set if recovery was poor (MRV signal in a deficit = back off fast).
    """
    pump_score = 1 if pump == 0 else -1
    combined   = pump_score + soreness
    if combined >= 2:    # good pump + good recovery = still below MAV
        return 1
    elif combined <= -1: # poor recovery in a deficit = likely above MRV
        return -1
    return 0


def biofeedback_message(adjustment):
    if adjustment == 1:
        return "→ Good stimulus + recovered well. +1 set next time."
    elif adjustment == -1:
        return "→ Recovery was rough (normal in a cut). -1 set next time."
    return "→ Volume on point. Maintaining."


# ── Weight suggestion ─────────────────────────────────────────────────────────
DELOAD_WEIGHT_FACTOR = 0.90

def suggest_weight(last_weight, incr, is_deload=False):
    if last_weight is None:
        return None
    if is_deload:
        return round(last_weight * DELOAD_WEIGHT_FACTOR, 2)
    return round(last_weight + incr, 2)
