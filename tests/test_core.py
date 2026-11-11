"""Unit tests for core cricket calculations using small, hand-built scenarios
with known answers, plus invariant checks on the real pipeline output.

Run: ./.venv/bin/python -I -m pytest tests/ -q      (or run this file directly)
"""
import sys
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

import config as C
import data_loader, match_state, pressure_engine


# ---------- helpers to build a synthetic innings ----------
def make_ball(match_id=1, innings=1, overid=1, over_ball_num=1, innings_ball_num=1,
              striker_id=100, bowler_id=200, runs=0, is_four=False, is_six=False,
              is_wicket=False, dismissal_type=None, dismissed_player_id=None,
              extras_type=None, extras_2_runs=0, non_striker_id=101):
    return dict(match_id=match_id, innings=innings, overid=overid,
                over_ball_num=over_ball_num, innings_ball_num=innings_ball_num,
                batting_team_id=1, bowling_team_id=2, striker_id=striker_id,
                striker_name=f"B{striker_id}", non_striker_id=non_striker_id,
                non_striker_name="NS", bowler_id=bowler_id, bowler_name=f"W{bowler_id}",
                batting_type="RHB", bowling_type="x", batting_order=1, runs=runs,
                is_four=is_four, is_six=is_six, is_wicket=is_wicket,
                dismissal_type_id=None, dismissal_type=dismissal_type,
                dismissed_player_id=dismissed_player_id, extras_type=extras_type,
                extras1_runs=6, extras_2_runs=extras_2_runs, pace_or_spin="Pace",
                comp_id=1358, comp_name="IPL 2022", match_format="T20", season="2022",
                is_ipl=1, revised_target=np.nan)


def enrich(rows):
    """Apply the same per-ball derivations data_loader.build_deliveries uses."""
    d = pd.DataFrame(rows)
    et = d["extras_type"].fillna("")
    d["is_legal"] = (~et.isin(C.NON_LEGAL_EXTRAS)).astype(int)
    d["batter_faced"] = (~et.isin(C.NOT_FACED_EXTRAS)).astype(int)
    d["is_wide"] = (et == "wide").astype(int)
    d["is_noball"] = (et == "Overstep").astype(int)
    d["is_bye_legbye"] = et.isin(["byes", "legbyes"]).astype(int)
    d["bat_runs"] = d["runs"].astype(int)
    e2 = d["extras_2_runs"].fillna(0)
    d["bowler_runs"] = d["bat_runs"] + d["is_wide"] + d["is_noball"] + e2
    d["team_runs"] = d["bowler_runs"] + d["is_bye_legbye"]
    dt = d["dismissal_type"].fillna("")
    d["is_wicket_bool"] = d["is_wicket"].astype(bool)
    d["bowler_wicket"] = (d["is_wicket_bool"] & (~dt.isin(C.NON_BOWLER_DISMISSALS))).astype(int)
    d["dot_ball"] = ((d["bat_runs"] == 0) & (d["is_wide"] == 0) &
                     (d["is_bye_legbye"] == 0) & (d["is_noball"] == 0)).astype(int)
    d["is_boundary"] = (d["is_four"] | d["is_six"]).astype(int)
    d["phase"] = d["overid"].map(lambda o: "powerplay" if o in C.POWERPLAY_OVERS
                                 else "middle" if o in C.MIDDLE_OVERS else "death")
    d["is_dls"] = 0
    return d.sort_values(["match_id", "innings", "innings_ball_num"]).reset_index(drop=True)


# ---------- tests ----------
def test_legal_ball_counting():
    rows = [make_ball(innings_ball_num=1, runs=1),
            make_ball(innings_ball_num=2, extras_type="wide"),
            make_ball(innings_ball_num=3, extras_type="Overstep", runs=1),
            make_ball(innings_ball_num=4, extras_type="legbyes"),
            make_ball(innings_ball_num=5, extras_type="byes"),
            make_ball(innings_ball_num=6, extras_type="other"),
            make_ball(innings_ball_num=7, runs=4, is_four=True)]
    d = enrich(rows)
    # wide, Overstep, other = not legal -> 4 legal balls
    assert d["is_legal"].sum() == 4, d["is_legal"].sum()


def test_batter_faced():
    rows = [make_ball(innings_ball_num=1, runs=1),
            make_ball(innings_ball_num=2, extras_type="wide"),      # not faced
            make_ball(innings_ball_num=3, extras_type="Overstep", runs=0),  # faced
            make_ball(innings_ball_num=4, extras_type="legbyes")]   # faced
    d = enrich(rows)
    assert d["batter_faced"].sum() == 3


def test_bowler_runs_vs_team_runs():
    # leg-bye of (recorded as) 1 is charged to team but NOT the bowler
    rows = [make_ball(runs=0, extras_type="legbyes"),
            make_ball(innings_ball_num=2, runs=4, is_four=True),
            make_ball(innings_ball_num=3, extras_type="wide"),         # +1 bowler
            make_ball(innings_ball_num=4, extras_type="Overstep", runs=2)]  # +1 penalty +2 bat
    d = enrich(rows)
    assert d["bowler_runs"].sum() == 0 + 4 + 1 + 3, d["bowler_runs"].sum()
    assert d["team_runs"].sum() == 1 + 4 + 1 + 3, d["team_runs"].sum()


def test_bowler_wicket_attribution():
    rows = [make_ball(is_wicket=True, dismissal_type="Bowled", dismissed_player_id=100),
            make_ball(innings_ball_num=2, is_wicket=True, dismissal_type="RunOut",
                      dismissed_player_id=101),
            make_ball(innings_ball_num=3, is_wicket=True, dismissal_type="Caught",
                      dismissed_player_id=100),
            make_ball(innings_ball_num=4, is_wicket=True, dismissal_type="Retire Out",
                      dismissed_player_id=100)]
    d = enrich(rows)
    # Bowled + Caught credited; RunOut + Retire Out not
    assert d["bowler_wicket"].sum() == 2, d["bowler_wicket"].sum()


def test_match_state_score_and_wickets():
    # over 1: 1,0,4,0,W(bowled),2  -> after ball6 score_before reflects prior balls
    rows = [make_ball(innings_ball_num=1, runs=1),
            make_ball(innings_ball_num=2, runs=0),
            make_ball(innings_ball_num=3, runs=4, is_four=True),
            make_ball(innings_ball_num=4, runs=0),
            make_ball(innings_ball_num=5, runs=0, is_wicket=True,
                      dismissal_type="Bowled", dismissed_player_id=100),
            make_ball(innings_ball_num=6, runs=2)]
    d = add_state(rows)
    last = d.iloc[-1]
    # score before last ball = 1+0+4+0+0 = 5; wickets before = 1; legal before = 5
    assert last["score_before"] == 5, last["score_before"]
    assert last["wkts_before"] == 1, last["wkts_before"]
    assert last["balls_remaining"] == C.BALLS_PER_INNINGS - 5


def test_required_run_rate():
    # innings 1 total = 10 (two balls: 6 + 4); target = 11
    inn1 = [make_ball(innings=1, innings_ball_num=1, runs=6, is_six=True),
            make_ball(innings=1, innings_ball_num=2, runs=4, is_four=True)]
    # innings 2: first ball, nothing scored yet
    inn2 = [make_ball(innings=2, innings_ball_num=1, runs=1)]
    d = add_state(inn1 + inn2)
    b = d[(d.innings == 2)].iloc[0]
    assert b["target"] == 11, b["target"]
    assert b["runs_required"] == 11, b["runs_required"]
    # balls remaining before this ball = 120; RRR = 6*11/120
    assert abs(b["req_run_rate"] - 6 * 11 / 120) < 1e-9


def add_state(rows):
    d = enrich(rows)
    return match_state.add_match_state(d)


def test_no_future_leakage():
    # score_before on ball k must equal sum of team_runs on balls 1..k-1
    rows = [make_ball(innings_ball_num=i, runs=(i % 3)) for i in range(1, 11)]
    d = add_state(rows)
    cum = 0
    for i, (_, r) in enumerate(d.iterrows()):
        assert r["score_before"] == cum, (i, r["score_before"], cum)
        cum += r["team_runs"]


def test_pressure_monotonic_in_rrr():
    # higher RRR (alive chase, same phase/wickets) -> higher batting pressure
    base = dict(innings=2, overid=16)
    lo = enrich([make_ball(**base, innings_ball_num=1, runs=1)])
    lo = match_state.add_match_state(lo)
    # craft two synthetic states directly
    df = pd.DataFrame([
        {"phase": "death", "innings": 2, "wkts_before": 3, "wkts_in_hand": 7,
         "req_run_rate": 8, "current_rr": 8, "chase_dead": 0, "chase_won": 0},
        {"phase": "death", "innings": 2, "wkts_before": 3, "wkts_in_hand": 7,
         "req_run_rate": 13, "current_rr": 8, "chase_dead": 0, "chase_won": 0},
    ])
    bp = pressure_engine.batting_pressure(df)
    assert bp.iloc[1] > bp.iloc[0]


def test_dead_chase_dampened():
    df = pd.DataFrame([
        {"phase": "death", "innings": 2, "wkts_before": 8, "wkts_in_hand": 2,
         "req_run_rate": 20, "current_rr": 7, "chase_dead": 1, "chase_won": 0},
        {"phase": "death", "innings": 2, "wkts_before": 8, "wkts_in_hand": 2,
         "req_run_rate": 20, "current_rr": 7, "chase_dead": 0, "chase_won": 0},
    ])
    bp = pressure_engine.batting_pressure(df)
    # the 'dead' version should have LOWER batting pressure than the 'alive' one
    assert bp.iloc[0] < bp.iloc[1]


def test_bowling_pressure_asymmetry():
    # cruising chase (low RRR) -> bowling pressure high, batting pressure lower
    df = pd.DataFrame([{
        "phase": "death", "innings": 2, "wkts_before": 1, "wkts_in_hand": 9,
        "req_run_rate": 4, "current_rr": 9, "chase_dead": 0, "chase_won": 0}])
    assert pressure_engine.bowling_pressure(df).iloc[0] > \
           pressure_engine.batting_pressure(df).iloc[0]


# ---------- invariant checks on real outputs ----------
def test_real_pipeline_invariants():
    pq = C.DATA_PROCESSED / "deliveries_state.parquet"
    if not pq.exists():
        return  # pipeline not yet run
    d = pd.read_parquet(pq)
    assert d["is_bat_pressure"].between(0, 1).all()
    assert (d["balls_remaining"] >= 0).all()
    assert (d["wkts_in_hand"].between(0, 10)).all()
    # rankings uniqueness
    for f in ["batter_rankings.csv", "bowler_rankings.csv"]:
        r = pd.read_csv(C.OUTPUTS / f).head(10)
        idc = "striker_id" if "batter" in f else "bowler_id"
        assert r[idc].nunique() == 10, f
        assert list(r["rank"]) == list(range(1, 11)), f


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = 0
    for fn in fns:
        try:
            fn()
            print(f"PASS {fn.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"FAIL {fn.__name__}: {e}")
        except Exception as e:
            print(f"ERROR {fn.__name__}: {type(e).__name__}: {e}")
    print(f"\n{passed}/{len(fns)} tests passed")
