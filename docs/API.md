# WattWise API

The browser uses the Flask API under `/api`. All analysis endpoints return the same envelope:

```json
{"success": true, "data": {}, "warnings": []}
```

Validation errors use:

```json
{"success": false, "error": {"code": "VALIDATION_ERROR", "message": "...", "details": []}}
```

See [`../phases/contracts/API_CONTRACTS.md`](../phases/contracts/API_CONTRACTS.md) and the request/result fixtures for complete field semantics.

## Routes

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/health` | Flask/core readiness and local model readiness |
| POST | `/api/consumption/estimate` | Appliance energy breakdown for a period |
| POST | `/api/prepaid/analyze` | Meter credit budget, projected duration, and routine options |
| POST | `/api/postpaid/analyze` | Household estimate and supported bill comparisons |
| POST | `/api/recommendations/plan` | Generate, refine, and verify a goal-based schedule with local Qwen |
| POST | `/api/recommendations/plan/stream` | Same verified plan over server-sent events with draft/revision progress |
| POST | `/api/recommendations/explain` | Optional local model explanation of a recomputed case |
| POST | `/api/recommendations/explain/stream` | Stream an optional local model explanation as text events |
| POST | `/api/auth/register` | Create an account and set its JWT session cookie |
| POST | `/api/auth/login` | Verify credentials and set the JWT session cookie |
| POST | `/api/auth/logout` | Clear the session cookie |
| GET | `/api/auth/me` | Return the signed-in user's email |
| GET/PUT | `/api/account/appliances` | Read or save the signed-in user's appliance profile |
| GET/POST | `/api/account/history` | List or save the signed-in user's analysis history |

Account endpoints require the browser's HttpOnly JWT cookie. Registration and login accept JSON containing `email` and `password`; passwords must be 8–128 characters. The password is stored as a scrypt hash. Account records and history are stored locally in SQLite at `instance/wattwise.sqlite3` by default. The session cookie is intentionally HttpOnly and is not returned as JSON.

## Health

```http
GET /api/health
```

The response reports `app`, `calculation_engine`, and `model`. Model state is `ready` if the configured local server responds, otherwise `not_loaded`. A health request does not load the model.

## Consumption estimate

```json
{
  "period_days": 30,
  "appliances": [
    {
      "id": "fan-1",
      "label": "Bedroom fan",
      "quantity": 1,
      "essential": false,
      "energy_input": {"method": "power_and_schedule", "power_watts": 75, "source": "appliance_label", "usage_factor": 1.0},
      "routine": {"hours_per_use_day": 8, "uses_per_week": 7, "preferred_time": "night"}
    }
  ]
}
```

## Prepaid analysis

`POST /api/prepaid/analyze` requires `target_days`, `available_units_kwh`, and a non-empty `appliances` array. An optional `topup_receipt` may describe a purchase. It is not substituted for the meter balance.

The response includes daily budget, estimated daily and target use, projected duration, estimated units after the target, feasibility, appliance breakdown, and evaluated routine alternatives. A zero-use household has a `null` duration and an explanatory warning.

## Postpaid analysis

`POST /api/postpaid/analyze` requires `billing_period.days` and `appliances`. Billed units, readings, multiplier, tariff, energy charge, total due, and other charges are optional. If billed units are omitted and valid readings are supplied, consumption is derived from their difference times the multiplier.

The response separates household estimated kWh, billed kWh, energy-charge calculations, and total bill. It does not diagnose fraud.

## AI routine plan

`POST /api/recommendations/plan` accepts `mode` and the complete `case` used for the relevant analysis. Prepaid uses the existing `target_days` and `available_units_kwh` goal. Postpaid additionally requires `case.target_reduction_percent`, a user-selected reduction from 5 to 80 percent against the appliance-based estimate for the bill period.

Qwen returns a structured appliance schedule. WattWise validates appliance IDs, keeps user-marked essential appliance routines unchanged, recalculates every row, and asks Qwen to revise up to three drafts when the calculated schedule misses the goal. If necessary, a bounded calculator adjustment is applied and disclosed. If essentials alone prevent the target, the response marks the plan as `closest_safe_plan` instead of claiming success.

The response contains `data.plan` with `title`, `summary`, `service_type`, `goal`, `schedule`, energy-charge estimates where a tariff is supplied, model tips, proposal-round count, and a verification note. Each schedule row includes appliance ID, label, rating source, usual and planned hours/days, baseline and planned daily kWh, and a reason. The browser displays the JSON as goal status, comparison metrics, a before/after appliance chart, and an accessible schedule table.

This endpoint requires the local model server. It returns `503 MODEL_UNAVAILABLE` if inference is unavailable and `502 AI_PLAN_INVALID` if WattWise cannot validate the generated schedule. The deterministic prepaid/postpaid analysis endpoints remain available without the model.

## Explanation

`POST /api/recommendations/explain` accepts `mode`, the original `case`, and an optional `selected_routine_id`. The service revalidates and recomputes the case before making a local request. Only server-generated numerical facts and routine options are passed to the model. If local inference is unavailable, the endpoint returns `503 MODEL_UNAVAILABLE`; prior calculation results remain usable.

