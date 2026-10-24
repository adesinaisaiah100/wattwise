# Phase 07 — Local Qwen routine planning and explanations

## Outcome

Make local open-weight AI a visible product capability for both prepaid and postpaid households: generate structured appliance schedules for user goals, then explain the verified plan. The model proposes schedules; Python remains the source of truth for energy, charges, essential-appliance rules, and whether the goal was reached.

## Runtime decision

Use the current standalone `llama.cpp` executable/server installed on the developer machine. Qwen3-0.6B Q8_0 has already passed a manual CLI smoke test. The Flask application will call the local OpenAI-compatible server over localhost (for example, `http://127.0.0.1:8080/v1`). Do not rely on the starter's old pinned `llama-cpp-python` binding. Do not check model weights into the repository.

## Implement

1. Add configuration for model API base URL, model identifier, request timeout, and maximum response size. Keep model endpoint local by default and avoid exposing local paths.
2. Add an adapter module that calls the server and normalizes the response behind a small Python interface. Keep it independent from Flask routes.
3. Ask the model for a JSON daily/weekly schedule using appliance IDs, current routines, flexibility, energy estimates, and the explicit user goal.
4. Verify model schedules against appliance limits and user-marked essential appliances. Recalculate them with the core engine. Feed a missed target back for up to three model drafts, then use a bounded calculator adjustment or report the closest safe result.
5. Add goal input for postpaid households; prepaid uses its existing desired duration. Show the generated result with goal status, before/after energy chart, schedule table, and model notes.
6. Keep concise streamed explanations available and validate their content. Never accept model-provided kWh or charges as authoritative.
7. Add timeouts and clear error states. Bill and meter calculations remain available when the model is down; AI plan generation reports that the model is unavailable.
8. Document separate local startup for the model server and Flask app.

## Components and links

- Consumes normalized cases and calculations from Phases 03–06.
- Adds goal-based planning for both service modes without changing the meaning of existing bill/meter calculations.
- Phase 08 verifies model-offline, invalid JSON, missed-target refinement, essential-appliance protection, and closest-safe-plan behavior.

## Ownership

Developer A owns adapter, prompts, API wiring, and fallback. Both developers review example explanations for factual consistency and usefulness.

## Verify and exit gate

- Local Qwen returns a structured schedule for both modes and refines a missed target.
- Numerical fields and goal status are recalculated by Python; essential appliances remain unchanged.
- The interface renders a verified schedule, chart, and table from the JSON result.
- Stop the model server: prepaid/postpaid analysis still works and plan generation reports a clear unavailable state.
- Model licence, source, role, and limitations are documented.

