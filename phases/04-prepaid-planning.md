# Phase 04 — Prepaid planning

## Outcome

Help a prepaid customer estimate whether their current meter credit can last for a target number of days and explore routines that could bring estimated use within budget.

## Implement

1. Collect current units available in the meter and target duration in days as the required planning values.
2. Offer optional receipt details: amount paid, units credited, user-supplied tariff, deductions/fees if printed, and purchase date. Ask the user to confirm current balance; receipt units must not be substituted for current available units automatically.
3. Calculate daily unit budget, estimated daily/period use, projected duration, estimated units remaining or shortfall, and target feasibility from Phase 03 results.
4. Generate a small set of alternatives by adjusting only user-approved flexible appliances. Keep user-marked essentials unchanged by default.
5. Recalculate every alternative with the Phase 03 engine. Return each changed field, energy impact, feasibility, duration, and explicit assumptions.
6. Let the user choose or edit an option and recalculate. Avoid unsafe advice and arbitrary refrigerator shutoff schedules.

## Components and links

- Consumes the appliance/routine data from Phase 02 and calculations from Phase 03.
- Provides results to the shared API/UI in Phase 06.
- Provides candidate routine IDs and calculated facts for optional explanations in Phase 07.
- Any generated routine remains editable and is re-evaluated by Phase 03.

## Ownership

Developer B owns prepaid formulas and target feasibility. Developer A owns the guided prepaid form and result presentation in Phase 06.

## Verify and exit gate

- Tests cover budget, duration, target met/not met, units remaining/shortfall, zero estimated use, and bad inputs.
- Receipt units and current available units are shown as separate facts.
- Every alternative is numerically recalculated and no default candidate changes an essential appliance.
- Prepaid analysis returns useful results without the AI model.

