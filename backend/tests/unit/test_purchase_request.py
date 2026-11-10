import json
from typing import Any

import pytest
from pydantic import ValidationError

from antegraph.domain.enums import Category, Role
from antegraph.domain.models import PurchaseRequest


def valid(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "id": "req-1",
        "requester_id": "emp_0042",
        "requester_roles": [],
        "department": "engineering",
        "category": "software",
        "amount_minor": 1250000,
        "currency": "USD",
        "vendor_id": "ven_0007",
        "vendor_risk": "low",
        "is_new_vendor": False,
        "requested_at": "2026-11-10T15:00:00Z",
    }
    base.update(overrides)
    return base


def parse(data: dict[str, Any]) -> PurchaseRequest:
    # Requests arrive as JSON, so validate through the JSON path (strict mode allows
    # enum strings and ISO timestamps there, but still rejects coercions like 1.0 -> 1).
    return PurchaseRequest.model_validate_json(json.dumps(data))


def error_types(data: dict[str, Any]) -> set[str]:
    with pytest.raises(ValidationError) as exc:
        parse(data)
    return {e["type"] for e in exc.value.errors()}


def test_valid_request_parses() -> None:
    req = parse(valid())
    assert req.category is Category.SOFTWARE
    assert req.amount_minor == 1250000


def test_round_trip_is_stable() -> None:
    req = parse(valid(requester_roles=["manager", "finance"]))
    again = PurchaseRequest.model_validate_json(req.model_dump_json())
    assert again == req
    assert req.model_dump(mode="json")["requested_at"] == "2026-11-10T15:00:00Z"


def test_requester_roles_are_normalized_sorted() -> None:
    req = parse(valid(requester_roles=["manager", "finance"]))
    assert req.requester_roles == [Role.FINANCE, Role.MANAGER]


@pytest.mark.parametrize("amount", [1250000.0, 1.25e6, "1250000", True])
def test_amount_must_be_integer(amount: Any) -> None:
    assert error_types(valid(amount_minor=amount)) & {"int_type", "int_from_float"}


@pytest.mark.parametrize("amount", [-1, 1_000_000_000_001])
def test_amount_bounds(amount: int) -> None:
    assert error_types(valid(amount_minor=amount)) & {"greater_than_equal", "less_than_equal"}


def test_amount_bounds_inclusive() -> None:
    assert parse(valid(amount_minor=0)).amount_minor == 0
    assert parse(valid(amount_minor=1_000_000_000_000)).amount_minor == 1_000_000_000_000


def test_missing_field_rejected() -> None:
    data = valid()
    del data["vendor_risk"]
    assert "missing" in error_types(data)


def test_null_field_rejected() -> None:
    assert error_types(valid(vendor_risk=None))


def test_extra_field_rejected() -> None:
    assert "extra_forbidden" in error_types(valid(notes="hello"))


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("category", "Software"),
        ("department", "it"),
        ("vendor_risk", "critical"),
        ("currency", "EUR"),
        ("requester_roles", ["ceo"]),
    ],
)
def test_invalid_enum_rejected(field: str, value: Any) -> None:
    assert "enum" in error_types(valid(**{field: value}))


def test_duplicate_roles_rejected() -> None:
    assert "value_error" in error_types(valid(requester_roles=["finance", "finance"]))


@pytest.mark.parametrize("flag", ["true", 1, 0])
def test_is_new_vendor_must_be_bool(flag: Any) -> None:
    assert "bool_type" in error_types(valid(is_new_vendor=flag))


@pytest.mark.parametrize("bad_id", ["", "has space", "x" * 65, "emp@corp"])
def test_identifier_pattern(bad_id: str) -> None:
    assert "string_pattern_mismatch" in error_types(valid(id=bad_id))


@pytest.mark.parametrize("ts", ["2026-11-10T15:00:00+02:00", "2026-11-10T15:00:00"])
def test_requested_at_must_be_utc(ts: str) -> None:
    assert error_types(valid(requested_at=ts))


def test_request_is_immutable() -> None:
    req = parse(valid())
    with pytest.raises(ValidationError):
        req.amount_minor = 1  # type: ignore[misc]
