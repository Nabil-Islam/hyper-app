#!/usr/bin/env python3
"""
main.py — Workout Tracker CLI

Usage:
    python main.py

On first run you'll be prompted for your GitHub credentials.
All data is stored in workout_data.json in your chosen GitHub repo.
"""

import sys
from datetime import date

import config as cfg_module
import store
import workout as wk

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


def prompt(text, default=None):
    suffix = f" [{default}]" if default is not None else ""
    val = input(f"  {text}{suffix}: ").strip()
    return val if val else (str(default) if default is not None else "")


def prompt_int(text, min_val=None, max_val=None, default=None):
    while True:
        raw = prompt(text, default)
        try:
            val = int(raw)
        except ValueError:
            print("    ! Enter a whole number.")
            continue
        if min_val is not None and val < min_val:
            print(f"    ! Minimum is {min_val}.")
            continue
        if max_val is not None and val > max_val:
            print(f"    ! Maximum is {max_val}.")
            continue
        return val


def prompt_float(text, default=None):
    while True:
        raw = prompt(text, default)
        try:
            return float(raw)
        except ValueError:
            print("    ! Enter a number (e.g. 80 or 82.5).")


def confirm(text):
    return input(f"  {text} (y/n): ").strip().lower() == "y"


# ── Workout session runner ────────────────────────────────────────────────────

def run_session(data):
    meso = data.get("current_meso")
    if not meso:
        print("\n  No active meso — start one first (option 2).")
        return data

    if meso.get("deload_done"):
        print("\n  Deload complete! Start a fresh mesocycle (option 2).")
        return data

    day_key  = wk.get_next_day(meso)
    day_tmpl = wk.WORKOUT_TEMPLATE[day_key]
    is_deload = meso.get("is_deload", False)
    rir_target = wk.get_current_rir(meso)

    # ── Session header ────────────────────────────────────────────────────────
    header(day_tmpl["name"])
    if is_deload:
        print("  🔄  DELOAD WEEK")
        print("      ~50 % of normal sets · weight stays same or drops 10 %")
        print("      Focus: movement quality, full recovery")
        rir_target = 4
    else:
        rir_str = " → ".join(str(r) for r in meso["rir_plan"]) + " → Deload"
        print(f"  Week {meso['current_week']} of {meso['total_weeks']}  |  "
              f"RIR target today: {rir_target}  |  Plan: {rir_str}")
    print()

    session_log = []

    for ex_tmpl in day_tmpl["exercises"]:
        slot = ex_tmpl["slot"]
        ex_state = meso["exercise_state"][day_key][slot]

        # ── Exercise header ───────────────────────────────────────────────────
        section(slot.upper())
        myo_tag = "  [MYO-REP MATCH]" if ex_tmpl["myo"] else ""
        print(f"  Exercise : {ex_state['name']}{myo_tag}")
        print(f"  Muscle   : {ex_tmpl['muscle']}  ({ex_tmpl['size']} muscle)")
        print(f"  Rep range: {ex_tmpl['rep_range']}")

        # Allow renaming on the fly
        new_name = input(f"  Rename exercise? [ENTER to keep]: ").strip()
        if new_name:
            ex_state["name"] = new_name

        # ── Myo-rep match explanation ─────────────────────────────────────────
        if ex_tmpl["myo"] and not is_deload:
            print()
            print("  MYO-REP MATCH protocol:")
            print("    1. Activation set  — hit the upper end of rep range (hard, ~1 RIR)")
            print("    2. Rest 5-10 breaths")
            print("    3. Mini sets       — aim to match ≈ 30 % of activation reps each")
            print("    4. Stop when you can't match anymore")
            print("    Track: activation reps + how many mini sets you completed")

        # ── Weight suggestion ─────────────────────────────────────────────────
        last_w  = ex_state.get("last_weight")
        suggest = wk.suggest_weight(last_w, ex_tmpl["incr"])

        if last_w:
            print(f"\n  Last session : {last_w} kg  ×  {ex_state.get('last_reps', '?')} reps")
        else:
            print("\n  (No previous data — enter weight manually)")

        # ── Planned set count ─────────────────────────────────────────────────
        planned_sets = ex_state["sets"]
        if is_deload:
            planned_sets = max(1, (planned_sets + 1) // 2)
        print(f"  Sets planned : {planned_sets}")
        print()

        sets_logged = []
        final_weight = last_w  # fallback for state update

        # ── MYO-REP branch ────────────────────────────────────────────────────
        if ex_tmpl["myo"] and not is_deload:
            # One activation set
            w_prompt = f"Activation set weight (kg)" + (f" [suggest {suggest}]" if suggest else "")
            if suggest:
                raw = input(f"  {w_prompt}: ").strip()
                weight = float(raw) if raw else suggest
            else:
                weight = prompt_float("Activation set weight (kg)")

            act_reps = prompt_int("  Activation set reps", min_val=1)
            mini_sets = prompt_int("  Mini sets completed", min_val=0)

            sets_logged.append({
                "type": "myo",
                "weight": weight,
                "activation_reps": act_reps,
                "mini_sets": mini_sets,
            })
            final_weight = weight
            final_reps = act_reps

        # ── Regular sets branch ───────────────────────────────────────────────
        else:
            set_num = 0
            current_suggest = suggest

            while True:
                set_num += 1
                print(f"  Set {set_num}:")

                if current_suggest is not None:
                    raw = input(f"    Weight (kg) [suggest {current_suggest}]: ").strip()
                    weight = float(raw) if raw else current_suggest
                else:
                    weight = prompt_float("    Weight (kg)")

                reps = prompt_int("    Reps completed", min_val=0)

                sets_logged.append({"set": set_num, "weight": weight, "reps": reps})
                current_suggest = weight  # keep same weight unless changed

                if set_num < planned_sets:
                    continue  # still working through planned sets

                # Planned sets done — offer to add more
                if not is_deload and confirm("  Add another set?"):
                    continue
                break

            final_weight = sets_logged[-1]["weight"]
            final_reps   = sets_logged[-1]["reps"]

        # Update state for next session
        ex_state["last_weight"] = final_weight
        ex_state["last_reps"]   = final_reps

        # ── Biofeedback ───────────────────────────────────────────────────────
        print(f"\n  — Biofeedback: {ex_tmpl['muscle'].upper()} —")
        pump     = prompt_int("  Pump?     (0=yes / 1=no)",                              min_val=-1, max_val=1)
        soreness = prompt_int("  Soreness? (-1=didn't recover / 0=just in time / 1=wasn't sore)", min_val=-1, max_val=1)

        adj = wk.compute_set_adjustment(pump, soreness)
        print(f"  {wk.biofeedback_message(adj)}")

        # Apply set adjustment (clamp between 1 and 8)
        ex_state["sets"] = max(1, min(8, ex_state["sets"] + adj))

        session_log.append({
            "slot": slot,
            "name": ex_state["name"],
            "muscle": ex_tmpl["muscle"],
            "size": ex_tmpl["size"],
            "myo": ex_tmpl["myo"],
            "sets": sets_logged,
            "biofeedback": {"pump": pump, "soreness": soreness},
            "set_adjustment": adj,
        })

    # ── Save session ──────────────────────────────────────────────────────────
    if "sessions" not in data:
        data["sessions"] = []

    data["sessions"].append({
        "date": str(date.today()),
        "day": day_key,
        "week": meso["current_week"],
        "rir_target": rir_target,
        "is_deload": is_deload,
        "exercises": session_log,
    })

    data["current_meso"] = wk.advance_day(meso)
    new_meso = data["current_meso"]

    print()
    hr("═")
    if new_meso.get("deload_done"):
        print("  ✓  Deload week complete! Start a new mesocycle (option 2).")
    elif new_meso.get("is_deload") and new_meso["next_day_index"] == 0:
        print("  ✓  Accumulation done! Next up: DELOAD")
    else:
        next_day = wk.get_next_day(new_meso)
        print(f"  ✓  Session logged! Next up: {wk.WORKOUT_TEMPLATE[next_day]['name']}")
    hr("═")

    return data


# ── New meso wizard ───────────────────────────────────────────────────────────

def start_new_meso(data):
    header("NEW MESOCYCLE")
    weeks = prompt_int("How many accumulation weeks? (3 / 4 / 5)", min_val=3, max_val=5, default=4)
    meso  = wk.new_meso(weeks)
    data["current_meso"] = meso

    rir_str = " → ".join(str(r) for r in meso["rir_plan"]) + " → Deload"
    print()
    print(f"  ✓  Mesocycle created!")
    print(f"     Duration   : {weeks} accumulation weeks + 1 deload")
    print(f"     RIR plan   : {rir_str}")
    print(f"     Start sets : large muscles = {wk.INITIAL_SETS['large']}, "
          f"small muscles = {wk.INITIAL_SETS['small']}")
    print(f"     First day  : {wk.WORKOUT_TEMPLATE[wk.get_next_day(meso)]['name']}")
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
        print(f"  {s['date']}  |  {s['day']}  |  "
              f"Week {s['week']}  |  RIR {s['rir_target']}{tag}")
        for ex in s["exercises"]:
            sets = ex["sets"]
            if sets and sets[0].get("type") == "myo":
                s0 = sets[0]
                summary = (f"{s0['weight']} kg × {s0['activation_reps']} "
                           f"+ {s0['mini_sets']} mini-sets [myo]")
            else:
                summary = "  ".join(
                    f"{st['weight']} kg×{st['reps']}" for st in sets
                )
            adj_sym = {1: "↑", -1: "↓", 0: "="}.get(ex.get("set_adjustment", 0), "")
            print(f"    • {ex['name']:<30} {summary} {adj_sym}")
        print()


# ── Meso status ───────────────────────────────────────────────────────────────

def _show_status(meso):
    if not meso:
        print("  No active mesocycle.")
        return
    if meso.get("deload_done"):
        print("  Meso complete — start a new one! (option 2)")
        return
    if meso.get("is_deload"):
        print(f"  Status   : DELOAD WEEK  (week {meso['current_week']})")
    else:
        rir = wk.get_current_rir(meso)
        print(f"  Status   : Week {meso['current_week']} of {meso['total_weeks']}  "
              f"(RIR target: {rir})")
    plan_str = " → ".join(str(r) for r in meso["rir_plan"]) + " → Deload"
    next_name = wk.WORKOUT_TEMPLATE[wk.get_next_day(meso)]["name"]
    print(f"  RIR plan : {plan_str}")
    print(f"  Next day : {next_name}")
    print(f"  Started  : {meso.get('start_date', '?')}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print()
    print("╔══════════════════════════════════════════════╗")
    print("║        W O R K O U T   T R A C K E R        ║")
    print("║          Push · Pull · Legs  v1.0            ║")
    print("╚══════════════════════════════════════════════╝")

    # Config
    cfg = cfg_module.load_config()
    if not cfg or not cfg.get("github_token"):
        cfg = cfg_module.setup_config()

    # Load data
    print("\n  Connecting to GitHub...", end="", flush=True)
    try:
        data, sha = store.load_data(cfg)
        print(" ✓")
    except Exception as e:
        print(f"\n  ✗  Could not load data: {e}")
        sys.exit(1)

    if not data:
        data = {"sessions": [], "current_meso": None}

    # sha wrapped in a list so inner helpers can mutate it
    state = {"sha": sha}

    def autosave():
        print("  Saving to GitHub...", end="", flush=True)
        try:
            state["sha"] = store.save_data(cfg, data, state["sha"])
            print(" ✓")
        except Exception as e:
            print(f"\n  ✗ Save failed: {e}")
            print("    Session is in memory but NOT on GitHub. Check token/repo.")

    # Main loop
    while True:
        print()
        hr("═")
        _show_status(data.get("current_meso"))
        hr("═")
        print("  [1]  Start workout")
        print("  [2]  New mesocycle")
        print("  [3]  View history")
        print("  [4]  Reconnect / reconfigure GitHub")
        print("  [0]  Exit")
        hr("═")

        choice = input("  > ").strip()

        if choice == "1":
            data = run_session(data)
            autosave()

        elif choice == "2":
            data = start_new_meso(data)
            autosave()

        elif choice == "3":
            view_history(data)

        elif choice == "4":
            cfg = cfg_module.setup_config()
            try:
                data, state["sha"] = store.load_data(cfg)
                print("  ✓ Reconnected.")
            except Exception as e:
                print(f"  ✗ {e}")

        elif choice == "0":
            print("\n  See you at the gym! 💪\n")
            sys.exit(0)


if __name__ == "__main__":
    main()
