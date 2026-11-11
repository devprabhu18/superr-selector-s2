"""Pre-compute the PUBLIC-SAFE aggregate data for the hosted dashboard.

Reads the LOCAL proprietary parquet + outputs and writes ONLY derived aggregates
(no ball-by-ball, no player/team master records) into public_dashboard/data/.
Run locally: `python -I scripts/build_public_data.py`. Never commit the parquet
or the data pack to the public repo — only this folder's output is safe to host.
"""
from __future__ import annotations
import shutil
import sys
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
PROC = ROOT / "data" / "processed"
OUT = ROOT / "outputs"
PUB = ROOT / "public_dashboard" / "data"
PUB.mkdir(parents=True, exist_ok=True)

d = pd.read_parquet(PROC / "deliveries_state.parquet")

# ---- 1. scalar KPIs (one row) ----
kpis = pd.DataFrame([{
    "matches": int(d.match_id.nunique()),
    "deliveries": int(len(d)),
    "batters": int(d.striker_id.nunique()),
    "bowlers": int(d.bowler_id.nunique()),
    "bat_pressure_balls": int(d.is_bat_pressure.sum()),
    "bowl_pressure_balls": int(d.is_bowl_pressure.sum()),
    "bat_ordinary_balls": int((1 - d.is_bat_pressure).sum()),
}])
kpis.to_csv(PUB / "overview_kpis.csv", index=False)

# ---- 2. format distribution ----
fm = (d.groupby("match_format")
      .agg(deliveries=("match_id", "size"), matches=("match_id", "nunique"))
      .reset_index())
fm.to_csv(PUB / "format_dist.csv", index=False)

# ---- 3. mean pressure intensity by over ----
by_over = d.groupby("overid")[["bat_pressure", "bowl_pressure"]].mean().reset_index()
by_over.to_csv(PUB / "pressure_by_over.csv", index=False)

# ---- 4. copy the already-safe DERIVED outputs (no raw records in these) ----
SAFE = [
    "batter_rankings.csv", "bowler_rankings.csv",
    "batter_stability.csv", "bowler_stability.csv",
    "batter_config_ranks.csv", "bowler_config_ranks.csv",
    "excluded_batters.csv", "excluded_bowlers.csv",
]
for f in SAFE:
    src = OUT / f
    if src.exists():
        shutil.copy(src, PUB / f)

print("Public-safe data written to", PUB)
print("KPIs:", kpis.to_dict("records")[0])
print("Files:", sorted(p.name for p in PUB.glob("*.csv")))
print("\nNOTE: the parquet and 6af3166e7b922_data_pack are NOT copied — keep them local.")
