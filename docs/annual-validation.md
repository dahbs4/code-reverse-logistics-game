> Historical: this report predates weekly-only planning. See [weekly model validation](weekly-validation.md) for the current game.

# Annual campaign update

New games last 52 operating weeks (364 days / 8,736 hours). Backlog warnings do
not end a campaign early; the score and backlog threshold determine the final
outcome at the end of the year. Older saves retain their stored duration.

Physical processing limits now apply in addition to labor and category effort:

| Site | Normal units/week | June–July units/week | Hard maximum units/week |
| --- | ---: | ---: | ---: |
| Indianapolis | 1,000,000 | 1,000,000 | 1,000,000 |
| East Coast | 450,000 | 420,000 | 500,000 |

East Coast overtime can increase its normal limit up to the hard maximum. Limits
are distributed hourly without carryover. A week crossing a month boundary uses
each hour's applicable seasonal rate.

Forecast & planning now includes the whole campaign: original forecasts, closed
week removal actuals, partial current-week actuals, and a revised annual outlook.
At week close, the latest four completed weeks' actual-to-baseline ratio revises
future forecasts. Baseline includes seasonal demand, monthly DC removal pulses,
holiday demand, and difficulty. The annual ledger is included in save/restore.
The Instructions navigation page explains the operating cycle and these rules.

Validation:

- 54 engine, simulated-player, and annual-model tests passed. Annual coverage
  includes enforced physical ceilings with abundant labor, summer dates,
  weekly forecast revisions, four-week lookback, forecast-only multipliers,
  save/load preservation, legacy saves, and a 52-week clock run.
- 3 API tests passed, including annual fields, weekly actuals, and checkpoint restore.
- 2 frontend unit tests passed; the production frontend build succeeded.
- Both Chromium browser tests passed. The annual view and Instructions were
  checked before play; a completed removal week updated the chart and all 52
  table rows; restore reset the forecast ledger. Full gameplay executed all 52
  weeks with real default freight generation, reached the terminal state, and
  disabled advancement. Desktop, tablet, and phone layouts were checked with no
  page errors. The full gameplay test took 7.2 minutes on this environment.

Previous validation reports and numerical player tournaments describe the former
28-day rules. They have not been rerun as 32 annual campaigns.
