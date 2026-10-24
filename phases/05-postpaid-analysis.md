# Phase 05 — Postpaid bill analysis

## Outcome

Estimate household use from appliances and routines, compare it with postpaid billing figures when available, and explain what can and cannot be inferred from the supplied bill.

## Implement

1. Collect billing-period days and the appliance/routine inputs required for a household-use estimate.
2. Offer optional bill details progressively: billed kWh; previous/current readings, dates, multiplier and actual/estimated reading type; tariff/band/DisCo context; energy charge; total amount due; other itemized charges; arrears/credits.
3. Derive billed kWh from readings only when reading values and multiplier are usable: (present − previous) × multiplier. Preserve whether a reading is estimated.
4. Compare household-estimated kWh with supplied/derived billed kWh only when both exist. Separately check billed kWh × user-supplied tariff against energy charge when possible.
5. Keep total amount due separate from energy charge. Do not compare total due directly with energy-only estimates unless other charges and arrears/credits are accounted for.
6. Present missing data, assumptions, and discrepancy caveats. A household estimate can flag a difference to investigate; it cannot prove overbilling or fraud.
7. Offer alternative routines using Phase 04's shared scenario approach where appropriate.

## Components and links

- Consumes Phase 02 appliance/routine input and Phase 03 calculations.
- Exposes a structured analysis result to Phase 06.
- Supplies trusted bill facts, comparison results, caveats, and approved routine options to Phase 07.

## Ownership

Developer B owns reading derivation and reconciliation logic. Developer A owns bill-entry UX and communicates which fields are optional and what a missing field prevents the app from checking.

## Verify and exit gate

- Tests cover directly entered billed kWh, derived kWh, estimated-reading label, missing tariff/charges, extra bill components, and invalid readings.
- The interface never labels an estimate as a meter reading or an arithmetic difference as proof of overbilling.
- A user can still get a household estimate when optional bill values are unavailable.

