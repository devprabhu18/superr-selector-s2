# Methodology development notes – SupeRR Selector

## Challenge interpretation
Round 1 requires two ordered top-10 lists: batters and bowlers who perform most reliably in high-pressure match situations, plus a transparent methodology report.

## Initial data inventory
The supplied files include delivery-level ball-by-ball data, match metadata, competition metadata, playing-XI records, team/player competition mappings and team metadata. The ball-by-ball file inspected contains 200,999 rows and 867 distinct match IDs. The matches file contains 883 match IDs. Competition metadata includes T20 and T20I formats and seasons from 2022 through 2026.

## Provisional pressure hypothesis
A transparent first hypothesis is to identify late-innings situations where the batting side has already lost several wickets. The prototype marks a delivery as pressure when:
- the over number is at or beyond a configurable late-innings threshold; and
- at least a configurable number of wickets had already fallen before that delivery.

This is only a starting point. It does not yet incorporate required run rate, target proximity, balls remaining, or match closeness. Those should be added after correct innings totals can be reconstructed.

## Baseline comparison
Compare each player's pressure performance with that player's non-pressure performance, rather than comparing raw pressure numbers alone.

Potential batter measures:
- strike rate under pressure vs baseline;
- runs per dismissal under pressure vs baseline;
- boundary and dot-ball rates if definitions are validated;
- pressure sample size and match count.

Potential bowler measures:
- wicket rate under pressure vs baseline;
- dot-ball percentage under pressure vs baseline;
- runs conceded per legal ball / economy only after extras are validated;
- credited wickets only, excluding run-outs and other non-bowler dismissals;
- pressure sample size and match count.

## Reliability
Apply minimum pressure-ball thresholds and shrink small-sample uplifts toward zero. Report the actual pressure balls and matches alongside every score. Run sensitivity analysis across multiple pressure definitions and minimum sample thresholds.

## Data-quality issue to resolve
`extras1_runs` has values that appear categorical (e.g. 6 on ordinary deliveries, 2 on wides, 3 on leg-byes, 4 on byes). Do not interpret it as a direct number of extras. Confirm the data dictionary for `runs`, `extras1_runs`, and `extras_2_runs` before calculating team totals, required run rate, or official bowling economy.

## Final report should document
1. Exact pressure definition and cricketing rationale.
2. Batter and bowler metrics and player-specific baselines.
3. Eligibility rules and sample-size handling.
4. IPL/T20I treatment and competition context.
5. Final ranked lists with supporting evidence.
6. Sensitivity analysis, reliability and limitations.
