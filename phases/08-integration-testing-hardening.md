# Phase 08 — Integration testing and hardening

**Status:** In progress.

## Current progress

- Hand-checked prepaid and postpaid fixtures pass through the deterministic calculation services.
- The prepaid and postpaid browser journeys were manually exercised with synthetic values, including routine alternatives and postpaid readings.
- A real local Qwen structured routine proposal and explanation request have returned successfully through Flask after disabling model reasoning for this short task.
- Automated tests cover core calculations, API validation and model-unavailable fallback, plus mocked adapter success, timeout, connection error, malformed model JSON, unknown routine IDs, and oversized output.
- Malformed JSON now returns a `400 MALFORMED_JSON` response; ordinary invalid fields retain `422 VALIDATION_ERROR`.
- Remaining before this phase is complete: verify the updated UI disclosure in-browser, exercise the browser explanation failure state, and rehearse the documented cold start on the demo machine.

## Outcome

Demonstrate that the full platform behaves correctly from the browser through Flask, calculations, routines, and optional local inference on the actual intended demo machine.

## Implement and verify

1. Calculation unit tests: appliance methods, schedules, tariff arithmetic, zero/missing inputs, rounding, duration, readings, and scenarios.
2. API tests: health, both analysis modes, validation, optional bill fields, malformed requests, request bounds, and stable response envelopes.
3. Adapter tests with a mocked llama server: success, timeout, connection error, invalid JSON, invalid appliance schedule, unknown routine ID, and oversized output. Automated tests must not require model downloads.
4. Browser journey checks: prepaid top-up context/current balance, appliance entry, AI schedule refinement to the duration goal, essential-appliance protection; postpaid bill entry, optional readings/charges, user reduction goal, AI schedule comparison, assumptions; explanation and fallback states.
5. Verify manual sample calculations against the hand-checked Phase 01 fixtures.
6. Test a clean local setup on the intended demo machine. Confirm model download/cache, CPU inference, JSON schedule quality, refinement wait time, Flask/model startup instructions, and goal status. Keep model inference out of health checks and basic calculation endpoints.
7. Review privacy and robustness: no bill-body logging, no tokens/identifiers requested, no secret/model files in Git, model/user text escaped, and errors do not leak stack traces.

## Components and links

- Exercises every phase as a connected system and feeds fixes back to the owning phase.
- Must pass before Phase 09's recorded/live demo is prepared.

## Ownership

Shared. Developer A leads API/UI/runtime integration checks. Developer B leads formula and scenario checks. Both run the clean-start demo and review limitations.

## Verify and exit gate

- Automated tests pass without requiring the actual Qwen weights.
- Both end-to-end journeys work with model enabled and with model unavailable.
- Displayed comparisons and assumptions match the submitted inputs and fixture outputs.
- The app starts from documented steps on the demo machine without relying on an already-running hidden process.

