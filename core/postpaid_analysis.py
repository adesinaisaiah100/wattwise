"""Postpaid household estimate and supported bill comparisons."""

from __future__ import annotations

from core.consumption import estimate_household
from core.scenarios import build_routine_options
from core.tariffs import energy_charge


def analyze_postpaid(appliances: list[dict], period_days: float,
                     billed_consumption: dict, tariff: dict,
                     bill: dict) -> dict:
    estimate = estimate_household(appliances, period_days)
    rate = tariff.get("rate_ngn_per_kwh")
    billed = billed_consumption.get("units_kwh")
    source = "entered" if billed is not None else None
    warnings = []
    if billed is None:
        # Preserve the source distinction: only derive kWh from readings when
        # the bill did not already provide a billed-consumption value.
        previous = billed_consumption.get("previous_reading_kwh")
        present = billed_consumption.get("present_reading_kwh")
        multiplier = billed_consumption.get("multiplier") or 1.0
        if previous is not None and present is not None:
            difference = (present - previous) * multiplier
            if difference >= 0:
                billed = difference
                source = "readings_derived"
            else:
                warnings.append("Meter readings do not produce a usable non-negative consumption value.")

    comparisons = []
    if billed is not None:
        comparisons.append({
            "kind": "estimated_minus_billed_kwh",
            "estimated_kwh": estimate["estimated_consumption_kwh"],
            "billed_kwh": billed,
            "difference_kwh": estimate["estimated_consumption_kwh"] - billed,
        })

    expected_billed_charge = energy_charge(billed, rate) if billed is not None else None
    supplied_energy_charge = bill.get("energy_charge_ngn")
    if expected_billed_charge is not None and supplied_energy_charge is not None:
        comparisons.append({
            "kind": "expected_billed_energy_charge_minus_supplied_energy_charge",
            "expected_from_billed_units_ngn": expected_billed_charge,
            "supplied_energy_charge_ngn": supplied_energy_charge,
            "difference_ngn": expected_billed_charge - supplied_energy_charge,
        })

    if billed is None:
        warnings.append("Billed kWh is unavailable, so the household estimate cannot be compared with billed consumption.")
    if rate is None:
        warnings.append("Tariff is unavailable, so energy charges cannot be estimated or reconciled.")
    if estimate["estimated_consumption_kwh"] > 0:
        options = build_routine_options(appliances, period_days, rate_ngn_per_kwh=rate)
    else:
        options = []
    return {
        "mode": "postpaid",
        "billing_period_days": period_days,
        "estimated_household_kwh": estimate["estimated_consumption_kwh"],
        "estimated_daily_kwh": estimate["estimated_daily_consumption_kwh"],
        "estimated_household_energy_charge_ngn": energy_charge(estimate["estimated_consumption_kwh"], rate),
        "billed_consumption": {
            "units_kwh": billed,
            "source": source,
            "reading_type": billed_consumption.get("reading_type"),
        },
        "expected_billed_energy_charge_ngn": expected_billed_charge,
        "comparisons": comparisons,
        "appliance_breakdown": estimate["appliance_breakdown"],
        "routine_options": options,
        "total_amount_due_ngn": bill.get("total_amount_ngn"),
        "energy_charge_ngn": supplied_energy_charge,
        "other_charges_ngn": bill.get("other_charges_ngn"),
        "assumptions": ["Household kWh is an appliance-based estimate, not a meter reading."],
        "warnings": warnings,
    }

