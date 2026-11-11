"""Batter performance analysis: pressure vs own baseline, plus per-match records.

Keyed strictly on striker_id (names are not unique). A batter's dismissal is
counted only when dismissed_player_id == striker_id (excludes non-striker run-outs).
"""
from __future__ import annotations
import numpy as np
import pandas as pd


def _bat_metrics(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["faced"] = df["batter_faced"]
    df["own_dismissal"] = (df["is_wicket_bool"] &
                           (df["dismissed_player_id"] == df["striker_id"])).astype(int)
    g = df.groupby("striker_id")
    out = g.agg(
        balls=("faced", "sum"),
        runs=("bat_runs", "sum"),
        dismissals=("own_dismissal", "sum"),
        fours=("is_four", "sum"),
        sixes=("is_six", "sum"),
        dots=("dot_ball", "sum"),
        matches=("match_id", "nunique"),
    )
    out["strike_rate"] = np.where(out["balls"] > 0, 100 * out["runs"] / out["balls"], np.nan)
    out["average"] = np.where(out["dismissals"] > 0, out["runs"] / out["dismissals"], np.nan)
    out["dot_pct"] = np.where(out["balls"] > 0, 100 * out["dots"] / out["balls"], np.nan)
    out["boundary_pct"] = np.where(out["balls"] > 0,
                                   100 * (out["fours"] + out["sixes"]) / out["balls"], np.nan)
    return out


def batter_table(d: pd.DataFrame) -> pd.DataFrame:
    """One row per batter with pressure & baseline metrics side by side."""
    faced = d[d["batter_faced"] == 1].copy()
    pres = faced[faced["is_bat_pressure"] == 1]
    base = faced[faced["is_bat_pressure"] == 0]

    P = _bat_metrics(pres).add_prefix("p_")
    B = _bat_metrics(base).add_prefix("b_")
    names = d.groupby("striker_id")["striker_name"].agg(lambda s: s.mode().iat[0])
    ipl = d.groupby("striker_id")["is_ipl"].mean().rename("ipl_share")

    t = pd.concat([P, B], axis=1).join(names).join(ipl).reset_index()
    t = t.rename(columns={"striker_name": "player"})
    # uplifts (pressure minus baseline)
    t["sr_uplift"] = t["p_strike_rate"] - t["b_strike_rate"]
    t["avg_uplift"] = t["p_average"] - t["b_average"]
    t["dot_uplift"] = t["p_dot_pct"] - t["b_dot_pct"]      # lower is better
    t["boundary_uplift"] = t["p_boundary_pct"] - t["b_boundary_pct"]
    return t


def batter_match_records(d: pd.DataFrame) -> pd.DataFrame:
    """Per (batter, match) pressure records, for match-level consistency."""
    faced = d[(d["batter_faced"] == 1) & (d["is_bat_pressure"] == 1)].copy()
    faced["own_dismissal"] = (faced["is_wicket_bool"] &
                              (faced["dismissed_player_id"] == faced["striker_id"])).astype(int)
    g = faced.groupby(["striker_id", "match_id"])
    m = g.agg(balls=("batter_faced", "sum"), runs=("bat_runs", "sum"),
              outs=("own_dismissal", "sum")).reset_index()
    m["sr"] = np.where(m["balls"] > 0, 100 * m["runs"] / m["balls"], np.nan)
    return m
