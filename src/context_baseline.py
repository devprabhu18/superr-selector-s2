"""Context-matched baseline — control for innings-phase bias.

The pooled personal baseline mixes all phases, but pressure balls are heavily
death-weighted, so part of a raw pressure-vs-baseline uplift is just the
death-over environment. Here we reweight each player's OWN non-pressure
performance to the phase mix of their pressure balls, with each per-phase
baseline shrunk toward the player's overall baseline (death-over non-pressure
samples are tiny, so shrinkage keeps the estimate honest).

apply_bat / apply_bowl take a built metrics table + the deliveries and return a
copy with phase-matched baselines and recomputed uplifts.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
import config as C


def matched_batter(d: pd.DataFrame, k: int | None = None) -> pd.DataFrame:
    k = C.CTX_SHRINK_BAT if k is None else k
    f = d[d["batter_faced"] == 1]
    base = f[f["is_bat_pressure"] == 0]
    pres = f[f["is_bat_pressure"] == 1]

    bp = (base.groupby(["striker_id", "phase"])
          .agg(runs=("bat_runs", "sum"), balls=("batter_faced", "sum"),
               dots=("dot_ball", "sum")).reset_index())
    bp = bp[bp["balls"] > 0]
    bp["sr"] = 100 * bp["runs"] / bp["balls"]
    bp["dot"] = 100 * bp["dots"] / bp["balls"]

    ov = base.groupby("striker_id").agg(runs=("bat_runs", "sum"),
                                        balls=("batter_faced", "sum"),
                                        dots=("dot_ball", "sum"))
    ov = ov[ov["balls"] > 0]
    ov["sr_all"] = 100 * ov["runs"] / ov["balls"]
    ov["dot_all"] = 100 * ov["dots"] / ov["balls"]

    pw = (pres.groupby(["striker_id", "phase"]).agg(pb=("batter_faced", "sum"))
          .reset_index())
    pw["w"] = pw["pb"] / pw.groupby("striker_id")["pb"].transform("sum")

    m = pw.merge(bp[["striker_id", "phase", "sr", "dot", "balls"]],
                 on=["striker_id", "phase"], how="left")
    m = m.merge(ov[["sr_all", "dot_all"]], on="striker_id", how="left")
    m["balls"] = m["balls"].fillna(0.0)
    m["sr"] = m["sr"].fillna(m["sr_all"])
    m["dot"] = m["dot"].fillna(m["dot_all"])
    shr = m["balls"] / (m["balls"] + k)
    m["sr_sh"] = m["sr"] * shr + m["sr_all"] * (1 - shr)
    m["dot_sh"] = m["dot"] * shr + m["dot_all"] * (1 - shr)
    m["wsr"] = m["w"] * m["sr_sh"]
    m["wdot"] = m["w"] * m["dot_sh"]
    return (m.groupby("striker_id")
            .agg(m_base_sr=("wsr", "sum"), m_base_dot=("wdot", "sum")).reset_index())


def matched_bowler(d: pd.DataFrame, k: int | None = None) -> pd.DataFrame:
    k = C.CTX_SHRINK_BOWL if k is None else k
    d = d.copy()
    d["bowl_dot"] = ((d["bowler_runs"] == 0) & (d["is_legal"] == 1)).astype(int)
    base = d[d["is_bowl_pressure"] == 0]
    pres = d[d["is_bowl_pressure"] == 1]

    bp = (base.groupby(["bowler_id", "phase"])
          .agg(runs=("bowler_runs", "sum"), lb=("is_legal", "sum"),
               wk=("bowler_wicket", "sum"), dots=("bowl_dot", "sum")).reset_index())
    bp = bp[bp["lb"] > 0]
    bp["econ"] = 6 * bp["runs"] / bp["lb"]
    bp["wro"] = 6 * bp["wk"] / bp["lb"]
    bp["dot"] = 100 * bp["dots"] / bp["lb"]

    ov = base.groupby("bowler_id").agg(runs=("bowler_runs", "sum"),
                                       lb=("is_legal", "sum"),
                                       wk=("bowler_wicket", "sum"),
                                       dots=("bowl_dot", "sum"))
    ov = ov[ov["lb"] > 0]
    ov["econ_all"] = 6 * ov["runs"] / ov["lb"]
    ov["wro_all"] = 6 * ov["wk"] / ov["lb"]
    ov["dot_all"] = 100 * ov["dots"] / ov["lb"]

    pw = (pres.groupby(["bowler_id", "phase"]).agg(pb=("is_legal", "sum"))
          .reset_index())
    pw["w"] = pw["pb"] / pw.groupby("bowler_id")["pb"].transform("sum")

    m = pw.merge(bp[["bowler_id", "phase", "econ", "wro", "dot", "lb"]],
                 on=["bowler_id", "phase"], how="left")
    m = m.merge(ov[["econ_all", "wro_all", "dot_all"]], on="bowler_id", how="left")
    m["lb"] = m["lb"].fillna(0.0)
    m["econ"] = m["econ"].fillna(m["econ_all"])
    m["wro"] = m["wro"].fillna(m["wro_all"])
    m["dot"] = m["dot"].fillna(m["dot_all"])
    shr = m["lb"] / (m["lb"] + k)
    m["econ_sh"] = m["econ"] * shr + m["econ_all"] * (1 - shr)
    m["wro_sh"] = m["wro"] * shr + m["wro_all"] * (1 - shr)
    m["dot_sh"] = m["dot"] * shr + m["dot_all"] * (1 - shr)
    m["we"] = m["w"] * m["econ_sh"]
    m["ww"] = m["w"] * m["wro_sh"]
    m["wd"] = m["w"] * m["dot_sh"]
    return (m.groupby("bowler_id")
            .agg(m_base_econ=("we", "sum"), m_base_wro=("ww", "sum"),
                 m_base_dot=("wd", "sum")).reset_index())


def apply_bat(t: pd.DataFrame, d: pd.DataFrame) -> pd.DataFrame:
    mb = matched_batter(d)
    t = t.merge(mb, on="striker_id", how="left")
    t["b_strike_rate"] = t["m_base_sr"].fillna(t["b_strike_rate"])
    t["b_dot_pct"] = t["m_base_dot"].fillna(t["b_dot_pct"])
    t["sr_uplift"] = t["p_strike_rate"] - t["b_strike_rate"]
    t["dot_uplift"] = t["p_dot_pct"] - t["b_dot_pct"]
    return t.drop(columns=["m_base_sr", "m_base_dot"])


def apply_bowl(t: pd.DataFrame, d: pd.DataFrame) -> pd.DataFrame:
    mb = matched_bowler(d)
    t = t.merge(mb, on="bowler_id", how="left")
    t["b_economy"] = t["m_base_econ"].fillna(t["b_economy"])
    t["b_wkt_rate_over"] = t["m_base_wro"].fillna(t["b_wkt_rate_over"])
    t["b_dot_pct"] = t["m_base_dot"].fillna(t["b_dot_pct"])
    t["econ_uplift"] = t["b_economy"] - t["p_economy"]
    t["wkt_rate_uplift"] = t["p_wkt_rate_over"] - t["b_wkt_rate_over"]
    t["dot_uplift"] = t["p_dot_pct"] - t["b_dot_pct"]
    return t.drop(columns=["m_base_econ", "m_base_wro", "m_base_dot"])
