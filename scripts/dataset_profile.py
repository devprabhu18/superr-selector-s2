"""Phase 1 dataset profiler for SupeRR Selector S2 data pack.

Run: python3 -I scripts/dataset_profile.py <data_pack_dir>
Prints a structured profile; does not modify the data pack.
"""
import sys
import json
from pathlib import Path
import pandas as pd
import numpy as np

pd.set_option("display.width", 200)
pd.set_option("display.max_columns", 100)

DATA = Path(sys.argv[1])

FILES = [
    "competitions.csv",
    "teams.csv",
    "matches.csv",
    "playing_eleven.csv",
    "competition_team_player_mapping.csv",
    "ball_by_ball.csv",
]


def hr(title):
    print("\n" + "=" * 90)
    print(title)
    print("=" * 90)


def profile(df, name):
    hr(f"FILE: {name}  ->  rows={len(df):,}  cols={df.shape[1]}")
    print("\nColumns / dtypes / nulls / n_unique / sample:")
    for c in df.columns:
        nn = df[c].isna().sum()
        nu = df[c].nunique(dropna=True)
        sample = df[c].dropna().unique()[:4]
        sample = [str(s)[:30] for s in sample]
        print(f"  {c:32s} {str(df[c].dtype):10s} nulls={nn:>7,} uniq={nu:>7,}  e.g. {sample}")


for f in FILES:
    p = DATA / f
    if not p.exists():
        print(f"MISSING: {f}")
        continue
    df = pd.read_csv(p, low_memory=False)
    profile(df, f)

    # full duplicate rows
    dup = df.duplicated().sum()
    print(f"\n  fully-duplicate rows: {dup:,}")

    if f == "competitions.csv":
        print("\n  Full competitions table:")
        print(df.to_string(max_rows=200))

    if f == "matches.csv":
        for col in df.columns:
            if df[col].nunique() <= 20:
                print(f"\n  value_counts[{col}]:")
                print(df[col].value_counts(dropna=False).to_string())

    if f == "ball_by_ball.csv":
        bb = df
        hr("BALL_BY_BALL DEEP DIVE")
        print("\nHead (first 8 rows, transposed):")
        print(bb.head(8).T.to_string())

        # candidate columns
        for col in ["runs", "extras1_runs", "extras_2_runs", "extras_type",
                    "is_wicket", "dismissal_type", "innings", "overid",
                    "innings_ball_num"]:
            if col in bb.columns:
                print(f"\n  value_counts[{col}] (top 15):")
                print(bb[col].value_counts(dropna=False).head(15).to_string())

        # relationship: extras_type vs extras1_runs vs extras_2_runs vs runs
        hr("EXTRAS SEMANTICS INVESTIGATION")
        et = "extras_type"
        for col in ["runs", "extras1_runs", "extras_2_runs"]:
            if col in bb.columns and et in bb.columns:
                print(f"\n  crosstab {et} x {col} (counts):")
                ct = pd.crosstab(bb[et].fillna("<NA>"), bb[col])
                print(ct.to_string())

        # per extras_type, distribution of the three numeric fields
        if et in bb.columns:
            grp = bb.groupby(bb[et].fillna("<NA>"))
            cols = [c for c in ["runs", "extras1_runs", "extras_2_runs"] if c in bb.columns]
            print("\n  mean/min/max of numeric run fields by extras_type:")
            print(grp[cols].agg(["mean", "min", "max", "count"]).to_string())

        # is a per-innings total plausible from `runs`?
        hr("INNINGS TOTAL RECONSTRUCTION TEST (using `runs` only)")
        key = [c for c in ["match_id", "innings"] if c in bb.columns]
        if "runs" in bb.columns and len(key) == 2:
            tot = bb.groupby(key)["runs"].sum()
            print("\n  distribution of per-innings `runs` sum:")
            print(tot.describe().to_string())
            print("\n  sample innings totals (first 12):")
            print(tot.head(12).to_string())

        # legal ball counting feasibility
        hr("LEGAL BALL / BALL NUMBER STRUCTURE")
        if "innings_ball_num" in bb.columns and len(key) == 2:
            per = bb.groupby(key)["innings_ball_num"].agg(["min", "max", "count"])
            print("\n  innings_ball_num min/max/count per innings (describe):")
            print(per.describe().to_string())
        if "overid" in bb.columns:
            print("\n  overid range:", bb["overid"].min(), "to", bb["overid"].max())

print("\nDONE.")
