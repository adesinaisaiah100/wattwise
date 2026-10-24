"""Tariff arithmetic for user-supplied single-rate tariffs."""


def energy_charge(kwh: float, rate_ngn_per_kwh: float | None) -> float | None:
    if rate_ngn_per_kwh is None:
        return None
    return kwh * rate_ngn_per_kwh

