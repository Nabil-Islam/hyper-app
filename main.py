#!/usr/bin/env python3
"""
main.py — Workout Tracker CLI
Data stored locally at ~/.workout_data.json

Commands at any prompt during a workout:
  /pause   — save progress, resume next session
  /cancel  — discard session entirely
  /done    — finish early with exercises completed so far
"""
import sys
from datetime import date

import store
import workout as wk

# ── Session control signals ───────────────────────────────────────────────────

class PauseSession(Exception):  pass
class CancelSession(Exception): pass
class FinishEarly(Exception):   pass

COMMANDS = {"/pause": PauseSession, "/cancel": CancelSession, "/done": FinishEarly}

def _check_command(raw):
    sig = COMMANDS.get(raw.strip().lower())
    if sig:
        raise sig()

# ── CLI helpers ───────────────────────────────────────────────────────────────

def hr(char="─", width=52):
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
    print("  · /pause  · /done  · /cancel  at any prompt ·")

def prompt_int(text, min_val=None, max_val=None, default=None):
    suffix = f" [{default}]" if default is not None else ""
    while True:
        raw = input(f"  {text}{suffix}: ").strip()
        _check_command(raw)
        val_str = raw if raw else (str(default) if default is not None else "")
        try:
            val = int(val_str)
        except ValueError:
            print("    ! Whole number please.")
            continue
        if min_val is not None and val < min_val:
            print(f"    ! Min is {min_val}.")
            continue
        if max_val is not None and val > max_val:
            print(f"    ! Max is {max_val}.")
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
            print("    ! Enter a number e.g. 60 or 62.5")

def confirm(text):
    raw = input(f"  {text} (y/n): ").strip()
    _check_command(raw)
    return raw.lower() == "y"

# ── Single exercise block ─────────────────────────────────────────────────────

def _run_exercise(ex_tmpl, state, rir_target, is_deload):
    section(f"{ex_tmpl['slot'].upper()}  ·  {ex_tmpl['muscle']}")

    myo_tag  = "  [MYO-REP MATCH]" if ex_tmpl.get("myo") else ""
    kind_tag = "COMPOUND" if ex_tmpl["kind"] == "compound" else "isolation"
    print(f"  [{kind_tag}]  {state['name']}{myo_tag}")
    print(f"  Reps : {ex_tmpl['rep_range']}  |  RIR target: {rir_target}")

    if ex_tmpl.get("note"):
        print(f"  Note : {ex_tmpl['note']}")

    _cmd_hint()

    new_name = input("  Rename? [ENTER to keep]: ").strip()
    _check_command(new_name)
    if new_name:
        state["name"] = new_name

    if ex_tmpl.get("myo") and not is_deload:
        print()
        print("  MYO-REP MATCH protocol:")
        print("    1. Activation set — top of rep range, ~1 RIR")
        print("    2. Rest 5-10 breaths")
        print("    3. Mini-sets — match ~30% of activation reps")
        print("    4. Stop when you can't match")

    last_w  = state.get("last_weight")
    suggest = wk.suggest_weight(last_w, ex_tmpl["incr"], is_deload)

    if last_w:
        note = f"  (deload → {suggest} kg)" if is_deload else ""
        print(f"\n  Last  : {last_w} kg × {state.get('last_reps','?')} reps{note}")
    else:
        print("\n  (No previous data — enter weight manually)")

    planned = state["sets"]
    if is_deload:
        planned = max(1, (planned + 1) // 2)
    print(f"  Sets  : {planned}")
    print()

    sets_logged = []

    if ex_tmpl.get("myo") and not is_deload:
        weight   = prompt_float("Activation weight (kg)", suggest)
        act_reps = prompt_int("Activation reps", min_val=1)
        minis    = prompt_int("Mini-sets completed", min_val=0)
        sets_logged.append({
            "type": "myo", "weight": weight,
            "activation_reps": act_reps, "mini_sets": minis,
        })
        final_weight, final_reps = weight, act_reps
    else:
        cur_suggest = suggest
        set_num = 0
        while True:
            set_num += 1
            print(f"  Set {set_num}:")
            w = prompt_float("    Weight (kg)", cur_suggest)
            r = prompt_int("    Reps", min_val=0)
            sets_logged.append({"set": set_num, "weight": w, "reps": r})
            cur_suggest = w
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
    print(f"\n  — Biofeedback: {ex_tmpl['muscle'].upper()} —")
    pump     = prompt_int("  Pump?     0=yes  1=no", min_val=0, max_val=1)
    soreness = prompt_int(
        "  Soreness? -1=didn't recover  0=just in time  1=wasn't sore",
        min_val=-1, max_val=1,
    )
    adj = wk.compute_set_adjustment(pump, soreness)
    print(f"  {wk.biofeedback_message(adj)}")
    state["sets"] = max(1, min(8, state["sets"] + adj))

    return state, {
        "slot":           ex_tmpl["slot"],
        "name":           state["name"],
        "muscle":         ex_tmpl["muscle"],
        "kind":           ex_tmpl["kind"],
        "myo":            ex_tmpl.get("myo", False),
        "sets":           sets_logged,
        "biofeedback":    {"pump": pump, "soreness": soreness},
        "set_adjustment": adj,
    }

# ── Session runner ────────────────────────────────────────────────────────────

def run_session(data):
    meso = data.get("current_meso")
    if not meso:
        print("\n  No active meso — start one first (option 2).")
        return data
    if meso.get("deload_done"):
        print("\n  Deload complete! Start a fresh mesocycle (option 2).")
        return data

    # Resume paused?
    paused = data.get("paused_session")
    if paused:
        print()
        hr("═")
        done_str = ", ".join(e["slot"] for e in paused["exercises_done"]) or "none"
        left_str = ", ".join(r["slot"] for r in paused["exercises_remaining"])
        print(f"  ⏸  Paused session from {paused['date']}")
        print(f"     Done      : {done_str}")
        print(f"     Remaining : {left_str}")
        hr("═")
        choice = input("  Resume (r)  ·  Discard & start fresh (s)  ·  Back (b): ").strip().lower()
        if choice == "b":
            return data
        if choice == "r":
            return _resume_session(data, paused, meso)
        data.pop("paused_session", None)
        print("  Paused session discarded.")

    is_deload  = meso.get("is_deload", False)
    rir_target = wk.get_current_rir(meso)
    day_key, day_data = wk.get_next_session(meso)

    session_num = meso["session_number"] + 1
    header(f"Session {session_num}  ·  {day_data['name']}")

    if is_deload:
        print("  🔄  DELOAD — ~50% sets  ·  ~90% weight  ·  perfect form, no grinding")
        rir_target = 4
    else:
        rir_str = "  →  ".join(str(r) for r in meso["rir_plan"]) + "  →  Deload"
        print(f"  Week {meso['current_week']} of {meso['total_weeks']}  "
              f"|  RIR today: {rir_target}  |  {rir_str}")
    print()

    exercises = day_data["exercises"]
    return _run_exercises(
        data, meso, day_key, exercises, session_num,
        rir_target, is_deload, exercises_done=[], start_index=0,
    )


def _resume_session(data, paused, meso):
    is_deload   = paused.get("is_deload", False)
    rir_target  = paused.get("rir_target", wk.get_current_rir(meso))
    session_num = paused["session_n"]
    day_key     = paused["day_key"]
    done_keys   = {e["slot"] for e in paused["exercises_done"]}

    all_exercises = wk.SESSIONS[day_key]["exercises"]
    remaining     = [e for e in all_exercises if e["slot"] not in done_keys]

    header(f"Session {session_num} (resumed)  ·  {wk.SESSIONS[day_key]['name']}")
    _cmd_hint()

    return _run_exercises(
        data, meso, day_key, remaining, session_num,
        rir_target, is_deload,
        exercises_done=paused["exercises_done"],
        start_index=len(paused["exercises_done"]),
        session_date=paused["date"],
    )


def _run_exercises(data, meso, day_key, exercises, session_num,
                   rir_target, is_deload, exercises_done,
                   start_index=0, session_date=None):
    if session_date is None:
        session_date = str(date.today())

    ex_state   = meso["exercise_state"]
    session_log = list(exercises_done)
    remaining   = list(exercises)

    for ex_tmpl in exercises:
        remaining = [e for e in remaining if e["slot"] != ex_tmpl["slot"]]
        key = ex_tmpl["key"]

        try:
            ex_state[key], log = _run_exercise(
                ex_tmpl, ex_state[key], rir_target, is_deload
            )
            session_log.append(log)

        except PauseSession:
            data["paused_session"] = {
                "date":                session_date,
                "session_n":           session_num,
                "rir_target":          rir_target,
                "is_deload":           is_deload,
                "day_key":             day_key,
                "exercises_done":      session_log,
                "exercises_remaining": [{"slot": e["slot"], "key": e["key"]} for e in remaining],
            }
            print("\n  ⏸  Paused. Progress saved — resume next time you start a workout.")
            return data

        except CancelSession:
            data.pop("paused_session", None)
            print("\n  ✗  Session cancelled. Nothing saved.")
            return data

        except FinishEarly:
            if not session_log:
                print("  Nothing completed — session not saved.")
                return data
            print(f"\n  Finishing early — saving {len(session_log)} exercise(s).")
            break

    # Commit session
    data.pop("paused_session", None)
    data["sessions"].append({
        "date":       session_date,
        "session_n":  session_num,
        "day":        day_key,
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
        print("  ✓  Deload done. Start a fresh mesocycle (option 2).")
    elif new_meso.get("is_deload") and not meso.get("is_deload"):
        print("  ✓  Accumulation done! Next up: DELOAD week.")
    else:
        nk, nd = wk.get_next_session(new_meso)
        print(f"  ✓  Session logged! Next: {nd['name']}")
    hr("═")

    return data

# ── New meso wizard ───────────────────────────────────────────────────────────

def start_new_meso(data):
    header("NEW MESOCYCLE  —  Cut Protocol")
    print("  Recommended: 3 weeks (cut-optimised — shorter mesos, higher RIR start)")
    print("  Longer options available if you want to experiment.")
    print()
    weeks = prompt_int("Accumulation weeks (3 / 4 / 5)", min_val=3, max_val=5, default=3)
    meso  = wk.new_meso(weeks)
    data["current_meso"] = meso
    data.pop("paused_session", None)

    rir_str = "  →  ".join(str(r) for r in meso["rir_plan"]) + "  →  Deload"
    _, first_day = wk.get_next_session(meso)

    print(f"\n  ✓  Mesocycle created!")
    print(f"     Duration   : {weeks} weeks + 1 deload week")
    print(f"     RIR plan   : {rir_str}")
    print(f"     Sets/start : compounds {wk.INITIAL_SETS['compound']}  ·  isolations {wk.INITIAL_SETS['isolation']}")
    print(f"     Session 1  : {first_day['name']}")
    print()
    print("  Protein target (GLP-1 + cut — most important number):")
    print("  ┌─────────────────────────────────────────────────┐")
    print("  │  200-220g protein daily                         │")
    print("  │  At your calorie target, fill protein FIRST     │")
    print("  │  then carbs (around training), then fats        │")
    print("  └─────────────────────────────────────────────────┘")
    print()
    print("  RP volume landmarks (sets/muscle/week):")
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

    n = min(len(sessions), 10)
    print(f"\n  Last {n} sessions:\n")
    for s in sessions[-n:]:
        tag = " [DELOAD]" if s.get("is_deload") else ""
        print(f"  {s['date']}  {s.get('day','?').upper():<10}  "
              f"Session {s['session_n']}  Week {s['week']}  RIR {s['rir_target']}{tag}")
        for ex in s["exercises"]:
            sets = ex["sets"]
            if sets and sets[0].get("type") == "myo":
                s0 = sets[0]
                summary = f"{s0['weight']}kg × {s0['activation_reps']} + {s0['mini_sets']} minis"
            else:
                summary = "  ".join(f"{st['weight']}×{st['reps']}" for st in sets)
            adj = {1: "↑", -1: "↓", 0: "="}.get(ex.get("set_adjustment", 0), "")
            kind = "C" if ex.get("kind") == "compound" else "i"
            print(f"    [{kind}] {ex['name']:<30} {summary} {adj}")
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
        print(f"  🔄  DELOAD WEEK  (session {meso['session_number'] + 1})")
    else:
        rir = wk.get_current_rir(meso)
        plan_str = "  →  ".join(str(r) for r in meso["rir_plan"]) + "  →  Deload"
        print(f"  Week {meso['current_week']} of {meso['total_weeks']}  "
              f"|  RIR {rir}  |  {plan_str}")

    _, nd = wk.get_next_session(meso)
    print(f"  Next   : {nd['name']}  (session {meso['session_number'] + 1})")
    print(f"  Started: {meso.get('start_date','?')}")

    if paused:
        done = ", ".join(e["slot"] for e in paused["exercises_done"]) or "none"
        print(f"  ⏸  Paused session ({paused['date']}) — done: {done}")

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print()
    print("╔══════════════════════════════════════════════╗")
    print("║        W O R K O U T   T R A C K E R        ║")
    print("║     Upper / Lower  ·  Cut Protocol           ║")
    print("╚══════════════════════════════════════════════╝")

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
