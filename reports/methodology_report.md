# Identifying the Most Reliable Players Under Pressure
## SupeRR Selector Season 2 — Round 1 Methodology Report

*A reproducible, delivery-level framework measuring how batters and bowlers perform in high-pressure
situations relative to their own baseline, across IPL and T20I cricket (2022–2026). Every number here is
traceable to the supplied data via `run_pipeline.py`, the test suite, and the interactive dashboard.*

> **Authoritative generated versions:** `reports/methodology_report.pdf` and `reports/methodology_report.docx`
> are built directly from the live pipeline outputs. This markdown mirrors them.

---

## 1. Executive summary

**Pressure** is a continuous, per-delivery intensity (0–1) built from the match situation *before* each
ball — innings phase, wickets already lost, balls remaining and, in run-chases, required run rate and how
alive the contest is. We build **two separate, asymmetric models**: a batting team is under pressure in hard
chases and at the death; a bowling team is under pressure when batters are set and scoring freely. Each
player is judged against a **context-matched baseline** — their own non-pressure level *in the same innings
phases* — and scored on an **absolute-leaning blend**: 50% absolute pressure performance, 30% uplift vs
baseline, 20% match-to-match consistency, with empirical-Bayes shrinkage so small samples cannot spike.
Rankings are stress-tested across **nine model configurations**; *reliability* is the share in which a player
stays in the top 10.

These are the **primary statistical rankings and apply no nationality filter.** A separate, clearly-labelled
**IPL-availability view** (§15) removes players an IPL franchise cannot sign, using *inferred* nationality;
it is a secondary lens only, never the headline result.

### Top 10 Batters Under Pressure
| # | Batter | Nat. | Score | Rel. | Pr. balls | Pressure SR | Baseline SR | SR uplift |
|--:|--|--|--:|--:|--:|--:|--:|--:|
| 1 | Matthew Wade | Australia | 88.6 | 67% | 229 | 162 | 110 | +52 |
| 2 | Naman Dhir | India | 87.2 | 89% | 267 | 193 | 152 | +41 |
| 3 | Babar Azam | Pakistan | 82.6 | 67% | 114 | 193 | 136 | +57 |
| 4 | Rohit Sharma | India | 82.5 | 33% | 82 | 194 | 142 | +52 |
| 5 | Rishabh Pant | India | 82.1 | 89% | 339 | 182 | 137 | +46 |
| 6 | Mohammad Rizwan | Pakistan | 82.1 | 44% | 117 | 174 | 126 | +47 |
| 7 | Shai Hope | West Indies | 79.3 | 56% | 116 | 178 | 139 | +40 |
| 8 | Harry Tector | Ireland | 79.2 | 56% | 182 | 162 | 114 | +48 |
| 9 | Fakhar Zaman | Pakistan | 78.8 | 67% | 129 | 171 | 124 | +48 |
| 10 | Shubman Gill | India | 78.8 | 33% | 202 | 193 | 155 | +38 |

### Top 10 Bowlers Under Pressure
| # | Bowler | Nat. | Type | Score | Rel. | Pr. balls | Pressure econ | Baseline econ | Wkts/over |
|--:|--|--|--|--:|--:|--:|--:|--:|--:|
| 1 | Haris Rauf | Pakistan | Pace | 95.3 | 100% | 283 | 8.31 | 9.16 | 0.59 |
| 2 | Craig Young | Ireland | Pace | 89.9 | 78% | 98 | 8.45 | 8.34 | 0.55 |
| 3 | Ravi Bishnoi | India | Spin | 88.6 | 78% | 223 | 9.09 | 8.86 | 0.48 |
| 4 | Wanindu Hasaranga | Sri Lanka | Spin | 88.3 | 78% | 432 | 7.79 | 7.96 | 0.46 |
| 5 | Mitchell Starc | Australia | Pace | 86.6 | 89% | 171 | 10.11 | 9.68 | 0.67 |
| 6 | Moeen Ali | England | Spin | 86.1 | 56% | 73 | 6.66 | 8.73 | 0.66 |
| 7 | Vaibhav Arora | — | Pace | 85.9 | 56% | 171 | 10.14 | 10.34 | 0.53 |
| 8 | Digvesh Rathi | — | Spin | 85.1 | 56% | 146 | 8.26 | 9.65 | 0.37 |
| 9 | Mukesh Choudhary | — | Pace | 84.5 | 67% | 97 | 9.40 | 10.94 | 0.43 |
| 10 | Nathan Ellis | Australia | Pace | 82.4 | 89% | 193 | 8.83 | 8.72 | 0.40 |

*Rel. = reliability across 9 configs. Pr. = pressure. Baselines are context-matched (same-phase). Wickets
credited to the bowler only (run-outs excluded). "—" = no T20I record, so nationality cannot be inferred.*

---

## 2. Problem & approach

Round 1 asks for a data-driven system measuring pressure performance vs usual level, and a ranking of the most
consistent performers. Pressure is ours to define. Principles:

- **Reliability over reputation** — every pick derives from the ball-by-ball data; no player list is hard-coded.
- **Self-referenced, phase-fair** — pressure numbers are credited relative to the player's own *same-phase* baseline.
- **No future leakage** — pressure at a ball uses only information available up to that ball.
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
- **Bowler wickets** exclude run-outs/retired/obstruction (609 of 10,881 → 10,272 credited). **Legal balls** exclude wides, no-balls and the re-bowled `other` extra. All aggregation keys on `player_id`.

## 5. Pressure definition

A weighted blend of normalised signals in [0,1], combined differently by role. Mean intensity rises through
the innings and differs by role (see `reports/figures/pressure_curve.png`).

**Batting pressure** rises with: innings phase (death highest), wickets already lost, and required run rate in
chases — but a *hopeless* chase (needing >3 runs/ball with few resources) is dampened.

**Bowling pressure** rises with: death overs; batting momentum (high current run rate with wickets in hand);
and defending a gettable chase (low required rate = batting side cruising).

A delivery is "pressure" when intensity ≥ 0.55 (configurable; swept in §12), giving ~33% batting- and ~19%
bowling-pressure deliveries.

## 6. Match-state reconstruction

For every delivery we reconstruct the pre-ball state chronologically: score, wickets fallen, wickets in hand,
legal balls bowled/remaining and — in the chase — target (inn1 + 1), runs required, required and current run
rate. Balls remaining clamp to ≥ 0; DLS matches are excluded from chase pressure. Correctness is covered by
unit tests — 11/11 pass.

## 7–8. Performance metrics & the context-matched baseline

**Batter** (per delivery set): balls, runs, strike rate, average (own dismissals only), dot %, boundary %,
matches. **Bowler**: legal balls, runs conceded, credited wickets, economy, strike rate, wickets/over, dot %,
boundary % conceded.

**Context-matched baseline (controls for innings-phase bias).** Pressure deliveries are heavily death-weighted
(≈59% of batting-pressure balls) while a player's pooled non-pressure baseline is powerplay/middle-dominated
(death is ≈4% of it). Because scoring rates differ sharply by phase, a raw pressure-minus-baseline uplift
partly measures the *phase*, not a pressure response. We therefore compare each player to their own
non-pressure level **in the same phases**, reweighted to their pressure phase mix. Death-over non-pressure
samples are thin, so each per-phase baseline is **shrunk toward the player's overall baseline**.

## 9. Rating methodology

**Score = 0.50·Absolute + 0.30·Uplift + 0.20·Consistency** (each a 0–1 percentile within the eligible pool, ×100):

- **Absolute (50%)** — pressure performance, *format-adjusted* against league pressure par for the formats the player played (batters: pressure SR + survival; bowlers: economy-vs-par + wicket rate + dot %). Weighted highest so a genuinely high-level pressure performance is rewarded on its own merit.
- **Uplift (30%)** — pressure minus the player's **context-matched** baseline, **empirical-Bayes shrunk** toward zero by pressure sample size.
- **Consistency (20%)** — share of pressure *matches* delivered. Batters: SR within 10% of their context-matched baseline (tolerance protects high-baseline players). Bowlers: a **graded** blend of economy improvement (45%), wicket contribution (30%) and dot-ball rate (25%) — replacing the old "economy ≤ baseline OR one wicket" rule a single wicket could fully satisfy.

## 10. Sample size, eligibility & reliability

Eligibility (configurable): batters ≥ 75 pressure balls, ≥ 5 pressure matches, ≥ 150 baseline balls; bowlers
≥ 60 pressure legal balls, ≥ 5 pressure matches, ≥ 120 baseline balls. Shrinkage priors (60 balls batters,
48 bowlers) pull small-sample uplifts toward zero. Thresholds are never tuned to force a player in.

## 11. IPL and T20I comparison

Both formats combined, but baselines are per-player (own non-pressure, same-phase balls) and the absolute
component is adjusted against format-specific pressure par (IPL pressure SR ≈ 153 vs T20I ≈ 138; IPL pressure
economy ≈ 10.6 vs T20I ≈ 10.0). IPL-weighted and strict-sample configs check associate-nation inflation.

## 12. Sensitivity & stability

The full rating was re-run under nine configurations: three thresholds (0.50/0.55/0.60), two alternative
batting definitions (chase-centric; death-and-collapse with no RRR), two bowling definitions (death-heavy;
defend-heavy), a strict-sample variant, and three weight mixes. The context-matched baseline and balanced
bowling consistency are applied inside *every* config, so reliability reflects the final model. **Rock-solid**
picks (≥89% of configs): Naman Dhir, Rishabh Pant among batters; Haris Rauf (100%), Mitchell Starc and Nathan
Ellis among bowlers. **More model-dependent** (flagged honestly): Rohit Sharma and Shubman Gill (33%) among
batters — strong under the primary absolute-leaning model but sample-light, so they move under alternative
definitions.

## 13–14. Evidence for the top 10

See the tables in §1 and figures `top_batters.png` / `top_bowlers.png`. Example reads: **Matthew Wade** —
pressure SR 162 vs 110 context-matched baseline (+52) over 229 pressure balls, top-10 in 67% of configs;
**Haris Rauf** — pressure economy 8.31 (baseline 9.16) with 0.59 wkts/over over 283 pressure balls, top-10 in
100% of configs.

## 15. IPL-availability — an optional, secondary view

The problem statement does not ask for a nationality filter, so the **primary rankings apply none**.
Separately, because Rajasthan Royals is an IPL franchise, we provide an *optional* view that removes players an
IPL side cannot sign. Nationality is **inferred** from the national team a player represents in T20Is — a
data-only heuristic that is **not independently verified** (players with no T20I record, e.g. several uncapped
Indian bowlers here, cannot be classified). It is therefore a secondary lens only. Removing the flagged players
and re-ranking yields the IPL-available top-10s in `outputs/*_ipl_available.csv` and the dashboard.

## 16. Model validation

- Unit-tested cricket logic (11/11): reconstruction, legal-ball counting, wicket credit, RRR, no-future-leakage.
- Innings totals cross-checked vs 356 result margins (median error 0).
- Pressure intensity rises monotonically through the innings and differs by role.
- Context-matched baseline removes the death-over confound; per-phase shrinkage controls thin samples.
- Sample-size-vs-score plots show no runaway small-sample effect.
- Rankings stable across nine configurations.

## 17. Limitations

- Approximate targets (±1–3 runs; DLS excluded from chase logic).
- Pressure is a modelling choice, not an official RR definition (mitigated by nine configs + reliability).
- Context-matched baselines lean on thin death-over non-pressure samples; shrinkage controls but does not eliminate this.
- IPL-availability is secondary and uses inferred, unverified nationality; uncapped players cannot be classified.
- No fitted win-probability model (closeness proxied by RRR/wickets/phase).

## 18. Conclusion

The framework turns "clutch" into a reproducible, delivery-level measurement: a transparent pressure index,
phase-fair self-referenced performance, an absolute-leaning and shrinkage-protected rating, and a nine-way
robustness check. Every name is backed by its own pressure-versus-baseline numbers and a reliability score, and
every figure is traceable to the supplied data via the accompanying code and dashboard.
