# Phase 06 — Flask API and browser workflows

## Outcome

Connect the deterministic core to a complete, usable browser app through Flask. A user can finish both prepaid and postpaid workflows and see transparent results.

## Implement: Flask and services

1. Add application configuration, blueprints/routes, consistent JSON success/error envelopes, request-size bounds, safe error handlers, and health/readiness reporting.
2. Implement health, consumption estimate, prepaid analyze, postpaid analyze, and explanation-request routes using Phase 01 contracts.
3. Keep route handlers thin: validate/normalize, invoke services, serialize results. Do not put formulas or prompt construction in routes.
4. Analysis routes must not call the model. They return calculation results and routine options even if Qwen is not installed/running.

## Implement: HTML/CSS/JavaScript

1. Create a home screen where the user chooses Prepaid or Postpaid.
2. Build progressive, mobile-friendly forms. Ask for core values first; place optional bill details and advanced ratings behind clear expandable controls.
3. Build reusable appliance/routine cards with quantity, energy-input method, routine, preferred time, essential flag, and source/estimate labels.
4. Show loading, validation, empty, calculation, and model-unavailable states. Preserve entered form data on recoverable errors.
5. Render appliance breakdowns, budget/charge comparisons, assumptions, warnings, and alternatives from API responses. Do not calculate authoritative values in JavaScript.
6. Let users edit/select a routine and request a new calculation.

## Components and links

- Integrates Phases 02–05 into user-facing workflows.
- Becomes the caller for Phase 07's optional explanation endpoint.
- Forms the main surface exercised by Phase 08 end-to-end tests.

## Ownership

Developer A leads Flask, services, and frontend. Developer B supplies stable core contracts and reviews displayed calculations against fixture outputs.

## Verify and exit gate

- Browser can complete one prepaid and one postpaid analysis using API results.
- API tests cover valid requests, missing optional values, malformed JSON, invalid ranges, and consistent errors.
- The app remains useful if the model process is stopped.
- No unsafe HTML rendering of user or model text.

