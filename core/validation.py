"""Input validation shared by HTTP routes and domain services."""

from __future__ import annotations

import math


class InputError(ValueError):
    def __init__(self, message: str, details: list[dict] | None = None):
        super().__init__(message)
        self.details = details or []


def number(value, field: str, *, minimum: float | None = None,
           maximum: float | None = None, required: bool = True) -> float | None:
    if value is None:
        if required:
            raise InputError(f"{field} is required.", [{"field": field, "issue": "required"}])
        return None
    if isinstance(value, bool):
        raise InputError(f"{field} must be a number.", [{"field": field, "issue": "not_numeric"}])
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        raise InputError(f"{field} must be a number.", [{"field": field, "issue": "not_numeric"}]) from None
    if not math.isfinite(parsed):
        raise InputError(f"{field} must be finite.", [{"field": field, "issue": "not_finite"}])
    if minimum is not None and parsed < minimum:
        raise InputError(f"{field} must be at least {minimum}.", [{"field": field, "issue": "below_minimum"}])
    if maximum is not None and parsed > maximum:
        raise InputError(f"{field} must be at most {maximum}.", [{"field": field, "issue": "above_maximum"}])
    return parsed


def validate_appliances(items) -> list[dict]:
    if not isinstance(items, list) or not items:
        raise InputError("Add at least one appliance.", [{"field": "appliances", "issue": "required"}])
    if len(items) > 40:
        raise InputError("A household can include up to 40 appliances in one analysis.",
                         [{"field": "appliances", "issue": "too_many"}])
    output = []
    seen = set()
    for index, raw in enumerate(items):
        prefix = f"appliances[{index}]"
        if not isinstance(raw, dict):
            raise InputError("Each appliance must be an object.", [{"field": prefix, "issue": "not_object"}])
        appliance_id = str(raw.get("id") or f"appliance-{index + 1}")
        if appliance_id in seen:
            raise InputError("Appliance IDs must be unique.", [{"field": f"{prefix}.id", "issue": "duplicate"}])
        seen.add(appliance_id)
        label = str(raw.get("label") or raw.get("name") or "Appliance").strip()[:80]
        if not label:
            raise InputError("Enter an appliance name.", [{"field": f"{prefix}.label", "issue": "required"}])
        quantity = number(raw.get("quantity"), f"{prefix}.quantity", minimum=1, maximum=100)
        if quantity != int(quantity):
            raise InputError("Quantity must be a whole number.", [{"field": f"{prefix}.quantity", "issue": "not_integer"}])
        source = "user_entered"
        raw_energy = raw.get("energy_input")
        if isinstance(raw_energy, dict):
            energy = dict(raw_energy)
        else:
            energy = {
                "method": "power_and_schedule",
                "power_watts": raw.get("power_watts"),
                "source": raw.get("power_source", "user_entered"),
                "usage_factor": raw.get("usage_factor", 1.0),
            }
        method = energy.get("method")
        source = str(energy.get("source") or source)
        if source not in {"user_entered", "measured", "appliance_label", "catalog_estimate"}:
            raise InputError("Choose a valid appliance value source.", [{"field": f"{prefix}.energy_input.source", "issue": "invalid_choice"}])
        if method == "power_and_schedule":
            energy = {
                "method": method,
                "power_watts": number(energy.get("power_watts"), f"{prefix}.power_watts", minimum=0.01, maximum=100000),
                "source": source,
                "usage_factor": number(energy.get("usage_factor", 1.0), f"{prefix}.usage_factor", minimum=0, maximum=1),
            }
        elif method == "known_daily_energy":
            energy = {
                "method": method,
                "kwh_per_use_day": number(energy.get("kwh_per_use_day"), f"{prefix}.kwh_per_use_day", minimum=0, maximum=10000),
                "source": source,
            }
        else:
            raise InputError("Choose watts or known daily energy for each appliance.",
                             [{"field": f"{prefix}.energy_input.method", "issue": "invalid_choice"}])

        routine = raw.get("routine") or {}
        if not isinstance(routine, dict):
            raise InputError("Routine must be an object.", [{"field": f"{prefix}.routine", "issue": "not_object"}])
        hours = number(
            routine.get("hours_per_use_day"), f"{prefix}.hours_per_use_day",
            minimum=0, maximum=24, required=(method == "power_and_schedule"),
        )
        days = number(routine.get("uses_per_week"), f"{prefix}.uses_per_week", minimum=0, maximum=7)
        essential = raw.get("essential")
        if not isinstance(essential, bool):
            raise InputError("Choose whether this appliance is essential to your household.",
                             [{"field": f"{prefix}.essential", "issue": "required_boolean"}])
        output.append({
            "id": appliance_id,
            "type": str(raw.get("type") or "custom")[:40],
            "label": label,
            "category": str(raw.get("category") or "other")[:40],
            "quantity": int(quantity),
            "essential": essential,
            "energy_input": energy,
            "routine": {
                "hours_per_use_day": hours or 0.0,
                "uses_per_week": days,
                "preferred_time": str(routine.get("preferred_time") or "")[:24] or None,
            },
        })
    return output


def object_payload(payload) -> dict:
    if not isinstance(payload, dict):
        raise InputError("Request body must be a JSON object.", [{"field": "body", "issue": "not_object"}])
    return payload

