from decimal import Decimal

from app.core.errors import DomainError
from app.models.enums import QuantityUnit

VOLUME = {QuantityUnit.ML, QuantityUnit.UL}
MASS = {QuantityUnit.MG, QuantityUnit.G}

TO_BASE = {
    QuantityUnit.UL: Decimal("1"),
    QuantityUnit.ML: Decimal("1000"),
    QuantityUnit.MG: Decimal("1"),
    QuantityUnit.G: Decimal("1000"),
}

BASE_UNIT = {
    QuantityUnit.UL: QuantityUnit.UL,
    QuantityUnit.ML: QuantityUnit.UL,
    QuantityUnit.MG: QuantityUnit.MG,
    QuantityUnit.G: QuantityUnit.MG,
}


def parse_unit(unit: str) -> QuantityUnit:
    normalized = unit.strip()
    for u in QuantityUnit:
        if u.value.lower() == normalized.lower() or u.name.lower() == normalized.lower():
            return u
    raise DomainError("INVALID_UNIT", f"Unsupported unit '{unit}'. Allowed: mL, uL, mg, g.")


def same_dimension(a: QuantityUnit, b: QuantityUnit) -> bool:
    return (a in VOLUME and b in VOLUME) or (a in MASS and b in MASS)


def to_base(quantity: Decimal, unit: QuantityUnit) -> Decimal:
    return quantity * TO_BASE[unit]


def convert(quantity: Decimal, from_unit: str, to_unit: str) -> Decimal:
    src = parse_unit(from_unit)
    dst = parse_unit(to_unit)
    if src == dst:
        return quantity
    if not same_dimension(src, dst):
        raise DomainError(
            "INCOMPATIBLE_UNITS",
            f"Cannot convert {from_unit} to {to_unit}: incompatible dimensions.",
            details={"from": from_unit, "to": to_unit},
        )
    return to_base(quantity, src) / TO_BASE[dst]


def assert_positive(quantity: Decimal, field: str = "quantity") -> None:
    if quantity <= 0:
        raise DomainError(
            "INVALID_QUANTITY",
            f"{field} must be greater than zero.",
            details={field: str(quantity)},
        )
