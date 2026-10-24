# WattWise implementation phases

This folder is the implementation roadmap for the WattWise MVP. Each phase defines a complete platform component, its user-facing features, implementation areas, dependencies, tests, and completion gate. The phase documents are intended to be used with the requirements and domain rules in `../SYSTEM_DESIGN.md`.

## Decisions reflected here

- The web app uses Flask with HTML, CSS, and JavaScript. The starter's Gradio screen is not a product requirement.
- The starter repository is a guide and a source of reusable setup ideas. WattWise keeps its own architecture and requirements.
- Both prepaid and postpaid customer journeys are first-class MVP features.
- Users enter appliances and their usual routines. Qwen proposes editable goal-based daily and weekly routines for both payment modes.
- Python owns all authoritative energy, duration, comparison, and cost calculations.
- Qwen3-0.6B is the current local model candidate. The app talks to the current standalone `llama.cpp` server over localhost; it does not depend on the starter's pinned Python binding.
- Qwen inference is required for AI routine generation; core bill and meter calculations remain usable when the model is stopped or unavailable.
- Each household can use a local email/password account. Passwords are hashed, JWT sessions are used, and account-owned profiles and analysis history are stored in local SQLite.
- No OCR, cloud storage, payments, meter control, or automatic DisCo integration is part of the MVP.

## Phase sequence

| Phase | Complete component | Depends on | Main completion gate |
|---|---|---|---|
| [00 — Repository foundation](00-repository-foundation.md) | WattWise repo and runnable Flask skeleton | None | Clean local startup and health route |
| [01 — Domain research and contracts](01-domain-research-and-contracts.md) | Confirmed bill terminology, request/response contracts, sample cases | Phase 00 | Team agrees on data shapes and hand-checked examples |
| [02 — Appliances and routines](02-appliances-and-routines.md) | Appliance entry, routine data, catalogue estimates, assumption labels | Phase 01 | A household can describe its appliance schedule without AI |
| [03 — Deterministic calculation engine](03-calculation-engine.md) | Appliance kWh, household totals, tariff arithmetic, assumptions | Phases 01–02 | Core calculations pass unit tests independently of Flask/model |
| [04 — Prepaid planning](04-prepaid-planning.md) | Available-unit budget, projected duration, target feasibility, routines | Phases 02–03 | Complete prepaid analysis returns calculated alternatives |
| [05 — Postpaid bill analysis](05-postpaid-analysis.md) | Bill inputs, reading derivation, charge checks, comparisons | Phases 02–03 | Complete postpaid analysis handles optional bill fields safely |
| [06 — Flask API and browser workflows](06-flask-api-and-web-ui.md) | API routes, services, responsive forms and results | Phases 01–05 | Browser completes both flows using server results |
| [07 — Local Qwen explanations](07-local-qwen-explanations.md) | Local model adapter, goal-based JSON schedules, verification, and explanations | Phase 06; model smoke test already done | AI plans for both modes are verified without changing calculation authority |
| [08 — Integration testing and hardening](08-integration-testing-hardening.md) | End-to-end, failure, privacy, and target-machine verification | Phases 03–07 | Both workflows pass on the demo machine with and without AI |
| [09 — Local accounts and persistence](09-local-accounts-and-persistence.md) | JWT authentication, local SQLite users, saved routines, and analysis history | Phases 06–08 | Two users have persistent, isolated local data |
| [10 — Documentation and demo release](10-documentation-demo-release.md) | Reproducible setup, licences, sample data, demo package | Phases 08–09 | A new person can run or review the project |

Phase 01 working artifacts are in [`contracts/`](contracts/API_CONTRACTS.md), including route contracts and hand-checkable prepaid/postpaid request and result examples.

## Team ownership

- **Developer A (you):** repository/app integration, Flask routes and services, HTML/CSS/JavaScript, local model adapter, setup and demo documentation.
- **Developer B (teammate):** appliance energy calculations, tariff arithmetic, prepaid planner, postpaid reconciliation, routine scenarios, and calculation tests.
- **Shared:** Phase 01 contracts, example validation, integration reviews, final tests, model limitations and demo.

The two developers can work in parallel after Phase 01 freezes the shared request/result shapes. Merge one small working slice at a time and keep the main branch runnable.

## Cross-phase rules

1. Missing data remains missing; it is never silently converted to zero.
2. Label user-entered, measured, catalogue-estimated, and calculated values distinctly.
3. A prepaid top-up receipt's units credited are not automatically the meter balance currently available.
4. A postpaid total due is not the same as an energy charge.
5. Essential appliances are protected in routine suggestions unless the user explicitly edits them.
6. The local model proposes goal-based routine JSON for prepaid and postpaid users; Python recalculates every schedule and reports whether the goal is met.
7. No private bills, model weights, local environment files, tokens, or secrets go into Git.

