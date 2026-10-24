"""Prepaid unit budgeting and target feasibility."""

from __future__ import annotations

from core.consumption import estimate_household
from core.scenarios import build_routine_options


def plan_prepaid(appliances: list[dict], available_units_kwh: float,
                 target_days: float) -> dict:
    baseline = estimate_household(appliances, target_days)
    daily = baseline["estimated_daily_consumption_kwh"]
    target_use = baseline["estimated_consumption_kwh"]
    options = build_routine_options(
        appliances, target_days,
        target_daily_kwh=available_units_kwh / target_days,
    )
    for option in options:
        option["projected_duration_days"] = (
            available_units_kwh / option["estimated_daily_kwh"]
            if option["estimated_daily_kwh"] > 0 else None
        )
        option["units_after_target_kwh"] = available_units_kwh - option["estimated_period_kwh"]
        option["target_met"] = option["units_after_target_kwh"] >= -1e-9
    return {
        "mode": "prepaid",
        "target_days": target_days,
        "available_units_kwh": available_units_kwh,
        "daily_budget_kwh": available_units_kwh / target_days,
        "estimated_daily_consumption_kwh": daily,
        "estimated_target_consumption_kwh": target_use,
        "projected_duration_days": available_units_kwh / daily if daily > 0 else None,
        "units_after_target_kwh": available_units_kwh - target_use,
        "target_met": target_use <= available_units_kwh,
        "appliance_breakdown": baseline["appliance_breakdown"],
        "routine_options": options,
        "assumptions": ["Usage is estimated from the supplied appliance ratings and weekly routines."],
        "warnings": (["No estimated use; projected duration cannot be calculated."] if daily == 0 else []),
    }

