"""Central configuration for the SupeRR pressure-analytics pipeline.

All thresholds here are *defaults*; the sensitivity analysis sweeps several of them.
No player identities or expected rankings are hard-coded anywhere in this project.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA_RAW = ROOT / "6af3166e7b922_data_pack"      # proprietary pack (local only)
DATA_PROCESSED = ROOT / "data" / "processed"
OUTPUTS = ROOT / "outputs"
REPORTS = ROOT / "reports"

for _p in (DATA_PROCESSED, OUTPUTS, REPORTS):
    _p.mkdir(parents=True, exist_ok=True)

# ---- Innings / ball conventions (validated in Phase 1) ----
MAIN_INNINGS = (1, 2)                 # 3,4 = super overs, excluded
BALLS_PER_INNINGS = 120               # standard T20
# extras_type values that are NOT a legal ball (re-bowled)
NON_LEGAL_EXTRAS = {"wide", "Overstep", "other"}
# extras_type a batter does not "face" (only wides; no-ball is faced)
NOT_FACED_EXTRAS = {"wide"}
# dismissals NOT credited to the bowler
NON_BOWLER_DISMISSALS = {"RunOut", "Retire Out",
                         "Obstructing the field", "Obstracting the field"}

# ---- Phase definition (overid is 1-based) ----
POWERPLAY_OVERS = range(1, 7)         # overs 1-6
MIDDLE_OVERS = range(7, 16)           # overs 7-15
DEATH_OVERS = range(16, 21)           # overs 16-20

# ---- Pressure model defaults ----
# phase stake weights (shared by batting & bowling, different roles below)
PHASE_STAKE = {"powerplay": 0.30, "middle": 0.45, "death": 0.85}

# Batting pressure component weights (2nd innings). For 1st innings the chase
# weight is redistributed proportionally to phase + wickets.
BAT_WEIGHTS = {"phase": 0.33, "wickets": 0.30, "chase": 0.37}
# Bowling pressure component weights.
BOWL_WEIGHTS = {"phase": 0.34, "momentum": 0.33, "defend": 0.33}

# chase-demand mapping: required run rate -> [0,1]
RRR_LOW, RRR_HIGH = 7.0, 14.0         # <=7 no demand, >=14 max demand
# "dead chase" guard: needing more than this per ball (sustained) ≈ hopeless
DEAD_CHASE_RPB = 3.0                  # >3 runs/ball required => dampen pressure
# current run rate -> bowler momentum pressure
CRR_LOW, CRR_HIGH = 8.0, 12.0
# defending a chase: bowler pressure high when batting side cruising (low RRR)
DEFEND_RRR_LOW, DEFEND_RRR_HIGH = 4.0, 10.0

# pressure classification threshold on the [0,1] intensity
PRESSURE_THRESHOLD = 0.55

# ---- Eligibility (configurable; swept in sensitivity) ----
MIN_PRESSURE_BALLS_BAT = 75
MIN_PRESSURE_BALLS_BOWL = 60          # ~10 overs
MIN_PRESSURE_MATCHES = 5
MIN_BASELINE_BALLS_BAT = 150
MIN_BASELINE_BALLS_BOWL = 120

# ---- Rating weights (absolute-leaning blend) ----
# Absolute raised to 0.50 so a genuinely high-level pressure performance ("a clutch
# knock is a clutch knock") is rewarded more than relative lift. Uplift/consistency
# remain meaningful but secondary. Swept in the sensitivity analysis.
BAT_RATING = {"absolute": 0.50, "uplift": 0.30, "consistency": 0.20}
BOWL_RATING = {"absolute": 0.50, "uplift": 0.30, "consistency": 0.20}

# empirical-Bayes shrinkage strength (prior pseudo-balls) for uplift/rates
SHRINK_PRIOR_BAT = 60
SHRINK_PRIOR_BOWL = 48

IPL_COMP_IDS = {1358, 1715, 2193, 2725, 3298}   # IPL 2022-2026

# ---- Context-matched baseline ----
# Compare pressure performance to the player's OWN non-pressure performance in the
# SAME innings phase (powerplay/middle/death), reweighted to the phase mix of their
# pressure balls. Each per-phase baseline is shrunk toward the player's overall
# baseline by these prior ball counts, to control thin (esp. death-over) samples.
CTX_SHRINK_BAT = 30     # baseline balls
CTX_SHRINK_BOWL = 24    # baseline legal balls (~4 overs)

# ---- IPL availability (SECONDARY, optional view only) ----
# The PRIMARY statistical rankings are NOT filtered by nationality. We additionally
# publish an optional, clearly-labelled "IPL-availability" view that removes players
# an IPL franchise cannot sign. Nationality is INFERRED from the national team a
# player represents in T20Is — this is a data-only heuristic and is not independently
# verified (uncapped players have no T20I record and cannot be classified).
EXCLUDE_NATIONS = {"Pakistan"}
