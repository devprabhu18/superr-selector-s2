"""End-to-end pipeline: build deliveries -> match state -> pressure -> player
metrics -> ratings -> ranked outputs. Writes processed data and output CSVs.

Run: python3 -I run_pipeline.py
"""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

import config as C
import data_loader, match_state, pressure_engine
import batter_analysis, bowler_analysis, rating_engine
import context_baseline as CB
import sensitivity_analysis as SA
import eligibility


def compute_format_par(d: pd.DataFrame) -> dict:
    """League pressure par metrics by format (for format-adjusted absolute scores)."""
    faced = d[d["batter_faced"] == 1]
    bp = faced[faced["is_bat_pressure"] == 1]
    def sr(sub):
        b = sub["batter_faced"].sum()
        return 100 * sub["bat_runs"].sum() / b if b else np.nan
    wp = d[d["is_bowl_pressure"] == 1]
    def econ(sub):
        lb = sub["is_legal"].sum()
        return 6 * sub["bowler_runs"].sum() / lb if lb else np.nan
    return {
        "bat_sr_ipl": sr(bp[bp.is_ipl == 1]),
        "bat_sr_t20i": sr(bp[bp.is_ipl == 0]),
        "bowl_econ_ipl": econ(wp[wp.is_ipl == 1]),
        "bowl_econ_t20i": econ(wp[wp.is_ipl == 0]),
    }


def main():
    print("Loading & building deliveries ...")
    d = data_loader.build_deliveries()
    d = match_state.add_match_state(d)
    d = pressure_engine.add_pressure(d)
    print(f"  {len(d):,} deliveries, {d.match_id.nunique()} matches")
    print(f"  batting-pressure balls: {int(d.is_bat_pressure.sum()):,} "
          f"({d.is_bat_pressure.mean():.1%}) | bowling-pressure balls: "
          f"{int(d.is_bowl_pressure.sum()):,} ({d.is_bowl_pressure.mean():.1%})")

    # save processed deliveries (local only - proprietary)
    keep = ["match_id", "comp_id", "comp_name", "match_format", "season", "is_ipl",
            "innings", "overid", "phase", "striker_id", "striker_name",
            "bowler_id", "bowler_name", "pace_or_spin", "batting_team_id",
            "bowling_team_id", "bat_runs", "bowler_runs", "team_runs",
            "batter_faced", "is_legal", "dot_ball", "is_four", "is_six",
            "is_boundary", "is_wicket_bool", "bowler_wicket", "dismissed_player_id",
            "score_before", "wkts_before", "wkts_in_hand", "balls_remaining",
            "target", "runs_required", "req_run_rate", "current_rr",
            "bat_pressure", "bowl_pressure", "is_bat_pressure", "is_bowl_pressure",
            "is_dls"]
    d[keep].to_parquet(C.DATA_PROCESSED / "deliveries_state.parquet", index=False)

    par = compute_format_par(d)
    print("Format par:", {k: round(v, 2) for k, v in par.items()})

    # ---- batters ----
    print("Rating batters ...")
    bt = batter_analysis.batter_table(d)
    bt = CB.apply_bat(bt, d)                     # context-matched (phase) baseline
    bmr = batter_analysis.batter_match_records(d)
    batters = rating_engine.rate_batters(bt, bmr, par)
    batters = eligibility.attach_nationality(batters, "striker_id")
    print(f"  eligible batters: {len(batters)}")

    # ---- bowlers ----
    print("Rating bowlers ...")
    wt = bowler_analysis.bowler_table(d)
    wt = CB.apply_bowl(wt, d)                     # context-matched (phase) baseline
    wmr = bowler_analysis.bowler_match_records(d)
    bowlers = rating_engine.rate_bowlers(wt, wmr, par)
    bowlers = eligibility.attach_nationality(bowlers, "bowler_id")
    print(f"  eligible bowlers: {len(bowlers)}")

    # ---- sensitivity / stability on the PRIMARY (unfiltered) pool ----
    print("Running sensitivity analysis ...")
    bat_stab, bowl_stab, bat_cr, bowl_cr, nb, nw = SA.run(d)
    bat_stab.to_csv(C.OUTPUTS / "batter_stability.csv", index=False)
    bowl_stab.to_csv(C.OUTPUTS / "bowler_stability.csv", index=False)
    bat_cr.to_csv(C.OUTPUTS / "batter_config_ranks.csv", index=False)
    bowl_cr.to_csv(C.OUTPUTS / "bowler_config_ranks.csv", index=False)
    batters = batters.merge(
        bat_stab[["id", "top10_freq"]].rename(columns={"id": "striker_id",
                                                       "top10_freq": "reliability"}),
        on="striker_id", how="left")
    bowlers = bowlers.merge(
        bowl_stab[["id", "top10_freq"]].rename(columns={"id": "bowler_id",
                                                        "top10_freq": "reliability"}),
        on="bowler_id", how="left")
    batters["reliability"] = batters["reliability"].fillna(0.0)
    bowlers["reliability"] = bowlers["reliability"].fillna(0.0)
    pd.DataFrame({"n_bat_configs": [nb], "n_bowl_configs": [nw]}).to_csv(
        C.OUTPUTS / "sensitivity_meta.csv", index=False)

    # ---- SECONDARY, optional IPL-availability view (derived from the primary,
    #      carries reliability; NOT the primary ranking) ----
    bat_ipl, bat_removed = eligibility.attach_and_filter(batters, "striker_id")
    bowl_ipl, bowl_removed = eligibility.attach_and_filter(bowlers, "bowler_id")
    if C.EXCLUDE_NATIONS:
        print(f"  IPL-availability view ({', '.join(sorted(C.EXCLUDE_NATIONS))}): "
              f"removes {len(bat_removed)} batters, {len(bowl_removed)} bowlers")
    bat_removed.to_csv(C.OUTPUTS / "excluded_batters.csv", index=False)
    bowl_removed.to_csv(C.OUTPUTS / "excluded_bowlers.csv", index=False)


    # ---- write outputs ----
    bat_cols = ["rank", "striker_id", "player", "nationality", "score", "reliability",
                "abs_component", "uplift_component", "consistency_component", "ipl_share",
                "p_balls", "p_matches", "p_runs", "p_strike_rate", "b_strike_rate",
                "sr_uplift", "p_average", "b_average", "p_dot_pct", "b_dot_pct",
                "p_boundary_pct", "deliver_share", "qual_matches"]
    bowl_cols = ["rank", "bowler_id", "player", "nationality", "score", "reliability",
                 "abs_component", "uplift_component", "consistency_component", "ipl_share",
                 "pace_or_spin", "p_legal_balls", "p_matches", "p_wickets",
                 "p_economy", "b_economy", "econ_uplift", "p_wkt_rate_over",
                 "b_wkt_rate_over", "p_dot_pct", "b_dot_pct", "p_boundary_pct",
                 "deliver_share", "qual_matches"]
    batters[bat_cols].to_csv(C.OUTPUTS / "batter_rankings.csv", index=False)
    bowlers[bowl_cols].to_csv(C.OUTPUTS / "bowler_rankings.csv", index=False)
    bat_ipl[bat_cols].to_csv(C.OUTPUTS / "batter_rankings_ipl_available.csv", index=False)
    bowl_ipl[bowl_cols].to_csv(C.OUTPUTS / "bowler_rankings_ipl_available.csv", index=False)
    bt.to_csv(C.OUTPUTS / "batter_metrics_all.csv", index=False)
    wt.to_csv(C.OUTPUTS / "bowler_metrics_all.csv", index=False)

    print("\n=== PRIMARY TOP 10 BATTERS UNDER PRESSURE (unfiltered) ===")
    print(batters[["rank", "player", "nationality", "score", "p_balls",
                   "p_strike_rate", "b_strike_rate", "sr_uplift"]].head(10).to_string(index=False))
    print("\n=== PRIMARY TOP 10 BOWLERS UNDER PRESSURE (unfiltered) ===")
    print(bowlers[["rank", "player", "nationality", "score", "p_legal_balls",
                   "p_economy", "b_economy", "p_wkt_rate_over"]].head(10).to_string(index=False))
    print("\n=== (SECONDARY) IPL-AVAILABILITY TOP 10 BATTERS ===")
    print(bat_ipl[["rank", "player", "score"]].head(10).to_string(index=False))
    print("\n=== (SECONDARY) IPL-AVAILABILITY TOP 10 BOWLERS ===")
    print(bowl_ipl[["rank", "player", "score"]].head(10).to_string(index=False))
    return d, batters, bowlers, par


if __name__ == "__main__":
    main()
