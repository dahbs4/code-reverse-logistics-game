# Weekly planning model

The game now exposes one decision: planned processing units per week for each
site. The browser and API advance one week only. Shift/day requests are rejected;
manual labor, dispatch, appointment, trailer, and equipment controls were removed.

The default view contains two target inputs, next week's inventory balance, and
a chart of ending backlog through the remaining campaign. It previews edits
without committing them. Unsaved edits block advancement until saved or reverted.
The outlook repeats the plan, uses the latest annual removal forecast, respects
site/scenario capacity, and carries each site's backlog independently.

Weekly execution uses an aggregate capacity model. Seeded weekly removals vary
±5% from the seasonal baseline. Available freight is processed oldest first up to
the target and scenario capacity. Unprocessed freight becomes next week's
carryover. Labor and freight costs are estimated automatically; East Coast output
above its typical rate has an automatic surge-labor premium. The former hourly
engine remains internally for legacy regression checks, not as a play mode.

Validation:

- Weekly model checks cover forecast purity, target-driven backlog changes,
  independent site inventories, zero plans, hard limits, seasonal usual rates,
  scenario capacity, deterministic save/load, partial legacy weeks, and all 52 weeks.
- Forecast/execution consistency is checked with controlled removal volume in
  stable, transport-crisis, and facility-breakdown scenarios.
- API tests reject daily/shift steps and invalid targets; they verify weekly
  preview isolation, committed targets, conservation, checkpoint restore, a full
  annual campaign, and terminal controls.
- Both browser tests passed, including live outlook changes, invalid inputs,
  blocking advancement of unsaved edits, persistence, restore, all 52 weekly
  advances, annual actuals, results, and tablet/phone overflow checks. No page
  errors occurred. Full weekly gameplay took 16.1 seconds in this environment.
- Frontend unit checks and production build passed.
- All 32 simulated-player episodes were rerun with weekly decisions over 52
  weeks, reaching terminal states with freight conservation intact. See
  [the weekly player report](player-simulation-report.md).

The earlier annual-update validation report describes the preceding detailed
logistics model and is retained as historical context.
