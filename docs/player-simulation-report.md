# Simulated player tournament

Deterministic rule-based players use the same actions and engine as human players. Each turn executes one weekly unit plan; conservation is checked after each week. These seeded episodes compare strategies; they do not establish optimal play.

Episodes: 32. All terminal states reached; freight conservation balance is zero in every episode.

| Player | Scenario | Difficulty | Runs | Wins | Mean score | Score range | Mean hours | Mean processed | Mean cost |
| --- | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| baseline | stable | standard | 2 | 0 | 61.8 | 61.8–61.9 | 8736 | 58,500,000 | 133,910,911.72 |
| baseline | crisis | standard | 2 | 0 | 57.3 | 57.2–57.4 | 8736 | 39,000,000 | 187,649,791.71 |
| baseline | peak | standard | 2 | 0 | 60.7 | 60.6–60.7 | 8736 | 58,500,000 | 118,958,188.75 |
| baseline | breakdown | standard | 2 | 0 | 61.0 | 61.0–61.1 | 8736 | 48,100,000 | 162,583,607.71 |
| hands_off | stable | standard | 2 | 2 | 67.2 | 66.8–67.5 | 8736 | 73,304,748 | 91,357,557.78 |
| hands_off | crisis | standard | 2 | 0 | 57.3 | 57.2–57.4 | 8736 | 39,000,000 | 187,649,791.71 |
| hands_off | peak | standard | 2 | 2 | 67.3 | 66.6–68.0 | 8736 | 70,610,756 | 78,626,625.12 |
| hands_off | breakdown | standard | 2 | 0 | 62.3 | 62.3–62.4 | 8736 | 52,000,000 | 151,857,878.40 |
| cost_conscious | stable | standard | 2 | 0 | 60.7 | 60.7–60.7 | 8736 | 52,000,000 | 151,764,071.71 |
| cost_conscious | crisis | standard | 2 | 0 | 57.3 | 57.2–57.4 | 8736 | 39,000,000 | 187,649,791.71 |
| cost_conscious | peak | standard | 2 | 0 | 60.6 | 60.6–60.6 | 8736 | 52,000,000 | 136,811,348.75 |
| cost_conscious | breakdown | standard | 2 | 0 | 60.6 | 60.6–60.6 | 8736 | 46,800,000 | 166,130,319.71 |
| adaptive_throughput | stable | standard | 2 | 2 | 83.4 | 82.5–84.3 | 8736 | 75,370,340 | 87,714,420.09 |
| adaptive_throughput | crisis | standard | 2 | 0 | 57.3 | 57.2–57.4 | 8736 | 39,000,000 | 187,649,791.71 |
| adaptive_throughput | peak | standard | 2 | 2 | 73.8 | 72.7–75.0 | 8736 | 71,565,351 | 73,652,284.57 |
| adaptive_throughput | breakdown | standard | 2 | 0 | 62.9 | 62.7–63.0 | 8736 | 54,166,322 | 147,310,891.40 |

## Players

- **baseline**: Plans 750,000 Indianapolis units and 375,000 East Coast units each week.
- **hands_off**: Retains the initial weekly targets (1,000,000 Indianapolis and the seasonal East Coast default).
- **cost_conscious**: Plans 650,000 Indianapolis units and 350,000 East Coast units each week.
- **adaptive_throughput**: Plans forecast removals plus one quarter of site backlog, up to each site maximum.

Results include full score components, costs, remaining freight, and seeds in the accompanying JSON. Wins use the engine’s target score and terminal rules. Backlog is assessed at the end of the 52-week campaign: a peak-season episode can lose even with a score at or above 60. The year continues despite midyear backlog warnings.
