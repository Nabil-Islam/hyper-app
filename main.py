#!/usr/bin/env python3
"""
main.py — Workout Tracker CLI
Data stored locally at ~/.workout_data.json

Commands available at any prompt during a workout:
  /pause   — save progress and exit (resume later with option 1)
  /cancel  — discard session entirely
  /done    — finish session early with exercises completed so far
"""
import sys
from datetime import date

import store
import workout as wk

# ── Session control signals ───────────────────────────────────────────────────

class PauseSession(Exception):
    pass

class CancelSession(Exception):
    pass

class FinishEarly(Exception):
    pass

COMMANDS = {
    "/pause":  PauseSession,
    "/cancel": CancelSession,
    "/done":   FinishEarly,
}

def _check_command(raw):
    """Raise the appropriate signal if the user typed a command."""
    stripped = raw.strip().lower()
    if stripped in COMMANDS:
        raise COMMANDS[stripped]()

# ── CLI helpers ───────────────────────────────────────────────────────────────

def hr(char="─", width=50):
    print(char * width)

def header(text):
    hr("═")
    print(f"  {text}")
    hr("═")

def section(text):
    print()
    hr()
    print(f"  {text}")
    hr()

def _cmd_hint():
    print("  (type /pause · /done · /cancel at any prompt)")

def prompt_int(text, min_val=None, max_val=None, default=None):
    suffix = f" [{default}]" if default is not None else ""
    while True:
        raw = input(f"  {text}{suffix}: ").strip()
        _check_command(raw)
        val_str = raw if raw else (str(default) if default is not None else "")
        try:
            val = int(val_str)
        except ValueError:
            print("    ! Enter a whole number  (or /pause · /done · /cancel).")
            continue
        if min_val is not None and val < min_val:
            print(f"    ! Minimum is {min_val}.")
            continue
        if max_val is not None and val > max_val:
            print(f"    ! Maximum is {max_val}.")
            continue
        return val

def prompt_float(text, suggest=None):
    suffix = f" [suggest {suggest}]" if suggest is not None else ""
    while True:
        raw = input(f"  {text}{suffix}: ").strip()
        _check_command(raw)
        if raw == "" and suggest is not None:
            return suggest
        try:
            return float(raw)
        except ValueError:
            print("    ! Enter a number (e.g. 60 or 62.5)  (or /pause · /done · /cancel).")

def confirm(text):
    raw = input(f"  {text} (y/n): ").strip()
    _check_command(raw)
    return raw.lower() == "y"

# ── Single exercise block ─────────────────────────────────────────────────────

def _run_exercise(tmpl, ex_key, state, rir_target, is_deload):
    """
    Prompt through one exercise.
    Raises PauseSession, CancelSession, or FinishEarly on command.
    Returns (updated_state, log_dict) on normal completion.
    """
    section(f"{tmpl['slot'].upper()}  ·  {tmpl['muscle']}")
    myo_tag = "  [MYO-REP MATCH]" if tmpl.get("myo") else ""
    print(f"  Exercise : {state['name']}{myo_tag}")
    print(f"  Reps     : {tmpl['rep_range']}  |  RIR {rir_target}")
    _cmd_hint()

    new_name = input("  Rename?    [ENTER to keep]: ").strip()
    _check_command(new_name)
    if new_name:
        state["name"] = new_name

    if tmpl.get("myo") and not is_deload:
        print()
        print("  MYO-REP MATCH:")
        print("    1. Activation set to ~1 RIR at top of rep range")
        print("    2. Rest 5-10 breaths")
        print("    3. Mini-sets matching ~30 % of activation reps until failure to match")

    last_w  = state.get("last_weight")
    suggest = wk.suggest_weight(last_w, tmpl["incr"], is_deload)

    if last_w:
        deload_note = f"  (deload → suggest {suggest} kg)" if is_deload else ""
        print(f"\n  Last time : {last_w} kg × {state.get('last_reps', '?')} reps{deload_note}")
    else:
        print("\n  (First session — enter weight manually)")

    planned = state["sets"]
    if is_deload:
        planned = max(1, (planned + 1) // 2)
    print(f"  Sets      : {planned}")
    print()

    sets_logged = []

    if tmpl.get("myo") and not is_deload:
        weight   = prompt_float("Activation weight (kg)", suggest)
        act_reps = prompt_int("Activation reps", min_val=1)
        minis    = prompt_int("Mini sets completed", min_val=0)
        sets_logged.append({
            "type": "myo",
            "weight": weight,
            "activation_reps": act_reps,
            "mini_sets": minis,
        })
        final_weight, final_reps = weight, act_reps
    else:
        current_suggest = suggest
        set_num = 0
        while True:
            set_num += 1
            print(f"  Set {set_num}:")
            weight = prompt_float("    Weight (kg)", current_suggest)
            reps   = prompt_int("    Reps", min_val=0)
            sets_logged.append({"set": set_num, "weight": weight, "reps": reps})
            current_suggest = weight
            if set_num < planned:
                continue
            if not is_deload and confirm("  Add another set?"):
                continue
            break
        final_weight = sets_logged[-1]["weight"]
        final_reps   = sets_logged[-1]["reps"]

    state["last_weight"] = final_weight
    state["last_reps"]   = final_reps

    # Biofeedback
    print(f"\n  — Biofeedback: {tmpl['muscle'].upper()} —")
    pump     = prompt_int("  Pump?     0=yes  1=no", min_val=0, max_val=1)
    soreness = prompt_int(
        "  Soreness? -1=didn't recover  0=just in time  1=wasn't sore",
        min_val=-1, max_val=1,
    )
    adj = wk.compute_set_adjustment(pump, soreness)
    print(f"  {wk.biofeedback_message(adj)}")
    state["sets"] = max(1, min(8, state["sets"] + adj))

    log = {
        "slot":           tmpl["slot"],
        "name":           state["name"],
        "muscle":         tmpl["muscle"],
        "myo":            tmpl.get("myo", False),
        "sets":           sets_logged,
        "biofeedback":    {"pump": pump, "soreness": soreness},
        "set_adjustment": adj,
    }
    return state, log

# ── Session runner ────────────────────────────────────────────────────────────

def run_session(data):
    meso = data.get("current_meso")
    if not meso:
        print("\n  No active meso — start one first (option 2).")
        return data
    if meso.get("deload_done"):
        print("\n  Deload complete! Start a fresh mesocycle (option 2).")
        return data

    # ── Resume paused session if one exists ───────────────────────────────────
    paused = data.get("paused_session")
    if paused:
        print()
        hr("═")
        print(f"  ⏸  Paused session found ({paused['date']})")
        print(f"     Completed : {', '.join(e['slot'] for e in paused['exercises_done']) or 'nothing yet'}")
        remaining = paused.get("exercises_remaining", [])
        print(f"     Remaining : {', '.join(r['slot'] for r in remaining)}")
        hr("═")
        choice = input("  Resume (r), discard paused & start fresh (s), or back to menu (b)? ").strip().lower()
        if choice == "b":
            return data
        elif choice == "r":
            return _resume_session(data, paused, meso)
        else:
            print("  Paused session discarded.")
            data.pop("paused_session", None)

    is_deload  = meso.get("is_deload", False)
    rir_target = wk.get_current_rir(meso)

    compound_key, iso_key, extra_iso = wk.get_next_session_plan(meso)
    c_tmpl   = wk.COMPOUND_TEMPLATES[compound_key]
    i_tmpl   = wk.ISOLATION_TEMPLATES[iso_key]
    ex2_tmpl = wk.ISOLATION_TEMPLATES[extra_iso] if extra_iso else None

    exercises = [
        (c_tmpl,   compound_key),
        (i_tmpl,   iso_key),
    ]
    if ex2_tmpl and extra_iso:
        exercises.append((ex2_tmpl, extra_iso))

    session_num = meso["session_number"] + 1
    slots = "  +  ".join(t["slot"] for t, _ in exercises)
    header(f"Session {session_num}  ·  {slots}")

    if is_deload:
        print("  🔄  DELOAD  —  ~50 % sets  ·  ~90 % weight  ·  clean form, no grinding")
        rir_target = 4
    else:
        rir_str = " → ".join(str(r) for r in meso["rir_plan"]) + " → Deload"
        print(f"  Week {meso['current_week']} of {meso['total_weeks']}  "
              f"|  RIR target: {rir_target}  |  {rir_str}")
    print()
    _cmd_hint()

    return _run_exercises(data, meso, exercises, session_num, rir_target, is_deload,
                          exercises_done=[], start_index=0)


def _resume_session(data, paused, meso):
    """Reconstruct exercise list and resume from where we left off."""
    is_deload  = paused.get("is_deload", False)
    rir_target = paused.get("rir_target", wk.get_current_rir(meso))
    session_num = paused["session_n"]

    remaining_slots = {r["key"]: r for r in paused.get("exercises_remaining", [])}

    # Rebuild full exercise list in original order
    compound_key, iso_key, extra_iso = paused["plan"]
    all_keys = [compound_key, iso_key] + ([extra_iso] if extra_iso else [])

    exercises = []
    for key in all_keys:
        tmpl = (wk.COMPOUND_TEMPLATES.get(key) or wk.ISOLATION_TEMPLATES.get(key))
        if tmpl:
            exercises.append((tmpl, key))

    # Only the remaining ones need running
    remaining_exercises = [(t, k) for t, k in exercises if k in remaining_slots]

    slots = "  +  ".join(t["slot"] for t, _ in remaining_exercises)
    header(f"Session {session_num} (resumed)  ·  {slots}")
    print()
    _cmd_hint()

    return _run_exercises(
        data, meso, remaining_exercises, session_num, rir_target, is_deload,
        exercises_done=paused["exercises_done"],
        start_index=len(paused["exercises_done"]),
        plan=paused["plan"],
        session_date=paused["date"],
    )


def _run_exercises(data, meso, exercises, session_num, rir_target, is_deload,
                   exercises_done, start_index, plan=None, session_date=None):
    """
    Inner loop.  Handles pause / cancel / finish-early by saving state.
    Returns updated data dict in all cases.
    """
    ex_state   = meso["exercise_state"]
    session_log = list(exercises_done)  # copy already-done exercises

    # Build plan tuple for pause storage
    if plan is None:
        compound_key, iso_key, extra_iso = wk.get_next_session_plan(meso)
        plan = (compound_key, iso_key, extra_iso)

    if session_date is None:
        session_date = str(date.today())

    remaining = list(exercises)

    for tmpl, ex_key in exercises:
        remaining = [(t, k) for t, k in remaining if k != ex_key]

        try:
            ex_state[ex_key], log = _run_exercise(
                tmpl, ex_key, ex_state[ex_key], rir_target, is_deload
            )
            session_log.append(log)

        except PauseSession:
            _save_paused(data, session_num, session_date, rir_target, is_deload,
                         plan, session_log, remaining)
            print()
            print("  ⏸  Session paused. Your progress is saved.")
            print("     Resume next time you start a workout.")
            return data

        except CancelSession:
            data.pop("paused_session", None)
            print()
            print("  ✗  Session cancelled. No data saved for this session.")
            return data

        except FinishEarly:
            if not session_log:
                print("  Nothing completed — session not saved.")
                return data
            print()
            print(f"  Finishing early — saving {len(session_log)} exercise(s).")
            break

    # ── Normal finish (or /done) ──────────────────────────────────────────────
    data.pop("paused_session", None)

    data["sessions"].append({
        "date":       session_date,
        "session_n":  session_num,
        "week":       meso["current_week"],
        "rir_target": rir_target,
        "is_deload":  is_deload,
        "exercises":  session_log,
    })

    data["current_meso"] = wk.advance_session(meso)
    new_meso = data["current_meso"]

    print()
    hr("═")
    if new_meso.get("deload_done"):
        print("  ✓  Deload done! Start a fresh mesocycle (option 2).")
    elif new_meso.get("is_deload") and not meso.get("is_deload"):
        print("  ✓  Accumulation complete! Next up: DELOAD week.")
    else:
        nck, nik, nextra = wk.get_next_session_plan(new_meso)
        nc = wk.COMPOUND_TEMPLATES[nck]["slot"]
        ni = wk.ISOLATION_TEMPLATES[nik]["slot"]
        ne = f" + {wk.ISOLATION_TEMPLATES[nextra]['slot']}" if nextra else ""
        print(f"  ✓  Session logged! Next up: {nc} + {ni}{ne}")
    hr("═")

    return data


def _save_paused(data, session_num, session_date, rir_target, is_deload,
                 plan, exercises_done, remaining_exercises):
    """Persist enough state to resume later."""
    data["paused_session"] = {
        "date":        session_date,
        "session_n":   session_num,
        "rir_target":  rir_target,
        "is_deload":   is_deload,
        "plan":        list(plan),
        "exercises_done": exercises_done,
        "exercises_remaining": [
            {"key": k, "slot": t["slot"]} for t, k in remaining_exercises
        ],
    }

# ── New meso wizard ───────────────────────────────────────────────────────────

def start_new_meso(data):
    header("NEW MESOCYCLE")
    weeks = prompt_int("Accumulation weeks? (3 / 4 / 5)", min_val=3, max_val=5, default=4)
    meso  = wk.new_meso(weeks)
    data["current_meso"] = meso

    rir_str = " → ".join(str(r) for r in meso["rir_plan"]) + " → Deload"
    nck, nik, nextra = wk.get_next_session_plan(meso)
    nc = wk.COMPOUND_TEMPLATES[nck]["slot"]
    ni = wk.ISOLATION_TEMPLATES[nik]["slot"]
    ne = f" + {wk.ISOLATION_TEMPLATES[nextra]['slot']}" if nextra else ""

    print(f"\n  ✓  Meso created!")
    print(f"     Duration  : {weeks} weeks + deload")
    print(f"     RIR plan  : {rir_str}")
    print(f"     Sets start: compound = {wk.INITIAL_SETS['compound']}, "
          f"isolation = {wk.INITIAL_SETS['isolation']}")
    print(f"     Session 1 : {nc} + {ni}{ne}")
    print()
    print("  Volume reference (RP landmarks, sets/muscle/week):")
    print(f"  {'Muscle':<14} {'MEV':>5} {'MAV':>5} {'MRV':>5}")
    hr()
    for muscle, v in wk.VOLUME_LANDMARKS.items():
        print(f"  {muscle:<14} {v['mev']:>5} {v['mav']:>5} {v['mrv']:>5}")

    return data

# ── History viewer ────────────────────────────────────────────────────────────

def view_history(data):
    sessions = data.get("sessions", [])
    if not sessions:
        print("\n  No sessions logged yet.")
        return

    how_many = min(len(sessions), 10)
    print(f"\n  Last {how_many} sessions:\n")

    for s in sessions[-how_many:]:
        tag = " [DELOAD]" if s.get("is_deload") else ""
        print(f"  {s['date']}  Session {s['session_n']}  "
              f"Week {s['week']}  RIR {s['rir_target']}{tag}")
        for ex in s["exercises"]:
            sets = ex["sets"]
            if sets and sets[0].get("type") == "myo":
                s0 = sets[0]
                summary = (f"{s0['weight']} kg × {s0['activation_reps']} "
                           f"+ {s0['mini_sets']} minis")
            else:
                summary = "  ".join(f"{st['weight']}×{st['reps']}" for st in sets)
            adj = {1: "↑", -1: "↓", 0: "="}.get(ex.get("set_adjustment", 0), "")
            print(f"    • {ex['name']:<32} {summary} {adj}")
        print()

# ── Status ────────────────────────────────────────────────────────────────────

def _show_status(meso, paused):
    if not meso:
        print("  No active mesocycle.")
        return
    if meso.get("deload_done"):
        print("  Meso complete — start a new one (option 2).")
        return

    if meso.get("is_deload"):
        print(f"  DELOAD WEEK  (session {meso['session_number'] + 1})")
    else:
        rir = wk.get_current_rir(meso)
        plan_str = " → ".join(str(r) for r in meso["rir_plan"]) + " → Deload"
        print(f"  Week {meso['current_week']} of {meso['total_weeks']}  "
              f"RIR {rir}  |  {plan_str}")

    nck, nik, nextra = wk.get_next_session_plan(meso)
    nc = wk.COMPOUND_TEMPLATES[nck]["slot"]
    ni = wk.ISOLATION_TEMPLATES[nik]["slot"]
    ne = f" + {wk.ISOLATION_TEMPLATES[nextra]['slot']}" if nextra else ""
    print(f"  Next   : {nc} + {ni}{ne}  (session {meso['session_number'] + 1})")
    print(f"  Started: {meso.get('start_date', '?')}")

    if paused:
        done_slots = ", ".join(e["slot"] for e in paused["exercises_done"]) or "none"
        print(f"  ⏸  Paused session from {paused['date']}  (done: {done_slots})")

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print()
    print("╔════════════════════════════════════════════╗")
    print("║       W O R K O U T   T R A C K E R       ║")
    print("╚════════════════════════════════════════════╝")

    data = store.load_data()

    while True:
        print()
        hr("═")
        _show_status(data.get("current_meso"), data.get("paused_session"))
        hr("═")
        print("  [1]  Start workout")
        print("  [2]  New mesocycle")
        print("  [3]  View history")
        print("  [0]  Exit")
        hr("═")

        choice = input("  > ").strip()

        if choice == "1":
            data = run_session(data)
            _save(data)
        elif choice == "2":
            data = start_new_meso(data)
            _save(data)
        elif choice == "3":
            view_history(data)
        elif choice == "0":
            print("\n  See you at the gym! 💪\n")
            sys.exit(0)


def _save(data):
    try:
        store.save_data(data)
        print(f"  Saved → {store.DATA_PATH}")
    except Exception as e:
        print(f"  ✗ Save failed: {e}")


if __name__ == "__main__":
    main()
