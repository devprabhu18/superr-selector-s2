# Data Dictionary — SupeRR Selector Season 2 Data Pack

*Phase 1 deliverable. All facts below are derived directly from the supplied files
(`6af3166e7b922_data_pack/`) via `scripts/dataset_profile.py`, `validate_extras.py`,
`integrity_checks.py`, `anomaly_probe.py`. Row counts verified, not assumed.*

## File inventory (verified)

| File | Rows | Cols | Grain (primary key) |
|------|-----:|-----:|---------------------|
| `competitions.csv` | 141 | 4 | `comp_id` |
| `teams.csv` | 353 | 3 | (`comp_id`, `team_id`) |
| `matches.csv` | 883 | 22 | `match_id` |
| `playing_eleven.csv` | 28,381 | 9 | (`match_id`, `team_id`, `player_id`) |
| `competition_team_player_mapping.csv` | 6,413 | 6 | (`comp_id`, `team_id`, `player_id`) |
| `ball_by_ball.csv` | 200,999 | 33 | (`match_id`, `innings`, `innings_ball_num`) |

Relationships: `ball_by_ball.match_id → matches.match_id → matches.comp_id → competitions.comp_id`.
Teams join via `team_id`; players via `player_id`. All joins verified (see quality report).

---

## competitions.csv
| Column | Type | Notes |
|--------|------|-------|
| `comp_id` | int | PK. 141 competitions. |
| `comp_name` | str | e.g. "IPL 2024", "India in England T20I Series 2022". |
| `match_format` | str | **Two values: `T20` (IPL franchise comps) and `T20I` (internationals).** |
| `season` | str | 2022, 2022/23, 2023, 2023/24, 2024, 2024/25, 2025, 2026. |

**IPL competitions** (all `match_format = T20`): comp_id 1358 (IPL 2022), 1715 (2023), 2193 (2024), 2725 (2025), 3298 (2026). Note: a few other `T20` comps exist (e.g. Emerging Teams Asia Cup, Asia Cup Rising Stars) — "T20" ≠ "IPL".

## teams.csv
| Column | Type | Notes |
|--------|------|-------|
| `comp_id` | int | FK → competitions. |
| `team_id` | int | 38 distinct teams across the pack. |
| `team_name` | str | National sides + IPL franchises. |

Grain = which teams participated in which competition.

## matches.csv
| Column | Type | Notes |
|--------|------|-------|
| `match_id` | int | PK. 883 matches. |
| `comp_id` | int | FK → competitions (138 distinct). |
| `match_number` | int | Match number within competition. |
| `match_date` | str (date) | 2022-01-22 … 2026. |
| `stage` | str | League (620), Others (226), Final (12), Qualifier (10), Super 4 (6), Eliminator (5), Semi Final (4). |
| `venue_id`, `venue_country` | int / str | 98 venues, 17 countries (India 425 most common). |
| `home_team_id` / `home_team` / `away_team_id` / `away_team` | | Participating teams. |
| `home_team_captain_id` / `away_team_captain_id` | float | 44 / 45 nulls. |
| `toss_win_team_id` / `toss_opted` | float / str | `toss_opted` ∈ {Fielding (639), Batting (229)}; 15 nulls. |
| `man_of_the_match` | int | player_id (0 = none / not recorded). |
| `first_inn_revised_overs` / `second_inn_revised_overs` / `revised_target` | float | **DLS / rain-affected flags.** 858–860 nulls → only ~23 rain-affected matches. |
| `knock_out` | int | 1 = knockout match (31), else 0. |
| `win_team_id` | float | Winner team_id; **41 nulls** (no-result / tie / abandoned). |
| `result` | str | Free text, e.g. "England Won by 1 Run", "Gujarat Titans Won by 5 Wickets", "… (DLS method)". Parseable for margin. |

## playing_eleven.csv
| Column | Type | Notes |
|--------|------|-------|
| `match_id`, `team_id`, `player_id` | int | Composite grain. 880 matches, 1,082 players. |
| `batting_order` | float | 8,678 nulls (did not bat / unused impact sub). |
| `is_played` | bool | Whether player actually featured. |
| `is_captain` / `is_wk` | object (True/False) | 8,667 nulls. Role flags. |
| `is_impact` / `is_impact_off` | int (0/1) | Impact Player substitution flags (IPL rule). |

## competition_team_player_mapping.csv
| Column | Type | Notes |
|--------|------|-------|
| `comp_id`, `comp_name`, `team_id`, `team_name` | | Squad context. |
| `player_id` | int | 1,217 distinct. |
| `player_name` | str | 1,210 distinct (a few shared names — see quality report). Primary id→name source. |

## ball_by_ball.csv (33 columns)

### Identity & sequence
| Column | Type | Notes |
|--------|------|-------|
| `match_id` | int | FK → matches. 867 distinct. |
| `innings` | int | **1, 2 = main innings; 3, 4 = Super Overs (6 matches only).** |
| `overid` | int | Over number, 1–20. |
| `over_ball_num` | int | Ball within over (1–13; >6 when extras bowled). |
| `innings_ball_num` | int | Sequential ball within innings (1…). Part of PK. |
| `batting_team_id` / `bowling_team_id` | int | FK → teams. |

### Players
| Column | Type | Notes |
|--------|------|-------|
| `striker_id` / `striker_name` | int / str | **Batter on strike. Key on `striker_id`.** 888 ids. |
| `non_striker_id` / `non_striker_name` | int / str | Batter at non-striker's end. |
| `bowler_id` / `bowler_name` | int / str | **Bowler. Key on `bowler_id`.** 647 ids. |
| `batting_type` | str | RHB / LHB. |
| `bowling_type` | str | 12 values (e.g. "Right-arm Fast", "Slow left-arm orthodox"). |
| `batting_order` | int | Position in order. |
| `pace_or_spin` | str | Pace / Spin. |

### Outcome (the critical block — see quality report §1)
| Column | Type | **Validated meaning** |
|--------|------|-----------------------|
| `runs` | int (0–6) | **Runs off the bat only (batter's runs).** Exact & reliable. Confirmed against `is_four`/`is_six`. |
| `is_four` / `is_six` | bool | Boundary flags (consistent with `runs`). |
| `is_wicket` | bool | A dismissal occurred on this ball (10,881 total). |
| `dismissal_type_id` / `dismissal_type` | float / str | Caught (7,557), Bowled (1,775), LBW (709), RunOut (600), Stump (214), Hit Wicket (17), Retire Out (6), Obstructing/Obstracting the field (3). Null when no wicket. |
| `dismissed_player_id` | float | Who was out (can differ from striker on run-outs). |
| `extras_type` | str | NaN = legal delivery (no extra). Else: `wide` (7,714), `legbyes` (2,748), `byes` (529), `Overstep` = no-ball (576), `other` (264), `Penalty` (1). |
| `extras1_runs` | int | **NOT a run amount — a one-to-one CODE for `extras_type`:** 1=Overstep, 2=wide, 3=legbyes, 4=byes, 5=other, 6=none(legal), 7=Penalty. **Do not sum this field.** |
| `extras_2_runs` | int | Additional runs on an extra delivery. Almost always 0 (only 36 rows: 20×1, 16×4). Magnitudes of most byes/legbyes/multi-run wides are **not** recorded. |

### Context / descriptive (available, lower priority)
| Column | Type | Notes |
|--------|------|-------|
| `bowl_speed` | float | kph; 0 used as missing for many balls. |
| `stroke` | str | 30 shot types (6,158 nulls). |
| `delivery_style` | str | 34 values (391 nulls). |
| `over_or_around` / `on_or_off` | str | Bowling angle / side. |
| `delivery_ist_time` | str | Timestamp (UTC despite name); near-unique per ball. |

---

## Derived fields the pipeline will build (all from reliable columns)

| Field | Definition |
|-------|------------|
| `legal_ball` | `extras_type ∉ {wide, Overstep, other}` — counts toward the 6-ball over. (`other` behaves as a re-bowled delivery; see quality report §3.) |
| `batter_ball_faced` | `extras_type ∉ {wide}` (a no-ball is faced; byes/legbyes are faced). |
| `bowler_wicket` | `is_wicket AND dismissal_type ∉ {RunOut, Retire Out, Obstructing/Obstracting the field}` → 10,272 credited. |
| `bowler_runs_conceded` | `runs` (off bat) + 1 per wide + 1 per no-ball + `extras_2_runs`. (Byes/leg-byes are **not** charged to the bowler — standard scoring.) |
| `team_runs` | `runs` + extras penalty (approximate; see quality report §1 on under-count). |
| `wickets_fallen_before` / `wickets_in_hand` | Cumulative, computed chronologically. |
| `balls_remaining`, `runs_required`, `required_run_rate` | 2nd-innings match state, computed chronologically (target approximate). |
