"""Bowler performance analysis: pressure vs own baseline, plus per-match records.

Keyed strictly on bowler_id. Wickets are bowler-credited only (run-outs etc.
excluded upstream). Economy uses runs charged to the bowler (off-bat + wides +
no-balls + extras_2); byes/leg-byes are not charged to the bowler.
"""
from __future__ import annotations
import numpy as np
import pandas as pd


def _bowl_metrics(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["bowl_dot"] = ((df["bowler_runs"] == 0) & (df["is_legal"] == 1)).astype(int)
    g = df.groupby("bowler_id")
    out = g.agg(
        legal_balls=("is_legal", "sum"),
        runs=("bowler_runs", "sum"),
        wickets=("bowler_wicket", "sum"),
        dots=("bowl_dot", "sum"),
        fours=("is_four", "sum"),
        sixes=("is_six", "sum"),
        matches=("match_id", "nunique"),
    )
    out["economy"] = np.where(out["legal_balls"] > 0, 6 * out["runs"] / out["legal_balls"], np.nan)
    out["strike_rate"] = np.where(out["wickets"] > 0, out["legal_balls"] / out["wickets"], np.nan)
    out["wkt_rate_over"] = np.where(out["legal_balls"] > 0, 6 * out["wickets"] / out["legal_balls"], np.nan)
    out["dot_pct"] = np.where(out["legal_balls"] > 0, 100 * out["dots"] / out["legal_balls"], np.nan)
    out["boundary_pct"] = np.where(out["legal_balls"] > 0,
                                   100 * (out["fours"] + out["sixes"]) / out["legal_balls"], np.nan)
    return out


def bowler_table(d: pd.DataFrame) -> pd.DataFrame:
    pres = d[d["is_bowl_pressure"] == 1]
    base = d[d["is_bowl_pressure"] == 0]
    P = _bowl_metrics(pres).add_prefix("p_")
    B = _bowl_metrics(base).add_prefix("b_")
    names = d.groupby("bowler_id")["bowler_name"].agg(lambda s: s.mode().iat[0])
    ipl = d.groupby("bowler_id")["is_ipl"].mean().rename("ipl_share")
    paceflag = d.groupby("bowler_id")["pace_or_spin"].agg(lambda s: s.mode().iat[0])

    t = pd.concat([P, B], axis=1).join(names).join(ipl).join(paceflag).reset_index()
    t = t.rename(columns={"bowler_name": "player"})
    # uplifts: for bowlers, improvement = baseline - pressure for econ (lower better)
    t["econ_uplift"] = t["b_economy"] - t["p_economy"]           # positive = better under pressure
    t["wkt_rate_uplift"] = t["p_wkt_rate_over"] - t["b_wkt_rate_over"]
    t["dot_uplift"] = t["p_dot_pct"] - t["b_dot_pct"]           # higher = better
    t["boundary_uplift"] = t["b_boundary_pct"] - t["p_boundary_pct"]  # positive = better
    return t


def bowler_match_records(d: pd.DataFrame) -> pd.DataFrame:
    pres = d[d["is_bowl_pressure"] == 1].copy()
    pres["bowl_dot"] = ((pres["bowler_runs"] == 0) & (pres["is_legal"] == 1)).astype(int)
    g = pres.groupby(["bowler_id", "match_id"])
    m = g.agg(legal_balls=("is_legal", "sum"), runs=("bowler_runs", "sum"),
              wickets=("bowler_wicket", "sum"), dots=("bowl_dot", "sum")).reset_index()
    m["economy"] = np.where(m["legal_balls"] > 0, 6 * m["runs"] / m["legal_balls"], np.nan)
    return m
