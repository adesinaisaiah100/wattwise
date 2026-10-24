"""Validate model-created routines and verify them with WattWise calculations."""

from __future__ import annotations

from copy import deepcopy

from core.consumption import estimate_household
from core.tariffs import energy_charge
from core.validation import InputError, number


def create_verified_plan(*, mode: str, appliances: list[dict], analysis: dict,
                         proposal: dict, target_reduction_percent: float | None = None,
                         fit_to_goal: bool = True, proposal_rounds: int = 1) -> dict:
    """Turn an AI schedule proposal into a bounded schedule with checked results."""
    original = {item["id"]: item for item in appliances}
    requested_rows = proposal["schedule"]
    if len(requested_rows) > len(original):
        raise InputError("The AI plan included too many appliance rows.")
    by_id = {}
    for row in requested_rows:
        if not isinstance(row, dict) or row.get("appliance_id") not in original:
            raise InputError("The AI plan referenced an appliance that is not in your household.")
        appliance_id = row["appliance_id"]
        if appliance_id in by_id:
            raise InputError("The AI plan repeated an appliance.")
        by_id[appliance_id] = row

    planned = deepcopy(appliances)
    for item in planned:
        suggested = by_id.get(item["id"], {})
        current = item["routine"]
        if item["essential"]:
            continue
        hours = current["hours_per_use_day"]
        if item["energy_input"]["method"] == "power_and_schedule":
            hours = _bounded_schedule_value(
                suggested.get("hours_per_use_day") if suggested.get("hours_per_use_day") is not None else hours,
                "hours_per_use_day", 0, hours,
            )
        days = _bounded_schedule_value(
            suggested.get("uses_per_week") if suggested.get("uses_per_week") is not None else current["uses_per_week"],
            "uses_per_week", 0,
            current["uses_per_week"],
        )
        current["hours_per_use_day"] = hours
        current["uses_per_week"] = days

    period_days = (analysis.get("target_days") if mode == "prepaid"
                   else analysis.get("billing_period_days"))
    if not period_days:
        raise InputError("The plan needs a billing period to calculate its schedule.")
    baseline = estimate_household(appliances, period_days)
    baseline_rows = {row["appliance_id"]: row for row in baseline["appliance_breakdown"]}
    if mode == "prepaid":
        target_kwh = analysis["available_units_kwh"]
        goal_label = f"Make {number_text(period_days)} days from {number_text(target_kwh)} kWh"
    else:
        if target_reduction_percent is None:
            raise InputError("Choose a household energy-use reduction goal.")
        target_kwh = baseline["estimated_consumption_kwh"] * (1 - target_reduction_percent / 100)
        goal_label = f"Reduce estimated household use by {number_text(target_reduction_percent)}%"

    candidate = estimate_household(planned, period_days)
    calculator_adjusted = False
    # The model proposes the routine. If its proposal misses the target, the
    # deterministic calculator carefully reduces flexible loads and verifies it.
    attempts = 0
    while (fit_to_goal and candidate["estimated_consumption_kwh"] > target_kwh + 1e-7
           and attempts < 6000):
        flexible = [item for item in planned if not item["essential"]]
        flexible.sort(key=lambda item: _next_step_saving(item, period_days), reverse=True)
        changed = False
        for item in flexible:
            routine = item["routine"]
            if item["energy_input"]["method"] == "power_and_schedule" and routine["hours_per_use_day"] > 0:
                routine["hours_per_use_day"] = max(0, round(routine["hours_per_use_day"] - 0.5, 2))
                changed = True
                break
            if routine["uses_per_week"] > 0:
                routine["uses_per_week"] = max(0, round(routine["uses_per_week"] - 0.5, 2))
                changed = True
                break
        if not changed:
            break
        calculator_adjusted = True
        attempts += 1
        candidate = estimate_household(planned, period_days)

    achieved = candidate["estimated_consumption_kwh"] <= target_kwh + 1e-7
    cost_rate = analysis.get("tariff_rate_ngn_per_kwh")
    rows_by_id = {row["appliance_id"]: row for row in candidate["appliance_breakdown"]}
    schedule = []
    for item in planned:
        energy_row = rows_by_id[item["id"]]
        original_routine = original[item["id"]]["routine"]
        if item["essential"]:
            reason = "Kept at your usual routine because you marked this appliance essential."
        else:
            changes = []
            if item["routine"]["hours_per_use_day"] != original_routine["hours_per_use_day"]:
                changes.append(f"{number_text(original_routine['hours_per_use_day'])} to {number_text(item['routine']['hours_per_use_day'])} hours per day")
            if item["routine"]["uses_per_week"] != original_routine["uses_per_week"]:
                changes.append(f"{number_text(original_routine['uses_per_week'])} to {number_text(item['routine']['uses_per_week'])} days per week")
            reason = ("Adjusted from your usual routine: " + " and ".join(changes) + "."
                      if changes else "Kept at your usual routine in this plan.")
        schedule.append({
            "appliance_id": item["id"],
            "name": item["label"],
            "quantity": item["quantity"],
            "essential": item["essential"],
            "energy_input": item["energy_input"],
            "hours_per_use_day": item["routine"]["hours_per_use_day"],
            "uses_per_week": item["routine"]["uses_per_week"],
            "usual_hours_per_use_day": original_routine["hours_per_use_day"],
            "usual_uses_per_week": original_routine["uses_per_week"],
            "baseline_daily_kwh": baseline_rows[item["id"]]["daily_kwh"],
            "daily_kwh": energy_row["daily_kwh"],
            "period_kwh": energy_row["period_kwh"],
            "reason": reason,
        })

    if achieved:
        verified_summary = "WattWise checked this suggested routine against your goal using the appliance details you entered."
    else:
        verified_summary = "This is the closest routine WattWise could verify while keeping appliances you marked essential unchanged."
    verification = f"Qwen refined this plan over {proposal_rounds} draft(s). WattWise recalculated each appliance and checked the schedule against your goal."
    if calculator_adjusted:
        verification += " WattWise made a final bounded adjustment to meet the target safely."
    return {
        "title": "Your suggested household routine",
        "summary": verified_summary,
        "service_type": mode,
        "goal": {
            "label": goal_label,
            "target_period_kwh": target_kwh,
            "baseline_period_kwh": baseline["estimated_consumption_kwh"],
            "baseline_daily_kwh": baseline["estimated_daily_consumption_kwh"],
            "estimated_period_kwh": candidate["estimated_consumption_kwh"],
            "estimated_daily_kwh": candidate["estimated_daily_consumption_kwh"],
            "saved_period_kwh": max(0, baseline["estimated_consumption_kwh"] - candidate["estimated_consumption_kwh"]),
            "achieved": achieved,
            "status": "achieved" if achieved else "closest_safe_plan",
            "period_days": period_days,
            "target_reduction_percent": target_reduction_percent,
        },
        "baseline_energy_charge_ngn": energy_charge(baseline["estimated_consumption_kwh"], cost_rate),
        "estimated_energy_charge_ngn": energy_charge(candidate["estimated_consumption_kwh"], cost_rate),
        "estimated_charge_savings_ngn": (
            energy_charge(baseline["estimated_consumption_kwh"], cost_rate)
            - energy_charge(candidate["estimated_consumption_kwh"], cost_rate)
            if cost_rate is not None else None
        ),
        "schedule": schedule,
        "tips": [str(tip)[:240] for tip in proposal.get("tips", [])[:5]
                 if isinstance(tip, str)] if isinstance(proposal.get("tips", []), list) else [],
        "calculator_adjusted_model_proposal": calculator_adjusted,
        "model_proposal_rounds": proposal_rounds,
        "verification": verification,
    }


def _bounded_schedule_value(value, field: str, minimum: float, maximum: float) -> float:
    parsed = number(value, field, minimum=0, maximum=100000)
    # Display and editing use half-hour / half-day increments for clear routines.
    return min(maximum, max(minimum, round(round(parsed * 2) / 2, 2)))


def _next_step_saving(appliance: dict, period_days: float) -> float:
    routine = appliance["routine"]
    energy = appliance["energy_input"]
    fraction = routine["uses_per_week"] / 7
    if energy["method"] == "known_daily_energy":
        return energy["kwh_per_use_day"] * appliance["quantity"] * period_days / 7 * 0.5
    return (energy["power_watts"] * appliance["quantity"] * energy["usage_factor"]
            * period_days / 7 * 0.5 * max(fraction, 1 / 7) / 1000)


def number_text(value: float) -> str:
    return f"{value:g}"
