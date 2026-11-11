"""Validate run/extras semantics by reconstructing innings totals and
checking against matches.csv result strings.

Run: python3 -I scripts/validate_extras.py <data_pack_dir>
"""
import sys
import re
from pathlib import Path
import pandas as pd
import numpy as np

DATA = Path(sys.argv[1])
bb = pd.read_csv(DATA / "ball_by_ball.csv", low_memory=False)
m = pd.read_csv(DATA / "matches.csv", low_memory=False)

print("=== 1. Confirm `runs` == runs off the bat (check vs is_four/is_six) ===")
print("rows with runs==4 but is_four False:", ((bb.runs == 4) & (~bb.is_four)).sum())
print("rows with is_four True but runs!=4:", ((bb.is_four) & (bb.runs != 4)).sum())
print("rows with runs==6 but is_six False:", ((bb.runs == 6) & (~bb.is_six)).sum())
print("rows with is_six True but runs!=6:", ((bb.is_six) & (bb.runs != 6)).sum())

print("\n=== 2. extras1_runs is a CODE for extras_type (one-to-one) ===")
print(bb.groupby("extras1_runs")["extras_type"].agg(lambda s: s.fillna("<none>").unique()[:3]).to_string())

print("\n=== 3. Build total-runs-per-ball under an explicit assumption ===")
# runs = off the bat. Extra penalty by type:
#   ordinary (NaN)   -> 0
#   wide             -> 1 + extras_2_runs (standard 1-run wide + extra wides run)
#   Overstep(no-ball)-> 1 penalty (+ off-bat runs already in `runs`) + extras_2_runs
#   legbyes          -> amount NOT stored numerically; assume extras_2_runs if >0 else 1
#   byes             -> same assumption
#   other            -> extras_2_runs if >0 else 1
#   Penalty          -> 5
et = bb["extras_type"].fillna("")
e2 = bb["extras_2_runs"].fillna(0)
extra_pen = np.select(
    [et == "", et == "wide", et == "Overstep", et == "legbyes",
     et == "byes", et == "other", et == "Penalty"],
    [0, 1 + e2, 1 + e2, np.where(e2 > 0, e2, 1),
     np.where(e2 > 0, e2, 1), np.where(e2 > 0, e2, 1), 5],
    default=0,
)
bb["total_runs"] = bb["runs"] + extra_pen

# legal ball: exclude wide and no-ball (Overstep)
bb["legal_ball"] = (~et.isin(["wide", "Overstep"])).astype(int)

tot = bb.groupby(["match_id", "innings"]).agg(
    total=("total_runs", "sum"), offbat=("runs", "sum"),
    balls=("legal_ball", "sum"), wkts=("is_wicket", "sum")).reset_index()

# only main innings 1 & 2
main = tot[tot.innings.isin([1, 2])]
p = main.pivot(index="match_id", columns="innings", values=["total", "wkts", "balls"])
p.columns = [f"{a}{b}" for a, b in p.columns]
p = p.reset_index().merge(m[["match_id", "result", "win_team_id"]], on="match_id", how="left")

# parse "Won by N runs"
def parse_runs(r):
    mobj = re.search(r"Won by (\d+) [Rr]uns?", str(r))
    return int(mobj.group(1)) if mobj else np.nan
def parse_wkts(r):
    mobj = re.search(r"Won by (\d+) [Ww]ickets?", str(r))
    return int(mobj.group(1)) if mobj else np.nan

p["margin_runs"] = p["result"].apply(parse_runs)
p["margin_wkts"] = p["result"].apply(parse_wkts)

# For a "won by runs" result: team batting first won; margin = inn1 - inn2
rr = p[p.margin_runs.notna()].copy()
rr["recon_margin"] = rr["total1"] - rr["total2"]
rr["diff"] = rr["recon_margin"] - rr["margin_runs"]
print("\n--- 'Won by N runs' matches: reconstructed margin vs actual ---")
print("count:", len(rr))
print("exact matches:", (rr["diff"] == 0).sum())
print("within +-1:", (rr["diff"].abs() <= 1).sum())
print("within +-3:", (rr["diff"].abs() <= 3).sum())
print(rr["diff"].describe().to_string())
print("\nworst mismatches:")
print(rr.reindex(rr["diff"].abs().sort_values(ascending=False).index)[
    ["match_id", "total1", "total2", "margin_runs", "recon_margin", "diff", "result"]].head(10).to_string())

# For a "won by wickets" result: chasing team (inn2) reached target = inn1+1
ww = p[p.margin_wkts.notna()].copy()
ww["target"] = ww["total1"] + 1
ww["chased_ok"] = ww["total2"] >= ww["target"]
print("\n--- 'Won by N wickets' matches: did inn2 total reach inn1+1? ---")
print("count:", len(ww))
print("inn2 >= inn1+1:", ww["chased_ok"].sum())
print("inn2 total - target (should be >=0, small):")
ww["over"] = ww["total2"] - ww["target"]
print(ww["over"].describe().to_string())
print("cases inn2 < target (reconstruction too low):", (ww["over"] < 0).sum())
print(ww[ww.over < 0][["match_id","total1","total2","margin_wkts","result"]].head(10).to_string())

print("\n=== 4. Compare with OFFBAT-ONLY reconstruction (ignoring extras) ===")
rr2 = p[p.margin_runs.notna()].copy()
# need offbat totals
ob = main.pivot(index="match_id", columns="innings", values="total")
# recompute offbat
obp = tot[tot.innings.isin([1,2])].pivot(index="match_id", columns="innings", values="offbat")
obp.columns=[f"offbat{c}" for c in obp.columns]
rr2 = rr2.merge(obp.reset_index(), on="match_id", how="left")
rr2["recon_ob"] = rr2["offbat1"] - rr2["offbat2"]
rr2["diff_ob"] = rr2["recon_ob"] - rr2["margin_runs"]
print("offbat-only exact margin matches:", (rr2["diff_ob"]==0).sum(), "of", len(rr2))
print("offbat-only within +-3:", (rr2["diff_ob"].abs()<=3).sum())

print("\n=== 5. Innings structure (3 & 4 = super overs?) ===")
print(tot.groupby("innings")["balls"].describe().to_string())
