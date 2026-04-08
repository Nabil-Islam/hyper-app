# Workout Tracker

A minimal terminal-based Push / Pull / Legs tracker.
Data lives in a GitHub repo — pull it up on any machine with a terminal.

---

## Setup (one time)

### 1. Create a GitHub repo

Create a new **private** repo (e.g. `my-workouts`) on GitHub.  
It can be completely empty — the app will create `workout_data.json` on first save.

### 2. Create a GitHub token

Go to **GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)**.  
Generate a new token with the **`repo`** scope.  
Copy it — you'll only see it once.

### 3. Install Python dependency

```bash
pip install -r requirements.txt
```

### 4. Run

```bash
python main.py
```

On first run you'll be prompted for your GitHub username, token, and repo name.  
Config is stored at `~/.workout_tracker_config.json` on each machine.

---

## Daily use

```
python main.py
```

```
╔══════════════════════════════════════════════╗
║        W O R K O U T   T R A C K E R        ║
║          Push · Pull · Legs  v1.0            ║
╚══════════════════════════════════════════════╝

  Status   : Week 2 of 4  (RIR target: 3)
  RIR plan : 3 → 3 → 2 → 1 → Deload
  Next day : Push 1 — Chest · Triceps · Shoulder

  [1]  Start workout
  [2]  New mesocycle
  [3]  View history
  [4]  Reconnect / reconfigure GitHub
  [0]  Exit
```

---

## The PPL split

| Day    | Focus              | Exercises                                    |
|--------|--------------------|----------------------------------------------|
| Push 1 | Chest + Tris       | Barbell Bench, Overhead Extension, Lateral Raise |
| Pull 1 | Horizontal Back    | Barbell Row, Barbell Curl, Face Pull          |
| Legs 1 | Quad focus         | Squat, Leg Curl (light), Hip Thrust           |
| Push 2 | Incline Chest      | Incline Press, Pushdown, Rear Delt Fly        |
| Pull 2 | Vertical Back      | Lat Pulldown, Incline DB Curl, Band Pull-Apart |
| Legs 2 | Hamstring focus    | SLDL, Leg Extension (light), RDL, Calf Raise  |

You can rename any exercise on the fly during the session prompt.

---

## Mesocycle structure

Start with: **2 sets** for large muscles, **3 sets** for small muscles.

| Duration | RIR progression           |
|----------|---------------------------|
| 3 weeks  | 3 → 2 → 1 → Deload        |
| 4 weeks  | 3 → 3 → 2 → 1 → Deload    |
| 5 weeks  | 3 → 3 → 2 → 2 → 1 → Deload |

Sets adjust automatically based on biofeedback after each exercise.

---

## Biofeedback

After each exercise you'll be asked:

```
Pump?      0 = yes (got a pump)       1 = no (barely felt it)
Soreness?  -1 = didn't recover        0 = recovered just in time
            1 = wasn't sore at all
```

| Pump | Soreness | Result              |
|------|----------|---------------------|
| yes  | 1        | +1 set next session |
| yes  | 0        | +1 set next session |
| yes  | -1       | = maintain          |
| no   | 0 / 1    | = maintain          |
| no   | -1       | -1 set next session |

---

## Myo-rep match sets (small muscles)

Small muscles (triceps, biceps, shoulders, glutes, calves) are logged as myo-rep match sets:

1. **Activation set** — go to ~1 RIR at the top of the rep range
2. **Rest** — 5-10 breaths
3. **Mini sets** — match ≈ 30 % of activation reps; repeat until failure to match
4. Log: activation reps + number of mini sets

---

## Accessing on another machine

```bash
git clone  # not needed — the app fetches/pushes directly via the GitHub API
pip install -r requirements.txt
python main.py
# enter your GitHub username, token, and repo name again
```

Your `~/.workout_tracker_config.json` stores credentials locally.  
All data is fetched live from GitHub on startup.
