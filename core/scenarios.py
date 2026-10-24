"""Small, bounded routine alternatives calculated with the core engine."""

from __future__ import annotations

from copy import deepcopy

from core.consumption import estimate_household


def build_routine_options(appliances: list[dict], period_days: float,
                          target_daily_kwh: float | None = None,
                          rate_ngn_per_kwh: float | None = None) -> list[dict]:
    options = []
    baseline = estimate_household(appliances, period_days)
    baseline_daily = baseline["estimated_daily_consumption_kwh"]
    for factor, label in ((0.9, "A little less flexible use"),
                          (0.75, "A balanced reduction"),
                          (0.5, "A larger reduction")):
        changed = deepcopy(appliances)
        changes = []
        for appliance in changed:
            if appliance["essential"]:
                continue
            previous = appliance["routine"].copy()
            if appliance["energy_input"]["method"] == "power_and_schedule":
                new_hours = round(previous["hours_per_use_day"] * factor, 1)
                appliance["routine"]["hours_per_use_day"] = new_hours
                field = "hours_per_use_day"
                value = new_hours
            else:
                new_days = round(previous["uses_per_week"] * factor, 1)
                appliance["routine"]["uses_per_week"] = new_days
                field = "uses_per_week"
                value = new_days
            if value != previous[field]:
                changes.append({"appliance_id": appliance["id"], "field": field,
                                "from": previous[field], "to": value})
        if not changes:
            continue
        estimate = estimate_household(changed, period_days)
        daily = estimate["estimated_daily_consumption_kwh"]
        if daily >= baseline_daily:
            continue
        option = {
            "id": f"routine-{int(factor * 100)}",
            "label": label,
            "changes": changes,
            "estimated_daily_kwh": daily,
            "estimated_period_kwh": estimate["estimated_consumption_kwh"],
            "estimated_energy_charge_ngn": (
                estimate["estimated_consumption_kwh"] * rate_ngn_per_kwh
                if rate_ngn_per_kwh is not None else None
            ),
        }
        options.append(option)
    if target_daily_kwh is not None:
        options.sort(key=lambda item: (
            item["estimated_daily_kwh"] > target_daily_kwh,
            abs(item["estimated_daily_kwh"] - target_daily_kwh),
            len(item["changes"]),
        ))
    else:
        options.sort(key=lambda item: item["estimated_daily_kwh"], reverse=True)
    return options[:3]

