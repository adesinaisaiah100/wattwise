"""Validation and orchestration for analysis endpoints."""

from __future__ import annotations

from core.postpaid_analysis import analyze_postpaid
from core.prepaid_planner import plan_prepaid
from core.validation import InputError, number, validate_appliances


def prepare_prepaid(payload: dict) -> tuple[dict, dict]:
    target_days = number(payload.get("target_days"), "target_days", minimum=1, maximum=366)
    if target_days != int(target_days):
        raise InputError("Target duration must be a whole number of days.", [{"field": "target_days", "issue": "not_integer"}])
    available = number(payload.get("available_units_kwh"), "available_units_kwh", minimum=0, maximum=1000000)
    appliances = validate_appliances(payload.get("appliances"))
    receipt = payload.get("topup_receipt") or {}
    if not isinstance(receipt, dict):
        raise InputError("Top-up receipt details must be an object.",
                         [{"field": "topup_receipt", "issue": "not_object"}])
    clean_receipt = {
        "amount_paid_ngn": number(receipt.get("amount_paid_ngn"), "topup_receipt.amount_paid_ngn", minimum=0, maximum=1000000000, required=False),
        "units_credited_kwh": number(receipt.get("units_credited_kwh"), "topup_receipt.units_credited_kwh", minimum=0, maximum=10000000, required=False),
        "rate_ngn_per_kwh": number(receipt.get("rate_ngn_per_kwh"), "topup_receipt.rate_ngn_per_kwh", minimum=0, maximum=100000, required=False),
    }
    clean_receipt = clean_receipt if any(value is not None for value in clean_receipt.values()) else None
    # A vending receipt is historical context; the plan always starts from the
    # current meter balance entered as available_units_kwh.
    result = plan_prepaid(appliances, available, target_days)
    result["topup_receipt"] = clean_receipt
    return {"target_days": target_days, "available_units_kwh": available,
            "topup_receipt": clean_receipt, "appliances": appliances}, result


def prepare_postpaid(payload: dict) -> tuple[dict, dict]:
    period = payload.get("billing_period") or {}
    if not isinstance(period, dict):
        raise InputError("Billing period must be an object.", [{"field": "billing_period", "issue": "not_object"}])
    days = number(period.get("days"), "billing_period.days", minimum=1, maximum=366)
    if days != int(days):
        raise InputError("Billing period must be a whole number of days.", [{"field": "billing_period.days", "issue": "not_integer"}])
    appliances = validate_appliances(payload.get("appliances"))
    billed = payload.get("billed_consumption") or {}
    tariff = payload.get("tariff") or {}
    bill = payload.get("bill") or {}
    if not all(isinstance(item, dict) for item in (billed, tariff, bill)):
        raise InputError("Bill, tariff, and billed consumption details must be objects.",
                         [{"field": "bill", "issue": "not_object"}])
    clean_billed = {
        "units_kwh": number(billed.get("units_kwh"), "billed_consumption.units_kwh", minimum=0, maximum=10000000, required=False),
        "previous_reading_kwh": number(billed.get("previous_reading_kwh"), "billed_consumption.previous_reading_kwh", minimum=0, maximum=100000000, required=False),
        "present_reading_kwh": number(billed.get("present_reading_kwh"), "billed_consumption.present_reading_kwh", minimum=0, maximum=100000000, required=False),
        "multiplier": number(billed.get("multiplier", 1.0), "billed_consumption.multiplier", minimum=0.000001, maximum=100000, required=False) or 1.0,
        "reading_type": billed.get("reading_type"),
    }
    clean_tariff = {
        "rate_ngn_per_kwh": number(tariff.get("rate_ngn_per_kwh"), "tariff.rate_ngn_per_kwh", minimum=0, maximum=100000, required=False),
        "disco": tariff.get("disco"),
        "band": tariff.get("band"),
    }
    clean_bill = {
        "total_amount_ngn": number(bill.get("total_amount_ngn"), "bill.total_amount_ngn", minimum=0, maximum=1000000000, required=False),
        "energy_charge_ngn": number(bill.get("energy_charge_ngn"), "bill.energy_charge_ngn", minimum=0, maximum=1000000000, required=False),
        "other_charges_ngn": number(bill.get("other_charges_ngn"), "bill.other_charges_ngn", minimum=0, maximum=1000000000, required=False),
        "arrears_or_credit_ngn": number(bill.get("arrears_or_credit_ngn"), "bill.arrears_or_credit_ngn", minimum=-1000000000, maximum=1000000000, required=False),
    }
    normalized = {"billing_period": {"days": days}, "billed_consumption": clean_billed,
                  "tariff": clean_tariff, "bill": clean_bill, "appliances": appliances}
    result = analyze_postpaid(appliances, days, clean_billed, clean_tariff, clean_bill)
    return normalized, result


def analyze_case(mode: str, case: dict) -> tuple[dict, dict]:
    if mode == "prepaid":
        return prepare_prepaid(case)
    if mode == "postpaid":
        return prepare_postpaid(case)
    raise InputError("Choose prepaid or postpaid mode.", [{"field": "mode", "issue": "invalid_choice"}])

