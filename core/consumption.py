"""Energy calculations. These functions do not depend on Flask or AI."""

from __future__ import annotations


def appliance_period_kwh(appliance: dict, period_days: float) -> float:
    quantity = appliance["quantity"]
    energy = appliance["energy_input"]
    routine = appliance["routine"]
    active_fraction = routine["uses_per_week"] / 7.0
    if energy["method"] == "known_daily_energy":
        daily = quantity * energy["kwh_per_use_day"] * active_fraction
    else:
        daily = (quantity * energy["power_watts"] * routine["hours_per_use_day"]
                 * active_fraction * energy["usage_factor"] / 1000.0)
    return daily * period_days


def estimate_household(appliances: list[dict], period_days: float) -> dict:
    rows = []
    total = 0.0
    for appliance in appliances:
        period = appliance_period_kwh(appliance, period_days)
        daily = period / period_days if period_days else 0.0
        total += period
        rows.append({
            "appliance_id": appliance["id"],
            "label": appliance["label"],
            "quantity": appliance["quantity"],
            "daily_kwh": daily,
            "period_kwh": period,
            "energy_source": appliance["energy_input"]["source"],
            "routine": dict(appliance["routine"]),
            "essential": appliance["essential"],
        })
    return {
        "period_days": period_days,
        "estimated_consumption_kwh": total,
        "estimated_daily_consumption_kwh": total / period_days if period_days else 0.0,
        "appliance_breakdown": rows,
    }

