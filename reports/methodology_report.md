# Identifying the Most Reliable Players Under Pressure
## SupeRR Selector Season 2 — Round 1 Methodology Report

*A reproducible, delivery-level framework measuring how batters and bowlers perform in high-pressure
situations relative to their own baseline, across IPL and T20I cricket (2022–2026). Every number here is
traceable to the supplied data via `run_pipeline.py`, the test suite, and the interactive dashboard.
This markdown mirrors `methodology_report.pdf`.*

---

## 1. Executive summary

**Pressure** is a continuous, per-delivery intensity (0–1) built from the match situation *before* each
ball — innings phase, wickets already lost, balls remaining and, in run-chases, required run rate and how
alive the contest is. We build **two separate, asymmetric models**: a batting team is under pressure in hard
chases and at the death; a bowling team is under pressure when batters are set and scoring freely. Each
player is judged against **their own baseline** and scored on a balanced blend of (i) absolute pressure
performance, (ii) uplift vs baseline, and (iii) match-to-match consistency, with empirical-Bayes shrinkage so
small samples cannot spike. Rankings are stress-tested across **nine model configurations**; *reliability* is
the share in which a player stays in the top 10.

Because Rajasthan Royals is an IPL franchise, the final lists apply an **IPL-availability filter** — players
whose national team (from their T20I appearances) is Pakistan are excluded, as they cannot be signed. The
scoring model itself is unchanged and fully data-driven.

### Top 10 Batters Under Pressure
| # | Batter | Score | Rel. | Pr. balls | Pr. mts | Pressure SR | Baseline SR | SR uplift | Pr. avg |
|--:|--|--:|--:|--:|--:|--:|--:|--:|--:|
| 1 | Matthew Wade | 88.3 | 67% | 229 | 19 | 162 | 111 | +51 | 53 |
| 2 | Namboori Tilak Varma | 85.8 | 89% | 886 | 63 | 169 | 129 | +40 | 39 |
| 3 | Naman Dhir | 84.4 | 100% | 267 | 25 | 193 | 148 | +45 | 32 |
| 4 | Rishabh Pant | 83.0 | 100% | 339 | 31 | 182 | 128 | +54 | 33 |
| 5 | Suryakumar Yadav | 82.9 | 89% | 590 | 39 | 198 | 158 | +40 | 40 |
| 6 | Sikandar Raza | 82.7 | 89% | 357 | 26 | 164 | 120 | +44 | 28 |
| 7 | Harry Tector | 81.4 | 78% | 182 | 16 | 162 | 111 | +51 | 30 |
| 8 | Shubman Gill | 81.3 | 56% | 202 | 17 | 193 | 146 | +47 | 39 |
| 9 | Tristan Stubbs | 81.2 | 78% | 613 | 49 | 168 | 125 | +44 | 38 |
| 10 | Virat Kohli | 77.4 | 22% | 172 | 15 | 189 | 142 | +47 | 54 |

### Top 10 Bowlers Under Pressure
| # | Bowler | Type | Score | Rel. | Pr. balls | Pr. mts | Pr. wkts | Pressure econ | Baseline econ | Wkts/over | Dot % |
|--:|--|--|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| 1 | Craig Young | Pace | 91.5 | 78% | 98 | 11 | 9 | 8.45 | 8.69 | 0.55 | 41 |
| 2 | Wanindu Hasaranga | Spin | 88.5 | 100% | 432 | 37 | 33 | 7.79 | 7.95 | 0.46 | 34 |
| 3 | Spencer Johnson | Pace | 87.9 | 44% | 97 | 14 | 8 | 9.34 | 9.20 | 0.49 | 41 |
| 4 | Azmatullah Omarzai | Pace | 85.3 | 78% | 131 | 19 | 9 | 8.93 | 8.67 | 0.41 | 40 |
| 5 | Vaibhav Arora | Pace | 84.3 | 78% | 171 | 22 | 15 | 10.14 | 9.61 | 0.53 | 36 |
| 6 | Mitchell Starc | Pace | 84.1 | 89% | 171 | 20 | 19 | 10.11 | 9.49 | 0.67 | 40 |
| 7 | Ravi Bishnoi | Spin | 83.7 | 67% | 223 | 28 | 18 | 9.09 | 8.22 | 0.48 | 39 |
| 8 | Digvesh Rathi | Spin | 82.9 | 44% | 146 | 14 | 9 | 8.26 | 9.30 | 0.37 | 32 |
| 9 | Mukesh Choudhary | Pace | 78.8 | 56% | 97 | 13 | 7 | 9.40 | 9.62 | 0.43 | 41 |
| 10 | Kartik Tyagi | Pace | 77.8 | 44% | 115 | 12 | 6 | 9.34 | 10.70 | 0.31 | 35 |

*Rel. = reliability across 9 configs. Pr. = pressure. Wickets credited to the bowler only (run-outs excluded).*

---

## 2. Problem & approach

Round 1 asks for a data-driven system measuring pressure performance vs usual level, and a ranking of the most
consistent performers. Pressure is ours to define. Principles:

- **Reliability over reputation** — every pick derives from the ball-by-ball data; no player list is hard-coded.
- **Self-referenced** — pressure numbers are credited relative to the player's *own* baseline.
- **No future leakage** — pressure at a ball uses only information available up to that ball; the result never labels earlier deliveries.
- **Honest about the data** — quantities we can't reconstruct reliably (exact team totals) are not built upon.
- **Robustness first** — the answer must survive reasonable changes to thresholds, weights, and the pressure definition.

## 3. Dataset

Seven files. Core: **ball_by_ball.csv** (200,961 main-innings deliveries after excluding 6 super-over innings),
joined to matches (883; 867 with ball data), competitions (141; 5 IPL seasons), teams, playing XIs and
competition–team–player mappings. Coverage: ~397 T20 matches (371 IPL) and ~470 T20I. Delivery key
(match, innings, ball) is unique; all joins verified.

## 4. Data cleaning & the extras puzzle

The key finding: **`extras1_runs` is not runs — it is a category code** one-to-one with `extras_type`
(6 = legal, 2 = wide, 3 = leg-bye, 4 = bye, 1 = no-ball, 5 = other, 7 = penalty). **`runs` = runs off the bat**
(every six has runs = 6, every four runs = 4; zero contradictions). Consequences:

- **Batting metrics are exact** (SR, boundary %, dot %, dismissals).
- **Bowler economy is reliable** — byes/leg-byes are not charged to the bowler; bowler runs = off-bat + wides + no-balls (+ recorded extras).
- **Team totals / RRR are approximate** — bye/leg-bye magnitudes beyond 1 aren't stored (validated vs 356 margins: median error 0, 266 within ±3; large misses are DLS games, which we exclude from chase logic).
- **Bowler wickets** exclude run-outs/retired/obstruction (609 of 10,881 → 10,272 credited). **Legal balls** exclude wides, no-balls and the re-bowled `other` extra. All aggregation keys on `player_id` (some names map to two IDs).

See `data_dictionary.md` and `data_quality_report.md` for the full Phase-1 findings.

## 5. Pressure definition

A weighted blend of normalised signals in [0,1], combined differently by role. Mean intensity rises through
the innings and differs by role (see `reports/figures/pressure_curve.png`).

**Batting pressure** rises with: innings phase (death highest), wickets already lost, and required run rate in
chases — but a *hopeless* chase (needing >3 runs/ball with few resources) is dampened, since garbage-time
hitting isn't a fair clutch test.

**Bowling pressure** rises with: death overs; batting momentum (high current run rate with wickets in hand);
and defending a gettable chase (low required rate = batting side cruising, bowler must break through).

A delivery is "pressure" when intensity ≥ 0.55 (configurable; swept in §12), giving ~33% batting- and ~19%
bowling-pressure deliveries.

## 6. Match-state reconstruction

For every delivery we reconstruct the pre-ball state chronologically: score, wickets fallen, wickets in hand,
legal balls bowled/remaining and — in the chase — target (inn1 + 1), runs required, required and current run
rate. Balls remaining clamp to ≥ 0; DLS matches are excluded from chase pressure. Correctness is covered by
unit tests (score, wickets, legal-ball counting, RRR, no-future-leakage) — 11/11 pass.

## 7–8. Performance metrics

**Batter** (per delivery set, pressure and own baseline): balls, runs, strike rate, average (own dismissals
only), dot %, boundary %, matches. **Bowler**: legal balls, runs conceded, credited wickets, economy, strike
rate, wickets/over, dot %, boundary % conceded. Each compared against the player's own baseline.

## 9. Rating methodology

**Score = 0.40·Absolute + 0.35·Uplift + 0.25·Consistency** (each a 0–1 percentile within the eligible pool, ×100):

- **Absolute** — pressure performance, *format-adjusted* against league pressure par for the formats the player played (batters: pressure SR + survival; bowlers: economy-vs-par + wicket rate + dot %).
- **Uplift** — pressure minus own baseline, **empirical-Bayes shrunk** toward zero by pressure sample size.
- **Consistency** — share of pressure *matches* in which the player delivered (batter SR ≥ own baseline; bowler economy ≤ baseline or a wicket), reliability-weighted by qualifying matches.

## 10. Sample size, eligibility & reliability

Eligibility (configurable): batters ≥ 75 pressure balls, ≥ 5 pressure matches, ≥ 150 baseline balls; bowlers
≥ 60 pressure legal balls, ≥ 5 pressure matches, ≥ 120 baseline balls. Shrinkage priors (60 balls batters,
48 bowlers) pull small-sample uplifts toward zero. Thresholds are never tuned to force a player in.

## 11. IPL and T20I comparison

Both formats combined, but baselines are per-player (own non-pressure balls) and the absolute component is
adjusted against format-specific pressure par (IPL pressure SR ≈ 153 vs T20I ≈ 138; IPL pressure economy
≈ 10.6 vs T20I ≈ 10.0). IPL-weighted and strict-sample configs check associate-nation inflation.

## 12. Sensitivity & stability

The full rating was re-run under nine configurations: three thresholds (0.50/0.55/0.60), two alternative
batting definitions (chase-centric; death-and-collapse with no RRR), two bowling definitions (death-heavy;
defend-heavy), a strict-sample variant, and three weight mixes. The *reliability* column reports top-10
persistence. **Rock-solid** picks (≥89% of configs): Tilak Varma, Naman Dhir, Rishabh Pant, Suryakumar Yadav,
Sikandar Raza among batters; Hasaranga, Mitchell Starc among bowlers. **More model-dependent** (flagged
honestly): Virat Kohli (22%) and Shubman Gill (56%) among batters; Spencer Johnson, Digvesh Rathi and
Kartik Tyagi (44%) among bowlers — they are genuine top-tier under the primary model but move in and out
under alternative definitions.

## 13–14. Evidence for the top 10

See the tables in §1 and figures `top_batters.png` / `top_bowlers.png`. Every top-10 player posts a positive
strike-rate (batters) or a competitive economy with a strong wicket rate (bowlers) under pressure, backed by a
stated pressure sample. Example reads: **Tilak Varma** — pressure SR 169 vs 129 baseline (+40) over 886
pressure balls in 63 matches, top-10 in 89% of configs; **Hasaranga** — pressure economy 7.79 (baseline 7.95)
with 0.46 wkts/over over 432 pressure balls, top-10 in 100% of configs.

## 15. IPL-availability filter

Excluded (would otherwise rank): **batters** — Babar Azam, Mohammad Rizwan, Fakhar Zaman, Usman Khan, Iftikhar
Ahmed, Salman Agha, Hasan Nawaz, Mohammad Haris; **bowlers** — Haris Rauf, Abbas Afridi, Sufiyan Muqeem, Abrar
Ahmed, Naseem Shah, Shadab Khan, Shaheen Afridi, Mohammad Nawaz, Mohammad Wasim. The filter is one configurable
setting; removing it reinstates them in rank order (Babar would be #4, Rizwan #6 among batters; Haris Rauf #2,
Abbas Afridi #8 among bowlers).

## 16. Model validation

- Unit-tested cricket logic (11/11): reconstruction, legal-ball counting, wicket credit, RRR, no-future-leakage.
- Innings totals cross-checked vs 356 result margins (median error 0).
- Pressure intensity rises monotonically through the innings and differs by role.
- Sample-size-vs-score plots show no runaway small-sample effect.
- Rankings stable across nine configurations.

## 17. Limitations

- Approximate targets (±1–3 runs; DLS excluded from chase logic).
- Pressure is a modelling choice, not an official RR definition (mitigated by nine configs + reliability).
- T20I opponent strength varies; baselines are format-adjusted but some inflation may remain.
- No fitted win-probability model (closeness proxied by RRR/wickets/phase).
- Availability filter uses T20I-inferred nationality; uncapped players with no T20I record are treated as IPL-eligible.

## 18. Conclusion

The framework turns "clutch" into a reproducible, delivery-level measurement: a transparent pressure index,
self-referenced performance, a balanced and shrinkage-protected rating, and a nine-way robustness check. Every
name is backed by its own pressure-versus-baseline numbers and a reliability score, and every figure is
traceable to the supplied data via the accompanying code and dashboard.
