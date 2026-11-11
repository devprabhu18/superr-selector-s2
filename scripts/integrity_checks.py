"""Join coverage, key integrity, player id/name consistency, anomalies.
Run: python3 -I scripts/integrity_checks.py <data_pack_dir>
"""
import sys
from pathlib import Path
import pandas as pd
import numpy as np

DATA = Path(sys.argv[1])
bb = pd.read_csv(DATA / "ball_by_ball.csv", low_memory=False)
m = pd.read_csv(DATA / "matches.csv", low_memory=False)
comp = pd.read_csv(DATA / "competitions.csv", low_memory=False)
pe = pd.read_csv(DATA / "playing_eleven.csv", low_memory=False)
cm = pd.read_csv(DATA / "competition_team_player_mapping.csv", low_memory=False)
teams = pd.read_csv(DATA / "teams.csv", low_memory=False)

print("=== JOIN COVERAGE ===")
bb_mids = set(bb.match_id.unique()); m_mids = set(m.match_id.unique())
print("matches with ball data:", len(bb_mids & m_mids), "/ bb matches:", len(bb_mids), "/ meta matches:", len(m_mids))
print("bb match_ids NOT in matches.csv:", len(bb_mids - m_mids))
print("matches.csv match_ids with NO ball data:", len(m_mids - bb_mids))
print("matches.comp_id all in competitions:", m.comp_id.isin(comp.comp_id).all())

print("\n=== DELIVERY KEY UNIQUENESS ===")
for keyset in [["match_id","innings","innings_ball_num"],
               ["match_id","innings","overid","over_ball_num"]]:
    d = bb.duplicated(keyset).sum()
    print(f"dups on {keyset}: {d}")

print("\n=== >120 LEGAL BALL ANOMALY ===")
et = bb.extras_type.fillna("")
bb["legal"] = (~et.isin(["wide","Overstep"])).astype(int)
inn = bb.groupby(["match_id","innings"]).agg(legal=("legal","sum"), rows=("legal","size")).reset_index()
big = inn[(inn.innings.isin([1,2])) & (inn.legal > 120)]
print("innings with >120 legal balls:", len(big))
print(big.head(10).to_string())

print("\n=== SUPER OVERS (innings 3,4) ===")
print("matches with innings>2:", bb[bb.innings>2].match_id.nunique())

print("\n=== PLAYER ID / NAME CONSISTENCY ===")
for idc, namec in [("striker_id","striker_name"),("bowler_id","bowler_name")]:
    g = bb.groupby(idc)[namec].nunique()
    multi = g[g>1]
    print(f"{idc}: {bb[idc].nunique()} ids, {bb[namec].nunique()} names; ids with >1 name: {len(multi)}")
    g2 = bb.groupby(namec)[idc].nunique()
    print(f"   names mapped to >1 id: {(g2>1).sum()}")

print("\n=== BOWLER WICKET CREDIT ===")
NONBOWLER = ["RunOut","Retire Out","Obstructing the field","Obstracting the field"]
credited = bb.is_wicket & (~bb.dismissal_type.fillna("").isin(NONBOWLER))
print("total wickets:", int(bb.is_wicket.sum()))
print("credited-to-bowler wickets:", int(credited.sum()))
print("non-bowler wickets excluded:", int(bb.is_wicket.sum()-credited.sum()))
print(bb[bb.is_wicket].dismissal_type.value_counts().to_string())

print("\n=== FORMAT / SEASON SPREAD (deliveries) ===")
mm = bb.merge(m[["match_id","comp_id"]],on="match_id",how="left").merge(
     comp[["comp_id","match_format","season"]],on="comp_id",how="left")
print("deliveries by format:")
print(mm.match_format.value_counts(dropna=False).to_string())
print("\nmatches by format:")
print(mm.drop_duplicates("match_id").match_format.value_counts(dropna=False).to_string())
print("\nmatches by season:")
print(mm.drop_duplicates("match_id").groupby("season").size().to_string())

print("\n=== IPL identification ===")
ipl = comp[comp.comp_name.str.contains("IPL", case=False, na=False)]
print(ipl.to_string())
ipl_ids = set(ipl.comp_id)
ipl_matches = m[m.comp_id.isin(ipl_ids)].match_id.nunique()
print("IPL matches in metadata:", ipl_matches)

print("\n=== player universe for eligibility (distinct strikers/bowlers with data) ===")
print("distinct strikers:", bb.striker_id.nunique(), "| distinct bowlers:", bb.bowler_id.nunique())
