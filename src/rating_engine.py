"""Rating engine: turn pressure-vs-baseline metrics into a balanced composite.

Composite = 0.40*Absolute + 0.35*Uplift + 0.25*Consistency  (weights configurable).
  Absolute   : how good the player is under pressure, FORMAT-ADJUSTED (compared
               against the league's pressure par for the formats they played) and
               percentile-ranked within the eligible pool.
  Uplift     : pressure minus own baseline, EMPIRICAL-BAYES shrunk toward 0 by
               pressure sample size (so tiny samples cannot dominate).
  Consistency: share of pressure matches in which the player actually delivered
               (match-level), percentile-ranked.

Nothing here references player identities or a target ranking.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
import config as C


def pct_rank(s: pd.Series) -> pd.Series:
    """Percentile rank in [0,1]; NaNs -> median (0.5)."""
    r = s.rank(pct=True, na_option="keep")
    return r.fillna(0.5)


def shrink(value, n, prior):
    """Shrink a per-player statistic toward 0 by sample size."""
    return value * (n / (n + prior))


# ---------------- BATTERS ----------------
def rate_batters(t: pd.DataFrame, match_recs: pd.DataFrame, format_par: dict,
                 weights=None, prior=None, elig=None) -> pd.DataFrame:
    weights = weights or C.BAT_RATING
    prior = C.SHRINK_PRIOR_BAT if prior is None else prior
    elig = elig or {}
    min_pb = elig.get("min_pressure_balls", C.MIN_PRESSURE_BALLS_BAT)
    min_pm = elig.get("min_pressure_matches", C.MIN_PRESSURE_MATCHES)
    min_bb = elig.get("min_baseline_balls", C.MIN_BASELINE_BALLS_BAT)

    t = t.copy()
    t["eligible"] = ((t["p_balls"] >= min_pb) & (t["p_matches"] >= min_pm) &
                     (t["b_balls"] >= min_bb))
    e = t[t["eligible"]].copy()
    if e.empty:
        return e

    # format-adjusted absolute SR: player pressure SR minus their format-weighted par
    par = (e["ipl_share"] * format_par["bat_sr_ipl"] +
           (1 - e["ipl_share"]) * format_par["bat_sr_t20i"])
    e["abs_sr_adj"] = e["p_strike_rate"] - par
    # survival: balls per dismissal under pressure (cap; no-dismissal = best)
    e["p_bpd"] = np.where(e["p_dismissals"] > 0, e["p_balls"] / e["p_dismissals"],
                          e["p_balls"].clip(lower=1) * 2.0)

    e["abs_component"] = (0.60 * pct_rank(e["abs_sr_adj"]) +
                          0.40 * pct_rank(e["p_bpd"]))

    # uplift (shrunk)
    e["sr_uplift_adj"] = shrink(e["sr_uplift"].fillna(0), e["p_balls"], prior)
    e["dot_uplift_adj"] = shrink(e["dot_uplift"].fillna(0), e["p_balls"], prior)   # lower better
    e["avg_uplift_adj"] = shrink(e["avg_uplift"].fillna(0), e["p_balls"], prior)
    e["uplift_component"] = (0.50 * pct_rank(e["sr_uplift_adj"]) +
                             0.30 * pct_rank(-e["dot_uplift_adj"]) +
                             0.20 * pct_rank(e["avg_uplift_adj"]))

    # consistency from per-match pressure records
    cons = _batter_consistency(match_recs, t.set_index("striker_id")["b_strike_rate"])
    e = e.merge(cons, on="striker_id", how="left")
    e["consistency_raw"] = e["consistency_raw"].fillna(0.0)
    e["consistency_component"] = pct_rank(e["consistency_raw"])

    e["score"] = 100 * (weights["absolute"] * e["abs_component"] +
                        weights["uplift"] * e["uplift_component"] +
                        weights["consistency"] * e["consistency_component"])
    e = e.sort_values("score", ascending=False).reset_index(drop=True)
    e["rank"] = np.arange(1, len(e) + 1)
    return e


def _batter_consistency(match_recs: pd.DataFrame, baseline_sr: pd.Series,
                        min_balls=5) -> pd.DataFrame:
    m = match_recs[match_recs["balls"] >= min_balls].copy()
    m["base_sr"] = m["striker_id"].map(baseline_sr)
    # 90% tolerance: hitting within 10% of own baseline still counts as delivered.
    # Without this, high-baseline players are systematically penalised — their 130 SR
    # pressure match is labelled "failure" while a 130 SR from a lower-baseline player passes.
    m["delivered"] = (m["sr"] >= m["base_sr"] * 0.90).astype(int)
    g = m.groupby("striker_id")
    out = g.agg(deliver_share=("delivered", "mean"),
                qual_matches=("match_id", "nunique")).reset_index()
    # reliability-weighted: more qualifying matches = more trustworthy
    out["consistency_raw"] = out["deliver_share"] * (out["qual_matches"] /
                                                     (out["qual_matches"] + 4))
    return out[["striker_id", "consistency_raw", "deliver_share", "qual_matches"]]


# ---------------- BOWLERS ----------------
def rate_bowlers(t: pd.DataFrame, match_recs: pd.DataFrame, format_par: dict,
                 weights=None, prior=None, elig=None) -> pd.DataFrame:
    weights = weights or C.BOWL_RATING
    prior = C.SHRINK_PRIOR_BOWL if prior is None else prior
    elig = elig or {}
    min_pb = elig.get("min_pressure_balls", C.MIN_PRESSURE_BALLS_BOWL)
    min_pm = elig.get("min_pressure_matches", C.MIN_PRESSURE_MATCHES)
    min_bb = elig.get("min_baseline_balls", C.MIN_BASELINE_BALLS_BOWL)

    t = t.copy()
    t["eligible"] = ((t["p_legal_balls"] >= min_pb) & (t["p_matches"] >= min_pm) &
                     (t["b_legal_balls"] >= min_bb))
    e = t[t["eligible"]].copy()
    if e.empty:
        return e

    par_econ = (e["ipl_share"] * format_par["bowl_econ_ipl"] +
                (1 - e["ipl_share"]) * format_par["bowl_econ_t20i"])
    e["abs_econ_adj"] = par_econ - e["p_economy"]          # positive = better than par
    e["abs_component"] = (0.45 * pct_rank(e["abs_econ_adj"]) +
                          0.35 * pct_rank(e["p_wkt_rate_over"]) +
                          0.20 * pct_rank(e["p_dot_pct"]))

    e["econ_uplift_adj"] = shrink(e["econ_uplift"].fillna(0), e["p_legal_balls"], prior)
    e["wkt_uplift_adj"] = shrink(e["wkt_rate_uplift"].fillna(0), e["p_legal_balls"], prior)
    e["dot_uplift_adj"] = shrink(e["dot_uplift"].fillna(0), e["p_legal_balls"], prior)
    e["uplift_component"] = (0.45 * pct_rank(e["econ_uplift_adj"]) +
                             0.35 * pct_rank(e["wkt_uplift_adj"]) +
                             0.20 * pct_rank(e["dot_uplift_adj"]))

    cons = _bowler_consistency(match_recs, t.set_index("bowler_id")["b_economy"],
                               t.set_index("bowler_id")["b_dot_pct"])
    e = e.merge(cons, on="bowler_id", how="left")
    e["consistency_raw"] = e["consistency_raw"].fillna(0.0)
    e["consistency_component"] = pct_rank(e["consistency_raw"])

    e["score"] = 100 * (weights["absolute"] * e["abs_component"] +
                        weights["uplift"] * e["uplift_component"] +
                        weights["consistency"] * e["consistency_component"])
    e = e.sort_values("score", ascending=False).reset_index(drop=True)
    e["rank"] = np.arange(1, len(e) + 1)
    return e


def _bowler_consistency(match_recs: pd.DataFrame, baseline_econ: pd.Series,
                        baseline_dot: pd.Series, min_balls=6) -> pd.DataFrame:
    """Balanced per-match delivery: graded blend of economy improvement (45%),
    wicket contribution (30%) and dot-ball rate (25%). Replaces the old permissive
    'economy <= baseline OR a wicket' rule, under which a single wicket fully
    excused any economy."""
    m = match_recs[match_recs["legal_balls"] >= min_balls].copy()
    m["base_econ"] = m["bowler_id"].map(baseline_econ)
    m["base_dot"] = m["bowler_id"].map(baseline_dot)
    m["m_dot"] = 100 * m["dots"] / m["legal_balls"]
    # economy: full credit if at/under baseline, partial as it worsens
    econ = np.where(m["economy"] <= m["base_econ"], 1.0,
                    np.clip(1 - (m["economy"] - m["base_econ"]) / m["base_econ"], 0, 1))
    wkt = np.clip(m["wickets"] / 2.0, 0, 1)                 # 2+ wickets = full credit
    dot = np.where(m["base_dot"] > 0, np.clip(m["m_dot"] / m["base_dot"], 0, 1), 0.0)
    m["mscore"] = 0.45 * econ + 0.30 * wkt + 0.25 * dot
    g = m.groupby("bowler_id")
    out = g.agg(deliver_share=("mscore", "mean"),
                qual_matches=("match_id", "nunique")).reset_index()
    out["consistency_raw"] = out["deliver_share"] * (out["qual_matches"] /
                                                     (out["qual_matches"] + 4))
    return out[["bowler_id", "consistency_raw", "deliver_share", "qual_matches"]]
