# Simulated player tournament

Deterministic rule-based players use the same actions and engine as human players. Each turn advances up to 24 hours; engine invariants run every simulated hour. These seeded episodes compare strategies; they do not establish optimal play.

Episodes: 32. All terminal states reached; freight conservation balance is zero in every episode.

| Player | Scenario | Difficulty | Runs | Wins | Mean score | Score range | Mean hours | Mean processed | Mean cost |
| --- | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| baseline | stable | standard | 2 | 2 | 72.3 | 71.6–73.0 | 672 | 2,951,066 | 7,782,065.20 |
| baseline | crisis | standard | 2 | 2 | 65.5 | 64.5–66.4 | 672 | 2,659,796 | 5,263,294.04 |
| baseline | peak | standard | 2 | 0 | 61.5 | 61.1–61.9 | 648 | 2,318,984 | 8,636,284.40 |
| baseline | breakdown | standard | 2 | 2 | 67.3 | 67.3–67.4 | 672 | 2,944,841 | 8,179,125.74 |
| hands_off | stable | standard | 2 | 2 | 73.3 | 71.9–74.7 | 672 | 3,156,663 | 5,193,140.04 |
| hands_off | crisis | standard | 2 | 1 | 60.0 | 59.9–60.1 | 672 | 2,267,582 | 4,201,753.83 |
| hands_off | peak | standard | 2 | 0 | 61.6 | 61.3–61.9 | 648 | 3,077,646 | 6,854,423.98 |
| hands_off | breakdown | standard | 2 | 2 | 70.2 | 68.4–71.9 | 672 | 2,238,832 | 5,446,176.49 |
| cost_conscious | stable | standard | 2 | 2 | 70.4 | 68.3–72.5 | 672 | 3,128,734 | 5,351,620.04 |
| cost_conscious | crisis | standard | 2 | 0 | 59.5 | 59.4–59.6 | 672 | 2,602,020 | 4,572,928.46 |
| cost_conscious | peak | standard | 2 | 0 | 59.2 | 59.1–59.2 | 648 | 2,826,164 | 7,242,088.89 |
| cost_conscious | breakdown | standard | 2 | 2 | 65.6 | 65.6–65.6 | 672 | 2,381,080 | 5,262,513.04 |
| adaptive_throughput | stable | standard | 2 | 2 | 84.2 | 84.0–84.4 | 672 | 5,024,564 | 10,467,647.46 |
| adaptive_throughput | crisis | standard | 2 | 2 | 67.6 | 67.4–67.7 | 672 | 4,038,282 | 11,166,026.88 |
| adaptive_throughput | peak | standard | 2 | 0 | 70.0 | 69.9–70.0 | 648 | 6,593,856 | 12,288,754.03 |
| adaptive_throughput | breakdown | standard | 2 | 2 | 84.5 | 84.4–84.6 | 672 | 5,024,564 | 10,890,140.36 |

## Players

- **baseline**: Original demonstration player: fixed dispatch targets and small queue-based labor transfers.
- **hands_off**: Keeps the existing operating plan with no new decisions or investments.
- **cost_conscious**: Uses value freight, regular labor, and queue-based allocation without overtime or investment.
- **adaptive_throughput**: Uses the available roster, queue-based allocation, and pressure-triggered overtime and faster freight.

Results include full score components, costs, remaining freight, and seeds in the accompanying JSON. Wins use the engine’s target score and terminal rules. A backlog loss takes precedence over the score: a peak-season episode can lose even with a score at or above 60. Early losses may have fewer hours, processed units, and costs.
