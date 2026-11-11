"""Chronological match-state reconstruction.

For every delivery, compute the state BEFORE the ball is bowled, using only
information available up to that point (no future leakage):
  - score before, wickets fallen before, wickets in hand
  - legal balls bowled before, balls remaining
  - (2nd innings) target, runs required, required run rate, current run rate
Targets are approximate (bye/legbye magnitudes not recorded); DLS matches flagged.
"""
from __future__ import annotations
import pandas as pd
import numpy as np
import config as C


def add_match_state(d: pd.DataFrame) -> pd.DataFrame:
    d = d.sort_values(["match_id", "innings", "innings_ball_num"]).copy()
    g = d.groupby(["match_id", "innings"], sort=False)

    # cumulative-before quantities
    d["score_before"] = g["team_runs"].cumsum() - d["team_runs"]
    d["wkts_before"] = g["is_wicket_bool"].apply(lambda s: s.cumsum()).to_numpy() - d["is_wicket_bool"].astype(int)
    d["legal_before"] = g["is_legal"].cumsum() - d["is_legal"]
    d["wkts_in_hand"] = (10 - d["wkts_before"]).clip(lower=0)
    d["balls_remaining"] = (C.BALLS_PER_INNINGS - d["legal_before"]).clip(lower=0)
    d["overs_done"] = d["legal_before"] / 6.0
    d["current_rr"] = np.where(d["legal_before"] > 0,
                               6.0 * d["score_before"] / d["legal_before"], np.nan)

    # first-innings final totals -> targets for second innings
    inn1 = (d[d["innings"] == 1].groupby("match_id")["team_runs"].sum()
            .rename("inn1_total"))
    d = d.merge(inn1, on="match_id", how="left")
    d["target"] = np.where(d["innings"] == 2, d["inn1_total"] + 1, np.nan)
    d["runs_required"] = np.where(d["innings"] == 2,
                                  (d["target"] - d["score_before"]).clip(lower=0), np.nan)
    with np.errstate(divide="ignore", invalid="ignore"):
        d["req_run_rate"] = np.where(
            (d["innings"] == 2) & (d["balls_remaining"] > 0),
            6.0 * d["runs_required"] / d["balls_remaining"], np.nan)
    # runs needed per ball (feasibility)
    d["req_per_ball"] = np.where(
        (d["innings"] == 2) & (d["balls_remaining"] > 0),
        d["runs_required"] / d["balls_remaining"], np.nan)
    # chase already won (runs_required == 0) or effectively dead
    d["chase_won"] = ((d["innings"] == 2) & (d["runs_required"] <= 0)).astype(int)
    d["chase_dead"] = ((d["innings"] == 2) &
                       (d["req_per_ball"] > C.DEAD_CHASE_RPB)).astype(int)
    return d


if __name__ == "__main__":
    import data_loader
    d = add_match_state(data_loader.build_deliveries())
    # sanity: a 2nd-innings ball
    s = d[(d.innings == 2)].iloc[50]
    print(s[["match_id", "overid", "score_before", "wkts_before", "balls_remaining",
             "target", "runs_required", "req_run_rate", "current_rr"]])
