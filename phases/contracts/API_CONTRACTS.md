# WattWise API contracts — Phase 1 draft

**Status:** Drafted from `SYSTEM_DESIGN.md` and reviewed against official NERC/IBEDC sources. Ready for teammate review before implementation. These contracts describe the MVP, not a production billing integration.

## 1. Domain findings used by the contract

- Prepaid customers pay in advance and receive credit/units on the meter; the planning input must be the **units currently available**, not just the units on the last purchase receipt.
- A prepaid vending receipt can provide the amount paid, units indicated, and tariff context. NERC says the tariff is indicated on electricity bills and prepaid vending receipts. Its FAQ says a user can derive a rate from the amount vended and indicated kWh after deducting VAT. WattWise must not infer a tariff from a gross amount when VAT or other deductions are unknown; ask for the printed/user-confirmed rate or enough confirmed receipt details.
- IBEDC Schedule 2 lists postpaid bill details including bill period, applicable tariff(s), multiplier when used, previous/present meter readings and dates, actual/estimated reading indicators, kWh used, value of energy, separate charges, arrears/credits, and total current bill. The MVP should request relevant analysis fields progressively and should not ask for name, address, account number, or meter number.
- Band and tariff are user-supplied context. WattWise does not look up a current rate or assume one tariff applies to every bill.
- A household appliance estimate is not a meter reading and cannot prove overbilling.

Sources: [NERC electricity tariff FAQ](https://nerc.gov.ng/faq/electricity-tariffs/), [NERC Metering Code, March 2026](https://nerc.gov.ng/wp-content/uploads/2026/04/Metering-Code_3rd-Edition.pdf), [IBEDC Customer Protection Regulations 2023, Schedule 2](https://ibedc.com/uploads/customer/Customer_Protection_Regulations_2023.pdf). The receipt fields in the example are representative user-entered context; vending-provider receipt layouts may differ.

## 2. Shared contract rules

- JSON uses numbers for numeric values and ISO dates (`YYYY-MM-DD`) when a date is provided.
- Energy is kWh, power is watts, duration is days/hours, and money is NGN.
- Do not round intermediate energy or money calculations. Round for display only; the API may return a documented precision.
- Missing/unknown is `null` or omitted according to the field. It is not zero.
- Input provenance is one of `user_entered`, `measured`, `appliance_label`, or `catalog_estimate` where relevant.
- `essential` is explicitly selected by the user; no appliance is assumed essential or flexible by default.
- No customer identity, meter/account number, address, or prepaid token is needed for an analysis request.
- A `success` envelope is used for ordinary application responses. Validation errors use a stable code and field details.

Success envelope:

```json
{"success": true, "data": {}, "warnings": []}
```

Error envelope:

```json
{"success": false, "error": {"code": "VALIDATION_ERROR", "message": "Check the highlighted fields.", "details": []}}
```

## 3. Appliance and routine object

An analysis request includes an `appliances` array. Each item has a request-local `id`, display `label`, optional `category`, positive `quantity`, user-selected `essential`, one `energy_input` method, and a `routine`.

Supported energy input variants:

- `{"method":"power_and_schedule","power_watts":75,"source":"user_entered","usage_factor":1.0}`
- `{"method":"known_daily_energy","kwh_per_use_day":1.2,"source":"measured"}`

Routine shape:

```json
{"hours_per_use_day": 8, "uses_per_week": 7, "preferred_time": "night"}
```

`preferred_time` is an optional planning preference and does not change energy arithmetic. Values for `hours_per_use_day` must be in 0–24; `uses_per_week` in 0–7. For cycling appliances such as refrigerators, prefer measured kWh/day when known; otherwise the estimate and limitation must be visible.

## 4. Prepaid request and result

Request requires `target_days`, `available_units_kwh`, and `appliances`. Optional `topup_receipt` is context about a purchase: `amount_paid_ngn`, `units_credited_kwh`, `rate_ngn_per_kwh`, `vat_ngn`, known deductions/fees, and `transaction_date`. Receipt units are not automatically the current balance; the user confirms the available units separately.

`POST /api/prepaid/analyze` returns at least:

- `available_units_kwh`, `target_days`, and `daily_budget_kwh`;
- baseline `estimated_daily_consumption_kwh` and `estimated_target_consumption_kwh`;
- `projected_duration_days`, `units_after_target_kwh`, and `target_met`;
- appliance breakdown, assumptions, warnings, and calculated `routine_options`.

If daily consumption is zero, `projected_duration_days` is `null` with a `no_estimated_use` warning. The UI presents “no estimated use” rather than infinity. A feasible target is based on estimated use and is explicitly labelled an estimate.

See [prepaid request](prepaid-request.example.json) and [prepaid expected result](prepaid-result.example.json). The fixture uses 60 kWh available, 14 days, and an example household consuming 2.1 kWh/day: budget is 60/14 = 4.285714 kWh/day; target use is 29.4 kWh; remaining is 30.6 kWh; projected duration is 60/2.1 = 28.571429 days.

## 5. Postpaid request and result

Request requires `billing_period.days` and `appliances`. Optional bill details include directly supplied billed kWh or usable previous/current readings and multiplier, reading type, user-supplied tariff, energy charge, total amount due, other charges, and arrears/credits.

`POST /api/postpaid/analyze` returns at least:

- household appliance-estimated kWh and daily average;
- billed kWh and its source (`entered` or `readings_derived`) when available;
- comparison `estimated_minus_billed_kwh` when both values exist;
- estimated household energy charge when tariff exists;
- expected billed energy charge (`billed_kwh × tariff`) and comparison with supplied **energy charge** when supported;
- missing fields, reading type, assumptions, warnings, and optional calculated routine options.

Never compare the total amount due directly with energy-only cost. Derived readings use `(present_reading_kwh - previous_reading_kwh) × multiplier`. Negative/invalid reading differences are rejected or reported as unusable; they are not converted to positive consumption.

See [postpaid request](postpaid-request.example.json) and [postpaid expected result](postpaid-result.example.json). Its fixture household estimate is 63 kWh, while the bill shows 100 kWh; `estimated_minus_billed_kwh` is -37 kWh. At NGN 100/kWh, expected energy charge is NGN 10,000, matching the supplied energy charge. The total bill is NGN 12,500 and remains a separate figure.

## 6. Routes and status behavior

| Method and path | Purpose | Calls model? |
|---|---|---:|
| `GET /api/health` | Application, core, and model readiness | No |
| `POST /api/consumption/estimate` | Appliance estimate and breakdown | No |
| `POST /api/prepaid/analyze` | Prepaid budget/duration and routines | No |
| `POST /api/postpaid/analyze` | Household estimate and bill comparisons | No |
| `POST /api/recommendations/plan` | Generate and verify a goal-based schedule for either service mode | Yes, required for plan |
| `POST /api/recommendations/explain` | Explain a recomputed case and approved options | Yes, optional |

- 200: analysis succeeded.
- 400: malformed JSON.
- 404: unknown path.
- 413: request too large.
- 422: valid JSON with missing/invalid fields.
- 503: explanation requested while the local model is unavailable.
- 502: generated plan is invalid and cannot be safely displayed.
- 504: explanation timed out.
- 500: unexpected failure with a generic user-safe message.

## 7. Phase 1 agreement checklist

- [ ] Both developers approve appliance and routine field names.
- [ ] Both developers approve prepaid receipt versus current-balance distinction.
- [ ] Both developers approve optional postpaid fields and comparison semantics.
- [ ] Both developers verify the sample arithmetic by hand.
- [ ] Both developers agree on response precision/display rounding and error details.

