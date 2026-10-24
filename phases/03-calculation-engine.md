# Phase 03 — Deterministic calculation engine

## Outcome

Implement a pure Python core that calculates appliance energy, household totals, and user-supplied tariff charges consistently. It is the single source of numeric truth for all workflows.

## Implement

1. Appliance energy from rated watts and schedule: quantity × watts × hours per use-day × uses-per-week / 7 × period days × usage factor / 1000.
2. Appliance energy from known kWh per use-day: quantity × kWh per use-day × uses-per-week / 7 × period days.
3. Return per-appliance and per-household daily and period totals with input source, routine, and assumptions.
4. Calculate energy charge only when a valid user-supplied NGN/kWh tariff is provided. Keep unrounded calculation precision until display/serialization policy is applied.
5. Handle zero use explicitly, reject invalid numeric values, and keep missing tariff or usage fields missing rather than treating them as zero.
6. Keep formulas in core Python functions with no Flask, browser, or model imports.

## Components and links

- Supplies the baseline calculations used by Phase 04 prepaid planning and Phase 05 postpaid analysis.
- Phase 04's scenario planner calls the same functions for every changed routine.
- Phase 06 displays server results; JavaScript must not independently duplicate these formulas.
- Phase 07 may explain the returned facts but is not a calculation dependency.

## Ownership

Developer B leads implementation and unit tests. Developer A reviews result serialization and ensures the Flask service consumes the agreed result shape without redoing arithmetic.

## Verify and exit gate

- Unit tests cover single and multiple appliances, quantity, schedule frequency, each energy input method, tariff multiplication, zero use, and invalid values.
- Hand-checked fixtures from Phase 01 match expected totals within the documented precision.
- Core tests run without loading Flask or Qwen.

