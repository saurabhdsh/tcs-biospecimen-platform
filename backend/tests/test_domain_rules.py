from decimal import Decimal

import pytest

from app.core.errors import DomainError
from app.models.enums import SampleStatus
from app.models.sample import Sample
from app.services.quantity_service import convert
from app.services.state_machine import SampleStateMachine


def test_volume_conversion():
    assert convert(Decimal("1"), "mL", "uL") == Decimal("1000")
    assert convert(Decimal("500"), "uL", "mL") == Decimal("0.5")


def test_mass_conversion():
    assert convert(Decimal("1"), "g", "mg") == Decimal("1000")


def test_incompatible_units():
    with pytest.raises(DomainError) as exc:
        convert(Decimal("1"), "mL", "mg")
    assert exc.value.code == "INCOMPATIBLE_UNITS"


def test_state_machine_allows_valid_path():
    sm = SampleStateMachine()
    sample = Sample(
        sample_id="SMP-TEST",
        status=SampleStatus.RECEIVED.value,
        sample_type="Blood",
        quantity_original=1,
        quantity_remaining=1,
        quantity_unit="mL",
    )
    sm.transition(sample, SampleStatus.ACCESSIONED)
    sm.transition(sample, SampleStatus.IN_STORAGE)
    sm.transition(sample, SampleStatus.CHECKED_OUT)
    sm.transition(sample, SampleStatus.IN_STORAGE)
    sm.transition(sample, SampleStatus.QUARANTINED)
    sm.transition(sample, SampleStatus.IN_STORAGE)


def test_state_machine_rejects_invalid():
    sm = SampleStateMachine()
    sample = Sample(
        sample_id="SMP-TEST",
        status=SampleStatus.RECEIVED.value,
        sample_type="Blood",
        quantity_original=1,
        quantity_remaining=1,
        quantity_unit="mL",
    )
    with pytest.raises(DomainError) as exc:
        sm.transition(sample, SampleStatus.CHECKED_OUT)
    assert exc.value.code == "INVALID_STATUS_TRANSITION"
