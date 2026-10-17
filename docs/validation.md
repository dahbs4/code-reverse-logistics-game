> Historical reference: this document describes the previous 28-day game. Current new campaigns last 52 weeks and enforce physical site throughput limits.

# Validation report

Validated in the cloud workspace on October 16, 2026, with Python 3.12.14, Node 24.19.0, npm 11.9.0, and system Chromium through Playwright.

- **29 backend tests passed** (`.venv/bin/python -m pytest -q`). Coverage includes conservation, nonnegative inventory/costs, unique lots, category handling, trailer size and fleet constraints, transportation ordering, rejection/retender, appointments, separate labor bottlenecks, carryover, accounting, equipment costs, seasonality and DC removal pulses, reproducibility, save/load, multi-step equivalence, action validation, routing, preview isolation, event effects/recovery, terminal behavior, and API response/command validation.
- **2 frontend unit tests passed** (`npm --prefix frontend test`). These check operational number presentation and combined inventory arithmetic. They are supplemented by real rendering and interaction tests below.
- **1 complete browser gameplay test passed**, including the full 28-day Stable Operations scenario, at desktop, tablet, and phone widths. It changed and previewed a plan, committed it, advanced time, saved/restored a checkpoint, reloaded persistent state, inspected a DC and its store IDs, viewed decisions and financials, executed four weeks, verified a terminal result and disabled advancing, and checked viewport overflow. No browser page errors were reported. Final test duration: 19.0 seconds (20.1 seconds including runner overhead). The demonstrated plan finished with a score of 77.2.
- **Production TypeScript/Vite build passed**. Chart and network dependencies are split into separate bundles.
- **Setup script passed on repeat execution** (`bash scripts/setup.sh`), including frozen frontend installation and build. **Startup wrapper passed** (`bash scripts/start.sh`) after stopping the separately launched development services. Functional requests through the Vite proxy generated and executed an 8-hour game: 41,444 units processed, costs accrued, and freight conservation held. Services were left running through the startup wrapper. Only games created by these browser/startup checks were removed afterward.
- **8 seeded agent episodes terminated with invariants intact at every executed hour**: all four scenarios with seeds 42 and 137. See `validation-results.json` for the complete numerical ledger. Stable, crisis, and breakdown completed 672 hours; both peak episodes lost at hour 648 after the seasonal demand baseline fell with a large backlog still present. A lost game is a gameplay outcome, not an invariant failure. The baseline policy is not an optimal controller.

| Scenario | Seed 42 | Seed 137 |
| --- | --- | --- |
| Stable Operations | Won · 73.0 | Won · 71.6 |
| Transportation Crisis | Won · 64.5 | Won · 66.4 |
| Peak Season | Lost · 61.1 | Lost · 61.9 |
| Facility Breakdown | Won · 67.4 | Won · 67.3 |

Screenshots in `screenshots/` were captured from the real application. Desktop and tablet images were visually inspected. The tablet map was corrected to refit after viewport changes, and the final browser test explicitly checks recovery-node containment. A phone screenshot is also included.

The Playwright-managed browser download was denied by network policy. The installed `/usr/bin/chromium` worked, so browser execution is **verified**, not skipped. No TLS, checksum, or package verification was disabled. Pytest emits a dependency deprecation warning for Starlette's AnyIO portal alias; npm reports the Recharts 2.x maintenance notice. Neither prevented the recorded checks.

Not validated: PostgreSQL, multi-user deployment, fresh-task snapshot restoration, or publication of this cloud environment. Remaining feature scope is listed explicitly in the README.
