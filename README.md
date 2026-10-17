# Reverse Network: Weekly Operations

A browser game for planning a national reverse logistics network over 52 weeks.
Set planned units per week for Indianapolis and East Coast, see the projected
backlog against the removal forecast, and advance one week at a time.

## Install and start

Requires Python 3.12+, Node 22+, and npm. No paid services, keys, or external
database are required.

```bash
bash scripts/setup.sh
bash scripts/start.sh
```

Open `http://localhost:5173` on the machine running the app. In GitHub Codespaces,
use **Ports → 5173 → Open in Browser**. FastAPI runs on port 8000; Vite proxies
`/api` requests. Stop the server with Ctrl+C before pulling and restarting.
SQLite saves campaigns in ignored `data/games.db`; dependencies and databases
are excluded from Git. This is a single-operator demo with no authentication.

## Weekly play

1. Choose a scenario and seed. Hard difficulty adds 10% removal volume.
2. On **Weekly plan**, enter planned processing units for each site.
3. Review next week's balance: starting backlog + forecast removals − projected
   processing = projected ending backlog. The chart repeats your targets across
   the remaining year to estimate ending backlog in every week.
4. Click **Save weekly plan**. Unsaved edits change only the outlook, and
   advancement is disabled until you save or undo the edit.
5. Click **Advance one week**. The model executes one aggregate operating week,
   records removal actuals, processes available freight, and carries backlog forward.
6. Review **Annual outlook** and adjust targets for the next week. Your saved
   targets repeat until you change them. Checkpoints save and restore the full state.

There are no daily/shift advances or manual dispatch, appointment, trailer, labor,
or equipment controls. **Instructions** explains the weekly model inside the app.

| Site | Typical units/week | June–July typical | Maximum units/week |
| --- | ---: | ---: | ---: |
| Indianapolis | 600,000 | 600,000 | 1,000,000 |
| East Coast | 450,000 | 420,000 | 500,000 |

East Coast targets above the typical rate automatically incur a surge labor
premium. Processing cannot exceed available freight, the planned target, or
scenario-adjusted capacity. Each site's backlog stays assigned to its fixed DC
routing. The Transportation Crisis acceptance factor and Indianapolis equipment
factor in Facility Breakdown reduce available weekly capacity. Weekly removals
vary by a seeded ±5% draw; detailed daily logistics are not executed by the game.

The annual removal baseline includes seasonality, holidays, difficulty, and monthly
DC removal pulses. After each closed week, the last four completed weeks'
actual/baseline ratio (bounded to 0.5–2.0) revises future removal forecasts. Changing
processing targets changes the backlog outlook, not forecast removal demand.
The outlook uses the same site and scenario constraints as weekly execution but
does not see future random draws.

Finish 52 weeks (364 days) with at least 60 points and inventory below 40 seasonal
demand-days. Backlog warnings do not end a campaign early. Older saves keep their
original duration; a partially completed week advances to its next boundary.

## Simulated players and checks

The four players use the same weekly target contract as humans: baseline, hands-off,
cost-conscious, and adaptive. They are deterministic examples, not optimal policies.

```bash
.venv/bin/python -m pytest -q
npm --prefix frontend test
npm --prefix frontend run build
# Start the app before browser checks:
npm --prefix frontend run e2e
# Compare all players, four scenarios, and two seeds:
.venv/bin/python -m scripts.simulate_players
# One comparison with weekly traces:
.venv/bin/python -m scripts.simulate_players --players adaptive_throughput --scenarios stable --seeds 42 --trace-dir /tmp/player-traces
.venv/bin/python -m simulation.agent --scenario stable --seed 42 --output /tmp/episode.jsonl
```

[Weekly model validation](docs/weekly-validation.md) describes the checks.
[Player results](docs/player-simulation-report.md) compare weekly strategies.
The former hourly engine remains as an internal legacy module with regression tests;
it is not exposed as a play mode. Older architecture and validation documents describe
previous versions and are marked historical.
