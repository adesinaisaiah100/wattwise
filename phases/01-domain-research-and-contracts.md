# Phase 01 — Domain research and contracts

**Status:** Research checked and draft contracts prepared. Team confirmation is still needed before dependent implementation is treated as final.

## Outcome

Turn the product specification into agreed field names, calculation examples, and API contracts. Both developers use these contracts so the browser, Flask services, and calculation modules can be integrated without guessing.

## Implement

1. Review the current `SYSTEM_DESIGN.md` and record the final MVP boundary: manual data entry; both payment modes; appliances and editable routines; deterministic estimates; optional local AI explanations.
2. Collect and review representative IBEDC postpaid bill examples and prepaid vending/top-up receipts. Record the labels users may see for billed kWh, readings, tariff, energy charge, total due, units credited, deductions, and dates. Keep a clear distinction between a receipt for a purchase and current prepaid balance. Do not request/store token codes or meter/account identifiers.
3. For each candidate bill field, state whether it is required, optional, how it is entered, and what analysis is possible if it is missing. Do not treat IBEDC-only field names as universal for every Nigerian DisCo.
4. Freeze JSON shapes for appliance/routine input, prepaid analysis, postpaid analysis, routine options, common result envelope, validation errors, and model explanation requests.
5. Create at least one hand-calculated sample household for prepaid and one for postpaid, including expected kWh, comparison results, and assumptions.
6. Agree on units, numeric ranges, rounding policy, date format, tariff source labels, and terminology shown in the UI.

## Components and links

- Phase 02 builds appliance/routine entry from the shared appliance schema.
- Phase 03 implements formulas against the frozen shapes and reference examples.
- Phases 04–05 define complete mode-specific outputs using those core results.
- Phases 06–07 consume the same contracts through API/UI and AI explanation layers.

## Ownership

Shared phase. Developer A drafts request/response envelopes and UI labels. Developer B validates energy and bill fields against calculation needs. Both approve fixtures before parallel implementation.

## Verify and exit gate

- Both developers can independently explain every required and optional input.
- Sample requests and expected outputs are checked by hand.
- No field conflates prepaid units credited with units available, or total bill with energy charge.
- Contracts and example fixtures are committed before dependent modules diverge.

## Phase 1 artifacts

- [Contract rules, routes, and verified domain notes](contracts/API_CONTRACTS.md)
- [Prepaid request fixture](contracts/prepaid-request.example.json)
- [Prepaid expected calculation fixture](contracts/prepaid-result.example.json)
- [Postpaid request fixture](contracts/postpaid-request.example.json)
- [Postpaid expected calculation fixture](contracts/postpaid-result.example.json)

The official source review confirms that tariffs are shown on both bills and prepaid vending receipts, while IBEDC's postpaid bill-detail schedule identifies readings, reading dates/status, tariff, kWh used, itemized charges, arrears/credits, and total due. The MVP contract intentionally asks for only the subset needed for analysis and avoids customer/account/meter identifiers. See [NERC tariff FAQ](https://nerc.gov.ng/faq/electricity-tariffs/) and [IBEDC Customer Protection Regulations, Schedule 2](https://ibedc.com/uploads/customer/Customer_Protection_Regulations_2023.pdf).

