"""STATISTICAL METHODOLOGY AUDIT — read-only experiments.

Preserves the primary model: writes NOTHING to outputs/. All experimental
results go to audit/. Prints numerical comparisons for:
  A1  phase-bias quantification + context-matched baseline rankings
  A2  revised (balanced) bowling consistency rankings
  A4  rankings WITHOUT the Pakistan/IPL-availability filter
Run: python -I scripts/audit.py
"""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "src"))
import config as C
import batter_analysis as BA, bowler_analysis as BW, rating_engine as RE

AUD = ROOT / "audit"; AUD.mkdir(exist_ok=True)
OUT = ROOT / "outputs"
d = pd.read_parquet(ROOT / "data" / "processed" / "deliveries_state.parquet")

cur_bat = pd.read_csv(OUT / "batter_rankings.csv")
cur_bowl = pd.read_csv(OUT / "bowler_rankings.csv")


def par_of(dd):
    faced = dd[dd.batter_faced == 1]; bp = faced[faced.is_bat_pressure == 1]
    wp = dd[dd.is_bowl_pressure == 1]
    sr = lambda s: 100 * s.bat_runs.sum() / s.batter_faced.sum() if s.batter_faced.sum() else np.nan
    ec = lambda s: 6 * s.bowler_runs.sum() / s.is_legal.sum() if s.is_legal.sum() else np.nan
    return {"bat_sr_ipl": sr(bp[bp.is_ipl == 1]), "bat_sr_t20i": sr(bp[bp.is_ipl == 0]),
            "bowl_econ_ipl": ec(wp[wp.is_ipl == 1]), "bowl_econ_t20i": ec(wp[wp.is_ipl == 0])}

PAR = par_of(d)


def top10(df, idc):
    return list(zip(df.head(10)["rank"].astype(int), df.head(10)["player"],
                    df.head(10)[idc]))


def compare(name, base_df, new_df, idc):
    """Print rank movement new vs base (both ranked, filtered identically)."""
    b = base_df.set_index(idc)["rank"].to_dict()
    print(f"\n----- {name}: new top 10 (was->now) -----")
    for _, r in new_df.head(10).iterrows():
        was = b.get(r[idc])
        mv = f"(#{was}->#{int(r['rank'])})" if was else "(NEW to top-10)"
        print(f"  {int(r['rank']):>2}. {r['player']:<24} {mv}")
    dropped = [base_df.set_index(idc).loc[i, 'player'] for i in
               (set(base_df.head(10)[idc]) - set(new_df.head(10)[idc]))]
    if dropped:
        print("  dropped out of top 10:", ", ".join(map(str, dropped)))


# =====================================================================
# A1 — PHASE BIAS QUANTIFICATION
# =====================================================================
print("="*74)
print("AREA 1 — INNINGS-PHASE BIAS IN THE PERSONAL BASELINE")
print("="*74)

faced = d[d.batter_faced == 1]
sr_by_phase = faced.groupby("phase").apply(
    lambda s: 100 * s.bat_runs.sum() / s.batter_faced.sum(), include_groups=False)
ec_by_phase = d.groupby("phase").apply(
    lambda s: 6 * s.bowler_runs.sum() / s.is_legal.sum(), include_groups=False)
print("\nLeague strike rate by phase (batting):")
for ph in ["powerplay", "middle", "death"]:
    print(f"   {ph:<10} SR {sr_by_phase[ph]:6.1f}")
print("League economy by phase (bowling):")
for ph in ["powerplay", "middle", "death"]:
    print(f"   {ph:<10} econ {ec_by_phase[ph]:5.2f}")

# phase distribution: pressure vs baseline balls
bp = faced[faced.is_bat_pressure == 1]; bb = faced[faced.is_bat_pressure == 0]
print("\nBatting phase mix (% of balls):")
print("   phase       pressure   baseline")
for ph in ["powerplay", "middle", "death"]:
    pp = 100 * (bp.phase == ph).mean(); bbp = 100 * (bb.phase == ph).mean()
    print(f"   {ph:<10}  {pp:6.1f}%   {bbp:6.1f}%")
print("  => pressure balls are death-heavy, baseline balls middle-heavy; the gap")
print("     inflates raw SR-uplift for anyone whose pressure is concentrated at death.")


def matched_baseline(d, role):
    """Per-player baseline metric reweighted to the player's pressure phase mix."""
    if role == "bat":
        f = d[d.batter_faced == 1]
        pres = f[f.is_bat_pressure == 1]; base = f[f.is_bat_pressure == 0]
        idc = "striker_id"
        # per (player,phase) baseline SR and dot%
        g = base.groupby([idc, "phase"]).agg(runs=("bat_runs", "sum"),
            balls=("batter_faced", "sum"), dots=("dot_ball", "sum"))
        g["sr"] = 100 * g.runs / g.balls
        g["dot"] = 100 * g.dots / g.balls
        # per (player,phase) pressure-ball weights
        w = pres.groupby([idc, "phase"]).agg(pb=("batter_faced", "sum"))
        # overall baseline fallbacks
        ov = base.groupby(idc).agg(runs=("bat_runs", "sum"), balls=("batter_faced", "sum"),
                                   dots=("dot_ball", "sum"))
        ov_sr = (100 * ov.runs / ov.balls); ov_dot = (100 * ov.dots / ov.balls)
        rows = []
        for pid, wp in w.groupby(level=0):
            tot = wp["pb"].sum()
            msr = mdot = 0.0
            for (_, ph), rr in wp.iterrows():
                wt = rr["pb"] / tot
                if (pid, ph) in g.index:
                    msr += wt * g.loc[(pid, ph), "sr"]
                    mdot += wt * g.loc[(pid, ph), "dot"]
                else:
                    msr += wt * (ov_sr.get(pid, np.nan))
                    mdot += wt * (ov_dot.get(pid, np.nan))
            rows.append((pid, msr, mdot))
        return pd.DataFrame(rows, columns=[idc, "m_base_sr", "m_base_dot"])
    else:
        pres = d[d.is_bowl_pressure == 1]; base = d[d.is_bowl_pressure == 0]
        idc = "bowler_id"
        g = base.groupby([idc, "phase"]).agg(runs=("bowler_runs", "sum"),
            lb=("is_legal", "sum"), wk=("bowler_wicket", "sum"))
        g = g[g.lb > 0]
        g["econ"] = 6 * g.runs / g.lb
        g["wro"] = 6 * g.wk / g.lb
        w = pres.groupby([idc, "phase"]).agg(pb=("is_legal", "sum"))
        ov = base.groupby(idc).agg(runs=("bowler_runs", "sum"), lb=("is_legal", "sum"),
                                   wk=("bowler_wicket", "sum"))
        ov = ov[ov.lb > 0]; ov_ec = 6 * ov.runs / ov.lb; ov_wro = 6 * ov.wk / ov.lb
        rows = []
        for pid, wp in w.groupby(level=0):
            tot = wp["pb"].sum()
            mec = mwro = 0.0
            for (_, ph), rr in wp.iterrows():
                wt = rr["pb"] / tot
                if (pid, ph) in g.index:
                    mec += wt * g.loc[(pid, ph), "econ"]; mwro += wt * g.loc[(pid, ph), "wro"]
                else:
                    mec += wt * ov_ec.get(pid, np.nan); mwro += wt * ov_wro.get(pid, np.nan)
            rows.append((pid, mec, mwro))
        return pd.DataFrame(rows, columns=[idc, "m_base_econ", "m_base_wro"])


# ---- batters: context-matched baseline ----
bt = BA.batter_table(d); bmr = BA.batter_match_records(d)
mb = matched_baseline(d, "bat")
bt_m = bt.merge(mb, on="striker_id", how="left")
# replace baseline SR & dot with phase-matched versions; recompute uplift
bt_m["b_strike_rate"] = bt_m["m_base_sr"].fillna(bt_m["b_strike_rate"])
bt_m["b_dot_pct"] = bt_m["m_base_dot"].fillna(bt_m["b_dot_pct"])
bt_m["sr_uplift"] = bt_m["p_strike_rate"] - bt_m["b_strike_rate"]
bt_m["dot_uplift"] = bt_m["p_dot_pct"] - bt_m["b_dot_pct"]
bat_matched = RE.rate_batters(bt_m, bmr, PAR)

# ---- bowlers: context-matched baseline ----
wt = BW.bowler_table(d); wmr = BW.bowler_match_records(d)
mbw = matched_baseline(d, "bowl")
wt_m = wt.merge(mbw, on="bowler_id", how="left")
wt_m["b_economy"] = wt_m["m_base_econ"].fillna(wt_m["b_economy"])
wt_m["b_wkt_rate_over"] = wt_m["m_base_wro"].fillna(wt_m["b_wkt_rate_over"])
wt_m["econ_uplift"] = wt_m["b_economy"] - wt_m["p_economy"]
wt_m["wkt_rate_uplift"] = wt_m["p_wkt_rate_over"] - wt_m["b_wkt_rate_over"]
bowl_matched = RE.rate_bowlers(wt_m, wmr, PAR)

# filter to IPL-eligible for apples-to-apples with current (current is filtered)
import eligibility as EL
nb = EL.nationality_map().rename(columns={"player_id": "striker_id"})
nw = EL.nationality_map().rename(columns={"player_id": "bowler_id"})
def ipl_filter(df, idc, natmap):
    r = df.merge(natmap, on=idc, how="left")
    r = r[~r["nationality"].isin(C.EXCLUDE_NATIONS)].sort_values("score", ascending=False)
    r["rank"] = range(1, len(r) + 1); return r.reset_index(drop=True)
bat_matched_f = ipl_filter(bat_matched, "striker_id", nb)
bowl_matched_f = ipl_filter(bowl_matched, "bowler_id", nw)

compare("A1 batters context-matched (IPL-filtered, vs current)", cur_bat, bat_matched_f, "striker_id")
compare("A1 bowlers context-matched (IPL-filtered, vs current)", cur_bowl, bowl_matched_f, "bowler_id")
bat_matched_f.to_csv(AUD / "A1_batters_context_matched.csv", index=False)
bowl_matched_f.to_csv(AUD / "A1_bowlers_context_matched.csv", index=False)


# =====================================================================
# A2 — REVISED (BALANCED) BOWLING CONSISTENCY
# =====================================================================
print("\n" + "="*74)
print("AREA 2 — REVISED BOWLING CONSISTENCY (economy + wickets + dots, graded)")
print("="*74)

_base_dot = {}  # bowler_id -> baseline dot%

def balanced_bowler_consistency(match_recs, baseline_econ, min_balls=6):
    m = match_recs[match_recs["legal_balls"] >= min_balls].copy()
    m["base_econ"] = m["bowler_id"].map(baseline_econ)
    m["base_dot"] = m["bowler_id"].map(_base_dot)
    m["m_dot"] = 100 * m["dots"] / m["legal_balls"]
    # graded components in [0,1]
    e = np.where(m["m_economy"] <= m["base_econ"], 1.0,
                 np.clip(1 - (m["m_economy"] - m["base_econ"]) / m["base_econ"], 0, 1))
    w = np.clip(m["wickets"] / 2.0, 0, 1)                 # 2+ wkts = full credit
    dt = np.where(m["base_dot"] > 0, np.clip(m["m_dot"] / m["base_dot"], 0, 1), 0.0)
    m["mscore"] = 0.45 * e + 0.30 * w + 0.25 * dt
    g = m.groupby("bowler_id")
    out = g.agg(deliver_share=("mscore", "mean"),
                qual_matches=("match_id", "nunique")).reset_index()
    out["consistency_raw"] = out["deliver_share"] * (out["qual_matches"] /
                                                     (out["qual_matches"] + 4))
    return out[["bowler_id", "consistency_raw", "deliver_share", "qual_matches"]]

# bowler_match_records has economy as 'economy' -> rename to m_economy expected above
wmr2 = wmr.rename(columns={"economy": "m_economy"})
_base_dot = wt.set_index("bowler_id")["b_dot_pct"].to_dict()
_orig = RE._bowler_consistency
RE._bowler_consistency = balanced_bowler_consistency
bowl_balcons = RE.rate_bowlers(wt, wmr2, PAR)
RE._bowler_consistency = _orig
bowl_balcons_f = ipl_filter(bowl_balcons, "bowler_id", nw)
compare("A2 bowlers balanced-consistency (IPL-filtered, vs current)", cur_bowl, bowl_balcons_f, "bowler_id")
bowl_balcons_f.to_csv(AUD / "A2_bowlers_balanced_consistency.csv", index=False)


# =====================================================================
# A4 — REMOVE IPL-AVAILABILITY FILTER (PURE STATISTICAL RANKINGS)
# =====================================================================
print("\n" + "="*74)
print("AREA 4 — PRIMARY RANKINGS WITHOUT THE PAKISTAN FILTER (current model)")
print("="*74)
bat_all = RE.rate_batters(bt, bmr, PAR)       # unfiltered, current model
bowl_all = RE.rate_bowlers(wt, wmr, PAR)
bat_all = bat_all.merge(nb, on="striker_id", how="left")
bowl_all = bowl_all.merge(nw, on="bowler_id", how="left")
print("\nUnfiltered TOP 10 BATTERS (nationality shown):")
for _, r in bat_all.head(10).iterrows():
    print(f"  {int(r['rank']):>2}. {r['player']:<24} {str(r['nationality']):<14} score {r['score']:.1f}")
print("\nUnfiltered TOP 10 BOWLERS:")
for _, r in bowl_all.head(10).iterrows():
    print(f"  {int(r['rank']):>2}. {r['player']:<24} {str(r['nationality']):<14} score {r['score']:.1f}")
pak_b = bat_all[bat_all.nationality.isin(C.EXCLUDE_NATIONS)].head(5)
pak_w = bowl_all[bowl_all.nationality.isin(C.EXCLUDE_NATIONS)].head(5)
print("\nPakistan players that ENTER the unfiltered lists:")
print("  batters:", ", ".join(f"{r.player}(#{int(r['rank'])})" for _, r in pak_b.iterrows()))
print("  bowlers:", ", ".join(f"{r.player}(#{int(r['rank'])})" for _, r in pak_w.iterrows()))
bat_all.to_csv(AUD / "A4_batters_unfiltered.csv", index=False)
bowl_all.to_csv(AUD / "A4_bowlers_unfiltered.csv", index=False)

print("\n\nAudit experiments written to", AUD, "(outputs/ untouched).")
