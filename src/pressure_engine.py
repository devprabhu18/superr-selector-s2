"""Pressure engine — converts match state into per-delivery pressure intensity.

Two SEPARATE, asymmetric models (per the brief: a batting team under pressure is
not the same as a bowling team under pressure):

  BATTING pressure rises with: death overs, wickets already lost, and a HIGH
    required run rate (hard chase) — but a hopeless ("dead") chase is dampened,
    because scoring in garbage time is not a fair clutch test.

  BOWLING pressure rises with: death overs, batters SET and scoring freely
    (high current run rate / many wickets in hand), and defending a gettable
    chase (LOW required run rate = batting side cruising, bowler must break through).

All signals are normalised to [0,1]; the composite is a documented weighted blend.
Several alternative definitions are provided for the sensitivity analysis.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
import config as C


def _ramp(x, lo, hi):
    """Linear ramp: <=lo -> 0, >=hi -> 1."""
    return np.clip((x - lo) / (hi - lo), 0.0, 1.0)


def _phase_stake(phase, stake=None):
    stake = stake or C.PHASE_STAKE
    return phase.map(stake).astype(float)


def batting_pressure(d: pd.DataFrame, weights=None, phase_stake=None,
                     rrr_lo=None, rrr_hi=None) -> pd.Series:
    w = weights or C.BAT_WEIGHTS
    rrr_lo = C.RRR_LOW if rrr_lo is None else rrr_lo
    rrr_hi = C.RRR_HIGH if rrr_hi is None else rrr_hi

    s_phase = _phase_stake(d["phase"], phase_stake)
    s_wkts = np.clip(d["wkts_before"] / 6.0, 0, 1)        # 6 down saturates

    # chase demand (2nd innings only, live chases)
    s_chase = _ramp(d["req_run_rate"], rrr_lo, rrr_hi)
    # dampen dead / already-won chases
    alive = np.where((d["chase_dead"] == 1) | (d["chase_won"] == 1), 0.25, 1.0)
    s_chase = np.where(d["innings"] == 2, s_chase * alive, 0.0)

    out = np.empty(len(d))
    is2 = (d["innings"] == 2).to_numpy()
    # 2nd innings: full blend
    out2 = w["phase"] * s_phase + w["wickets"] * s_wkts + w["chase"] * s_chase
    # 1st innings: redistribute chase weight to phase+wickets
    denom = w["phase"] + w["wickets"]
    out1 = ((w["phase"] + w["chase"] * w["phase"] / denom) * s_phase +
            (w["wickets"] + w["chase"] * w["wickets"] / denom) * s_wkts)
    out = np.where(is2, out2, out1)
    return pd.Series(np.clip(out, 0, 1), index=d.index)


def bowling_pressure(d: pd.DataFrame, weights=None, phase_stake=None) -> pd.Series:
    w = weights or C.BOWL_WEIGHTS
    s_phase = _phase_stake(d["phase"], phase_stake)

    # batting momentum: batters scoring fast + many wickets in hand => bowler pressure
    s_crr = _ramp(d["current_rr"].fillna(0), C.CRR_LOW, C.CRR_HIGH)
    s_resource = np.clip(d["wkts_in_hand"] / 10.0, 0, 1)
    s_momentum = 0.65 * s_crr + 0.35 * s_resource

    # defending a chase: pressure high when batting side cruising (low RRR), alive game
    s_defend_raw = 1.0 - _ramp(d["req_run_rate"], C.DEFEND_RRR_LOW, C.DEFEND_RRR_HIGH)
    alive = np.where((d["chase_dead"] == 1) | (d["chase_won"] == 1), 0.3, 1.0)
    s_defend = np.where(d["innings"] == 2, s_defend_raw * alive, 0.0)

    is2 = (d["innings"] == 2).to_numpy()
    out2 = w["phase"] * s_phase + w["momentum"] * s_momentum + w["defend"] * s_defend
    # 1st innings: no chase; redistribute defend weight to phase+momentum
    denom = w["phase"] + w["momentum"]
    out1 = ((w["phase"] + w["defend"] * w["phase"] / denom) * s_phase +
            (w["momentum"] + w["defend"] * w["momentum"] / denom) * s_momentum)
    out = np.where(is2, out2, out1)
    return pd.Series(np.clip(out, 0, 1), index=d.index)


# ---- alternative definitions for sensitivity ----
def batting_pressure_chase_centric(d):
    """Def B: chase-driven, RRR-heavy, lighter on phase."""
    return batting_pressure(d, weights={"phase": 0.15, "wickets": 0.20, "chase": 0.65})


def batting_pressure_death_collapse(d):
    """Def C: no RRR (robust to approximate target) — phase + wickets only."""
    return batting_pressure(d, weights={"phase": 0.55, "wickets": 0.45, "chase": 0.0})


def bowling_pressure_death_heavy(d):
    return bowling_pressure(d, weights={"phase": 0.55, "momentum": 0.30, "defend": 0.15})


def bowling_pressure_defend_heavy(d):
    return bowling_pressure(d, weights={"phase": 0.20, "momentum": 0.30, "defend": 0.50})


def add_pressure(d: pd.DataFrame, threshold=None) -> pd.DataFrame:
    threshold = C.PRESSURE_THRESHOLD if threshold is None else threshold
    d = d.copy()
    d["bat_pressure"] = batting_pressure(d)
    d["bowl_pressure"] = bowling_pressure(d)
    d["is_bat_pressure"] = (d["bat_pressure"] >= threshold).astype(int)
    d["is_bowl_pressure"] = (d["bowl_pressure"] >= threshold).astype(int)
    return d


if __name__ == "__main__":
    import data_loader, match_state
    d = match_state.add_match_state(data_loader.build_deliveries())
    d = add_pressure(d)
    print("batting pressure share:", d["is_bat_pressure"].mean().round(3))
    print("bowling pressure share:", d["is_bowl_pressure"].mean().round(3))
    print(d.groupby("phase")[["bat_pressure", "bowl_pressure"]].mean().round(3))
