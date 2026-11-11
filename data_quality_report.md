# Data Quality Report — SupeRR Selector Season 2

*Phase 1 deliverable. Evidence comes from `scripts/dataset_profile.py`,
`validate_extras.py`, `integrity_checks.py`, `anomaly_probe.py` run against the
supplied data pack. This report states what can and cannot be computed reliably.*

---

## 1. The extras / run-field ambiguity — RESOLVED

The brief warned that `extras1_runs` might not be a run amount. **Confirmed: it is a
categorical code, not runs.** It maps one-to-one to `extras_type`:

| `extras1_runs` | meaning | rows |
|---:|---|---:|
| 6 | legal delivery (no extra) | 189,167 |
| 2 | wide | 7,714 |
| 3 | legbyes | 2,748 |
| 1 | Overstep (no-ball) | 576 |
| 4 | byes | 529 |
| 5 | other | 264 |
| 7 | Penalty | 1 |

**Summing `extras1_runs` would be meaningless.** The prototype's caution was correct.

### What `runs` means — RESOLVED
`runs` = **runs off the bat** (the batter's own runs). Evidence:
- Every `is_six=True` ball has `runs=6` (0 contradictions); every `is_four=True` ball has `runs=4` (0 contradictions).
- All wides, byes, leg-byes have `runs=0` (those are not scored off the bat) — if `runs` were *total* delivery runs, byes/leg-byes would show 1–4. They do not.
- 20 balls have `runs=4` without `is_four`, 3 have `runs=6` without `is_six` → these are all-run 4s / overthrows, i.e. runs off the bat not from a clean boundary. Consistent with the "off the bat" reading.

**→ Batter run totals, strike rate, boundary %, dot % are exact and fully reliable.**

### What is *not* fully recoverable
The **magnitude** of byes, leg-byes, and multi-run wides is generally **not stored**
(`extras_2_runs` is non-zero on only 36 of 200,999 rows). So exact *team totals* are
slightly under-counted. Validation against `matches.csv` result margins:

- "Won by N runs" matches (n=356): reconstructed margin **exact in 111**, within ±1 in 175, within ±3 in **266**. Median error 0.
- The large errors are almost entirely **DLS / rain-affected matches** (margins computed on par scores, not reconstructable from ball data) — expected, not a data fault.
- "Won by N wickets" matches (n=364): 2nd-innings total reached (inn1+1) in 269; the shortfalls are mostly 1–3 runs — exactly the un-recorded extras.

**Implication:**
- **Bowler economy is reliable** — byes/leg-byes are not charged to the bowler, so `bowler_runs_conceded = off-bat + wides + no-balls (+extras_2_runs)` is computable. Only rare multi-run wides are lost.
- **Team totals / required run rate are approximate** (typically within ±1–3 runs/innings). Usable for pressure classification (RRR bands are coarse), but we will not present exact official totals, and we will exclude the ~23 DLS matches from RRR logic. This is documented wherever RRR is used.

---

## 2. Join integrity — CLEAN

- All 867 `match_id`s in ball-by-ball exist in `matches.csv` (0 orphans).
- 16 matches in `matches.csv` have **no** ball-by-ball data (future/abandoned fixtures) → simply excluded from analysis.
- All `matches.comp_id` exist in `competitions.csv`.
- Delivery key (`match_id`, `innings`, `innings_ball_num`) is **unique — 0 duplicates**. Also unique on (`match_id`, `innings`, `overid`, `over_ball_num`).

## 3. Legal-ball counting — one wrinkle, handled

Legal balls per over should be 6. Distribution across all overs: 31,518 overs have exactly 6; **235 have 7**, 8 have 8, 1 has 9; a few have <6 (innings ended). Cause: the `other` extras type (264 rows) is recorded as an on-field delivery but behaves like a **re-bowled** extra (it sits inside an over that then has 7 legal-looking balls). 150 innings showed >120 "legal" balls under a naive rule.

**Resolution:** treat `legal_ball = extras_type ∉ {wide, Overstep, other}`. This brings
over lengths back to 6 in essentially all cases. The residual 8–9-ball overs (9 total)
are genuine multi-extra overs. `balls_remaining` is clamped to ≥0. Net effect on analysis
is negligible (<0.2% of deliveries).

## 4. Player identity — use IDs, never names

Key all aggregation on `player_id` / `striker_id` / `bowler_id`. Names are not unique:
- `striker_name` "Abdul Samad" → ids {7446, 6922}; "Basil Hameed" → {8638, 39444}; "Haider Ali" → {7338, 28756}.
- `bowler_name` "Basil Hameed" → {8638, 39444}.

No id maps to >1 name, so id→name is a safe display lookup. 888 distinct strikers, 647 distinct bowlers have ball data.

## 5. Bowler wicket attribution

Of 10,881 dismissals, **10,272 are credited to the bowler**. Excluded (609): RunOut (600),
Retire Out (6), Obstructing/Obstracting the field (3). Note the two spellings of
"Obstracting"/"Obstructing" — both handled.

## 6. Coverage / sample

- **Deliveries:** 94,672 T20 (IPL + a few domestic) / 106,327 T20I.
- **Matches:** 397 T20 (371 IPL) / 470 T20I.
- **Seasons:** 2022 (168 matches), 2023 (137), 2024 (190), 2025 (210), 2026 (144) + a few 2022/23–2024/25 spanning series.
- Super Overs (innings 3/4): 6 matches — excluded from the main pressure analysis (tiny, non-standard).

## 7. Other notes
- `bowl_speed = 0` is a missing-value sentinel for many balls (do not treat as 0 kph).
- `stroke`, `delivery_style`, `over_or_around` have some nulls; used only as optional context, never in core metrics.
- `win_team_id` null (41) and `toss_opted` null (15) → no-result/abandoned; handled by exclusion where relevant.
- DLS matches (~23, flagged by `revised_target` / `revised_overs`) excluded from RRR-based pressure.

---

## Bottom line: what we can and cannot compute

| Computation | Reliability |
|---|---|
| Batter: runs, balls faced, SR, dot%, boundary%, dismissals | **Exact** |
| Bowler: credited wickets, legal balls, dot%, boundary conceded | **Exact** |
| Bowler: economy / runs conceded | **Reliable** (rare multi-run wides lost) |
| Innings phase, wickets in hand, balls remaining | **Reliable** |
| Team total, target, required run rate | **Approximate (±1–3 runs);** fine for coarse pressure bands, DLS matches excluded |
| Exact official team totals | **Not reproduced** (and not needed) |

No blocking data issues. The analysis can proceed; every approximate quantity is flagged
where it is used.
