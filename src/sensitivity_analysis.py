"""Sensitivity / stability analysis.

Re-runs the whole rating under many *reasonable* model configurations
(different pressure definitions, thresholds, eligibility minimums, rating
weights) and measures how often each player appears in the top 10 / top 16.
A player who survives across configs is a robust pick; volatile picks are flagged.
"""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np
import pandas as pd

_SRC = Path(__file__).resolve().parent
sys.path.insert(0, str(_SRC))
sys.path.insert(0, str(_SRC.parent))

import config as C
import pressure_engine as PE
import batter_analysis, bowler_analysis, rating_engine
import context_baseline as CB


def _par(d):
    faced = d[d.batter_faced == 1]
    bp = faced[faced.is_bat_pressure == 1]
    wp = d[d.is_bowl_pressure == 1]
    def sr(s):
        b = s.batter_faced.sum(); return 100*s.bat_runs.sum()/b if b else np.nan
    def ec(s):
        lb = s.is_legal.sum(); return 6*s.bowler_runs.sum()/lb if lb else np.nan
    return {"bat_sr_ipl": sr(bp[bp.is_ipl==1]), "bat_sr_t20i": sr(bp[bp.is_ipl==0]),
            "bowl_econ_ipl": ec(wp[wp.is_ipl==1]), "bowl_econ_t20i": ec(wp[wp.is_ipl==0])}


def _relabel(d, bat_scorer, bowl_scorer, threshold):
    d = d.copy()
    d["bat_pressure"] = bat_scorer(d)
    d["bowl_pressure"] = bowl_scorer(d)
    d["is_bat_pressure"] = (d["bat_pressure"] >= threshold).astype(int)
    d["is_bowl_pressure"] = (d["bowl_pressure"] >= threshold).astype(int)
    return d


# configuration grid ------------------------------------------------------
def bat_configs():
    A = PE.batting_pressure
    B = PE.batting_pressure_chase_centric
    Cc = PE.batting_pressure_death_collapse
    return [
        ("base",            dict(scorer=A,  thr=0.55, elig={}, w=None)),
        ("thr_0.50",        dict(scorer=A,  thr=0.50, elig={}, w=None)),
        ("thr_0.60",        dict(scorer=A,  thr=0.60, elig={}, w=None)),
        ("def_chase",       dict(scorer=B,  thr=0.55, elig={}, w=None)),
        ("def_death_coll",  dict(scorer=Cc, thr=0.55, elig={}, w=None)),
        ("strict_sample",   dict(scorer=A,  thr=0.55,
                                 elig={"min_pressure_balls":120,"min_pressure_matches":8}, w=None)),
        ("w_uplift",        dict(scorer=A,  thr=0.55, elig={},
                                 w={"absolute":0.25,"uplift":0.55,"consistency":0.20})),
        ("w_absolute",      dict(scorer=A,  thr=0.55, elig={},
                                 w={"absolute":0.60,"uplift":0.20,"consistency":0.20})),
        ("w_consistency",   dict(scorer=A,  thr=0.55, elig={},
                                 w={"absolute":0.30,"uplift":0.30,"consistency":0.40})),
    ]


def bowl_configs():
    A = PE.bowling_pressure
    D = PE.bowling_pressure_death_heavy
    Df = PE.bowling_pressure_defend_heavy
    return [
        ("base",            dict(scorer=A,  thr=0.55, elig={}, w=None)),
        ("thr_0.50",        dict(scorer=A,  thr=0.50, elig={}, w=None)),
        ("thr_0.60",        dict(scorer=A,  thr=0.60, elig={}, w=None)),
        ("def_death",       dict(scorer=D,  thr=0.55, elig={}, w=None)),
        ("def_defend",      dict(scorer=Df, thr=0.55, elig={}, w=None)),
        ("strict_sample",   dict(scorer=A,  thr=0.55,
                                 elig={"min_pressure_balls":120,"min_pressure_matches":8}, w=None)),
        ("w_uplift",        dict(scorer=A,  thr=0.55, elig={},
                                 w={"absolute":0.25,"uplift":0.55,"consistency":0.20})),
        ("w_absolute",      dict(scorer=A,  thr=0.55, elig={},
                                 w={"absolute":0.60,"uplift":0.20,"consistency":0.20})),
        ("w_consistency",   dict(scorer=A,  thr=0.55, elig={},
                                 w={"absolute":0.30,"uplift":0.30,"consistency":0.40})),
    ]


def run(d, topn=10, top16=16, exclude_bat_ids=None, exclude_bowl_ids=None):
    """Stability across configs. exclude_*_ids: player ids removed from each
    config's ranked list before taking the top-N (IPL-availability filter)."""
    exclude_bat_ids = set(exclude_bat_ids or [])
    exclude_bowl_ids = set(exclude_bowl_ids or [])
    bat_rows, bowl_rows = [], []
    bat_top, bowl_top = {}, {}
    bat_top16, bowl_top16 = {}, {}

    for name, cfg in bat_configs():
        dd = _relabel(d, cfg["scorer"], PE.bowling_pressure, cfg["thr"])
        par = _par(dd)
        t = batter_analysis.batter_table(dd)
        t = CB.apply_bat(t, dd)
        mr = batter_analysis.batter_match_records(dd)
        r = rating_engine.rate_batters(t, mr, par, weights=cfg["w"], elig=cfg["elig"])
        if exclude_bat_ids:
            r = r[~r["striker_id"].isin(exclude_bat_ids)].copy()
            r["rank"] = range(1, len(r) + 1)
        for _, row in r.head(topn).iterrows():
            bat_top.setdefault(row["striker_id"], {"player": row["player"], "count": 0})
            bat_top[row["striker_id"]]["count"] += 1
        for _, row in r.head(top16).iterrows():
            bat_top16.setdefault(row["striker_id"], {"player": row["player"], "count": 0})
            bat_top16[row["striker_id"]]["count"] += 1
        for _, row in r.head(topn).iterrows():
            bat_rows.append({"config": name, "rank": int(row["rank"]),
                             "player": row["player"], "id": row["striker_id"]})

    for name, cfg in bowl_configs():
        dd = _relabel(d, PE.batting_pressure, cfg["scorer"], cfg["thr"])
        par = _par(dd)
        t = bowler_analysis.bowler_table(dd)
        t = CB.apply_bowl(t, dd)
        mr = bowler_analysis.bowler_match_records(dd)
        r = rating_engine.rate_bowlers(t, mr, par, weights=cfg["w"], elig=cfg["elig"])
        if exclude_bowl_ids:
            r = r[~r["bowler_id"].isin(exclude_bowl_ids)].copy()
            r["rank"] = range(1, len(r) + 1)
        for _, row in r.head(topn).iterrows():
            bowl_top.setdefault(row["bowler_id"], {"player": row["player"], "count": 0})
            bowl_top[row["bowler_id"]]["count"] += 1
        for _, row in r.head(top16).iterrows():
            bowl_top16.setdefault(row["bowler_id"], {"player": row["player"], "count": 0})
            bowl_top16[row["bowler_id"]]["count"] += 1
        for _, row in r.head(topn).iterrows():
            bowl_rows.append({"config": name, "rank": int(row["rank"]),
                              "player": row["player"], "id": row["bowler_id"]})

    nb, nw = len(bat_configs()), len(bowl_configs())
    bat_stab = pd.DataFrame([
        {"id": k, "player": v["player"], "top10_configs": v["count"],
         "top10_freq": v["count"]/nb,
         "top16_configs": bat_top16.get(k, {"count":0})["count"]}
        for k, v in bat_top.items()]).sort_values("top10_configs", ascending=False)
    bowl_stab = pd.DataFrame([
        {"id": k, "player": v["player"], "top10_configs": v["count"],
         "top10_freq": v["count"]/nw,
         "top16_configs": bowl_top16.get(k, {"count":0})["count"]}
        for k, v in bowl_top.items()]).sort_values("top10_configs", ascending=False)

    return (bat_stab.reset_index(drop=True), bowl_stab.reset_index(drop=True),
            pd.DataFrame(bat_rows), pd.DataFrame(bowl_rows), nb, nw)


if __name__ == "__main__":
    import data_loader, match_state
    d = match_state.add_match_state(data_loader.build_deliveries())
    d = PE.add_pressure(d)
    bs, ws, br, wr, nb, nw = run(d)
    bs.to_csv(C.OUTPUTS / "batter_stability.csv", index=False)
    ws.to_csv(C.OUTPUTS / "bowler_stability.csv", index=False)
    br.to_csv(C.OUTPUTS / "batter_config_ranks.csv", index=False)
    wr.to_csv(C.OUTPUTS / "bowler_config_ranks.csv", index=False)
    print(f"\n=== BATTER STABILITY (top-10 appearances across {nb} configs) ===")
    print(bs.head(20).to_string(index=False))
    print(f"\n=== BOWLER STABILITY (top-10 appearances across {nw} configs) ===")
    print(ws.head(20).to_string(index=False))
