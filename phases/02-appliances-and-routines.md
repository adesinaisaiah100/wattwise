# Phase 02 — Appliance and routine model

## Outcome

Let users describe household appliances and their usual routines with enough detail for useful energy estimates, without making the form intimidating.

## Implement

1. Support appliance type/name, quantity, whether the household considers it essential, energy input, and routine.
2. Energy input supports user-entered rated watts, known kWh per use-day, or an optional catalogue estimate. Each value carries its source and is visibly marked as measured, user-entered, appliance-label, or estimated.
3. Routine input supports hours per use-day, uses per week, and an optional preferred time of day. Keep preferred time as a human-facing preference; it does not alter kWh arithmetic by itself.
4. Include common categories such as lighting, cooling, refrigeration, cooking, entertainment, pumping, laundry, and other. Allow custom appliance names.
5. Provide an “Add appliance” interaction and a small set of optional example presets. Let users edit or remove every entry. Do not silently assign default appliance ratings or assume essential status.
6. For cycling appliances such as refrigerators, allow known kWh/day or mark watts-times-hours as a rough estimate and expose any adjustment assumption.
7. Bound quantity, power, hours, and days-per-week; reject non-finite and negative values.

## Components and links

- Defines the input consumed by the Phase 03 energy engine.
- Powers the baseline and editable alternatives in Phases 04–05.
- Phase 06 renders the appliance cards and progressive details.
- Phase 07 receives these values only as trusted, server-generated context; it cannot alter them.

## Ownership

Developer B owns the canonical appliance/routine schema and validation bounds. Developer A can build the form against Phase 01 fixtures while the backend schema is finalized.

## Verify and exit gate

- A household can represent multiple appliances with different quantities and routines.
- User values remain distinguishable from catalogue estimates.
- Essential status is selected by the user and survives edits/submission.
- Invalid inputs produce actionable field errors; no calculation or AI is required for this phase.

