"""Data loading & cleaning for the SupeRR pressure pipeline.

Reads the proprietary pack, validates columns, attaches match/competition
context, derives the reliable per-ball flags established in Phase 1.
"""
from __future__ import annotations
import pandas as pd
import numpy as np
import config as C


def load_raw():
    bb = pd.read_csv(C.DATA_RAW / "ball_by_ball.csv", low_memory=False)
    matches = pd.read_csv(C.DATA_RAW / "matches.csv", low_memory=False)
    comps = pd.read_csv(C.DATA_RAW / "competitions.csv", low_memory=False)
    pe = pd.read_csv(C.DATA_RAW / "playing_eleven.csv", low_memory=False)
    mapping = pd.read_csv(C.DATA_RAW / "competition_team_player_mapping.csv", low_memory=False)
    teams = pd.read_csv(C.DATA_RAW / "teams.csv", low_memory=False)
    return bb, matches, comps, pe, mapping, teams


def build_deliveries():
    """Return the cleaned, context-enriched delivery table (main innings only)."""
    bb, matches, comps, pe, mapping, teams = load_raw()

    # attach competition/match context
    mctx = matches[["match_id", "comp_id", "match_date", "stage", "venue_country",
                    "home_team", "away_team", "win_team_id", "result",
                    "revised_target", "first_inn_revised_overs",
                    "second_inn_revised_overs", "knock_out"]]
    cctx = comps[["comp_id", "comp_name", "match_format", "season"]]
    d = bb.merge(mctx, on="match_id", how="left").merge(cctx, on="comp_id", how="left")

    # main innings only (drop super overs)
    d = d[d["innings"].isin(C.MAIN_INNINGS)].copy()

    et = d["extras_type"].fillna("")
    # --- reliable per-ball flags (Phase 1) ---
    d["is_legal"] = (~et.isin(C.NON_LEGAL_EXTRAS)).astype(int)
    d["batter_faced"] = (~et.isin(C.NOT_FACED_EXTRAS)).astype(int)
    d["is_wide"] = (et == "wide").astype(int)
    d["is_noball"] = (et == "Overstep").astype(int)
    d["is_bye_legbye"] = et.isin(["byes", "legbyes"]).astype(int)

    # runs off the bat (exact)
    d["bat_runs"] = pd.to_numeric(d["runs"], errors="coerce").fillna(0).astype(int)

    # runs charged to the bowler: off-bat + wide + no-ball penalties + extras_2
    e2 = pd.to_numeric(d["extras_2_runs"], errors="coerce").fillna(0)
    d["bowler_runs"] = d["bat_runs"] + d["is_wide"] + d["is_noball"] + e2
    # team runs (approximate; byes/legbyes counted as 1 where present)
    d["team_runs"] = d["bat_runs"] + d["is_wide"] + d["is_noball"] + e2 + d["is_bye_legbye"]

    # bowler-credited wicket
    dt = d["dismissal_type"].fillna("")
    d["is_wicket_bool"] = d["is_wicket"].astype(bool)
    d["bowler_wicket"] = (d["is_wicket_bool"] & (~dt.isin(C.NON_BOWLER_DISMISSALS))).astype(int)

    d["dot_ball"] = ((d["bat_runs"] == 0) & (d["is_wide"] == 0) &
                     (d["is_bye_legbye"] == 0) & (d["is_noball"] == 0)).astype(int)
    d["is_boundary"] = ((d["is_four"]) | (d["is_six"])).astype(int)

    # phase
    def phase(o):
        if o in C.POWERPLAY_OVERS:
            return "powerplay"
        if o in C.MIDDLE_OVERS:
            return "middle"
        return "death"
    d["phase"] = d["overid"].map(phase)

    # IPL flag
    d["is_ipl"] = d["comp_id"].isin(C.IPL_COMP_IDS).astype(int)
    d["is_dls"] = d["revised_target"].notna().astype(int)

    d = d.sort_values(["match_id", "innings", "innings_ball_num"]).reset_index(drop=True)
    return d


if __name__ == "__main__":
    d = build_deliveries()
    print("deliveries:", len(d), "matches:", d.match_id.nunique())
    print(d[["match_id", "innings", "overid", "phase", "bat_runs", "bowler_runs",
             "team_runs", "is_legal", "bowler_wicket", "dot_ball"]].head())
