import sys
from pathlib import Path
import pandas as pd
DATA = Path(sys.argv[1])
bb = pd.read_csv(DATA/"ball_by_ball.csv", low_memory=False)
et = bb.extras_type.fillna("")
bb["legal"] = (~et.isin(["wide","Overstep"])).astype(int)

# Look at one anomalous innings over-by-over
sub = bb[(bb.match_id==13513)&(bb.innings==1)]
legal_per_over = sub.groupby("overid")["legal"].sum()
print("match 13513 inn1 legal balls per over:")
print(legal_per_over.to_string())
print("overs with >6 legal:", (legal_per_over>6).sum(), "| total overs:", sub.overid.nunique())
# distribution of legal-balls-per-over across whole dataset
lpo = bb[bb.innings.isin([1,2])].groupby(["match_id","innings","overid"])["legal"].sum()
print("\nlegal-balls-per-over value counts (whole data):")
print(lpo.value_counts().sort_index().to_string())

# 'other' extras: are they on separate ball nums or appended? check over_ball_num behaviour
print("\n'other' extras: do they advance over_ball_num like a legal ball? sample:")
oth = bb[et=="other"].head(5)[["match_id","innings","overid","over_ball_num","innings_ball_num","runs","extras_type","is_wicket"]]
print(oth.to_string())

# names -> multiple ids
for namec, idc in [("striker_name","striker_id"),("bowler_name","bowler_id")]:
    g = bb.groupby(namec)[idc].nunique()
    for nm in g[g>1].index:
        ids = bb[bb[namec]==nm][idc].unique()
        print(f"\n{namec}='{nm}' -> ids {ids}")
