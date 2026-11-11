# SupeRR Selector S2 — Pressure Analytics

Round 1 entry: identify the **10 most reliable batters and 10 most reliable bowlers under pressure**
from the supplied IPL + T20I ball-by-ball data (2022–2026), with a transparent, reproducible methodology
and an interactive dashboard.

> **Proprietary competition data.** The `6af3166e7b922_data_pack/` files are for this competition only —
> do not share, publish, or upload them. All processing is local.

## What's here

```
superr_pressure_dashboard/
├── app.py                      # Dashboard page 1 (Overview)
├── pages/                      # Dashboard pages 2–7
├── dash_common.py              # Shared theme, palette, cached loaders
├── config.py                   # All thresholds & switches (incl. EXCLUDE_NATIONS)
├── run_pipeline.py             # End-to-end: data → pressure → ratings → outputs
├── src/
│   ├── data_loader.py          # Clean + derive reliable per-ball flags
│   ├── match_state.py          # Chronological match-state reconstruction
│   ├── pressure_engine.py      # Batting & bowling pressure (asymmetric)
│   ├── batter_analysis.py      # Pressure vs baseline + per-match records
│   ├── bowler_analysis.py
│   ├── rating_engine.py        # Balanced blend + EB shrinkage + percentiles
│   ├── sensitivity_analysis.py # 9-config stability sweep
│   └── eligibility.py          # Nationality + IPL-availability filter
├── scripts/                    # Phase-1 profiling + report/figure builder
├── tests/test_core.py          # 11 cricket-correctness + invariant tests
├── outputs/                    # Rankings, metrics, stability, exclusions (CSV)
├── reports/                    # methodology_report.pdf + .md + figures
├── data/processed/             # deliveries_state.parquet (local only)
├── data_dictionary.md          # Phase-1 column reference
└── data_quality_report.md      # Phase-1 what-can/can't-be-computed
```

## Run

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

python -I run_pipeline.py          # builds all outputs (~20s)
python -I tests/test_core.py       # 11/11 should pass
python -I scripts/build_report.py  # figures + methodology_report.pdf
streamlit run app.py               # interactive dashboard (7 pages)
```

## Method in one paragraph

Pressure is a per-delivery intensity (0–1) from innings phase, wickets lost, balls remaining and — in
chases — required run rate and contest closeness, computed chronologically (no future leakage), with
**separate asymmetric models** for batting vs bowling. Each player is compared to **their own baseline** and
scored on a balanced blend of absolute pressure performance, uplift vs baseline, and match-to-match
consistency, with empirical-Bayes shrinkage for small samples. Rankings are stress-tested over nine
configurations (the `reliability` column). The final lists apply an **IPL-availability filter** (Pakistan
nationals excluded, since an IPL franchise cannot sign them) applied *after* scoring — the model is unchanged.

## Key data note

`extras1_runs` is a **category code, not runs**; `runs` is **off the bat** (exact). Bye/leg-bye magnitudes aren't stored, so team totals/RRR are approximate (±1–3; DLS matches excluded) — but batting metrics and
bowler economy are reliable. Full detail in `data_quality_report.md`.
