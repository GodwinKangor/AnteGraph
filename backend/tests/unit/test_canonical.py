import json
import random
import re
from typing import Any

import pytest
from hypothesis import given
from hypothesis import strategies as st

from antegraph.domain.models import PurchaseRequest
from antegraph.dsl.canonical import canonical_json, content_hash
from antegraph.dsl.policy import Policy
from antegraph.dsl.validate import validate_policy
from tests.helpers import FIXTURES, acme_v1

HASH_RE = re.compile(r"^sha256:[0-9a-f]{64}$")

json_scalars = st.none() | st.booleans() | st.integers() | st.text(max_size=20)
json_values = st.recursive(
    json_scalars,
    lambda children: (
        st.lists(children, max_size=5) | st.dictionaries(st.text(max_size=10), children, max_size=5)
    ),
    max_leaves=30,
)


def policy_from(doc: Any) -> Policy:
    result = validate_policy(doc)
    assert result.policy is not None, result.errors
    return result.policy


def shuffled_keys(value: Any, rng: random.Random) -> Any:
    if isinstance(value, dict):
        items = list(value.items())
        rng.shuffle(items)
        return {k: shuffled_keys(v, rng) for k, v in items}
    if isinstance(value, list):
        return [shuffled_keys(v, rng) for v in value]
    return value


def test_canonical_form_is_compact_and_sorted() -> None:
    assert canonical_json({"b": 1, "a": [True, None, "é"]}) == '{"a":[true,null,"é"],"b":1}'


def test_hash_format() -> None:
    assert HASH_RE.match(content_hash({"a": 1}))


@given(json_values, st.integers(min_value=0, max_value=2**32))
def test_hash_ignores_key_order_and_whitespace(value: Any, seed: int) -> None:
    reformatted = json.loads(json.dumps(shuffled_keys(value, random.Random(seed)), indent=2))
    assert content_hash(reformatted) == content_hash(value)


@given(json_values)
def test_canonical_json_round_trips(value: Any) -> None:
    assert json.loads(canonical_json(value)) == value


@pytest.mark.parametrize("bad", [1.0, {"a": float("nan")}, [1, 2.5], {1: "x"}, {"a": object()}])
def test_rejects_non_canonical_values(bad: Any) -> None:
    with pytest.raises(TypeError):
        canonical_json(bad)


def test_policy_hash_ignores_formatting() -> None:
    text = (FIXTURES / "policies" / "acme_v1.json").read_text()
    compact = json.dumps(json.loads(text), separators=(",", ":"))
    rng = random.Random(7)
    shuffled = json.dumps(shuffled_keys(json.loads(text), rng), indent=4)
    hashes = {content_hash(policy_from(t)) for t in (text, compact, shuffled)}
    assert len(hashes) == 1


def test_absent_and_null_optional_fields_hash_the_same() -> None:
    with_null = acme_v1()
    with_null["effective_date"] = None
    without = acme_v1()
    del without["effective_date"]
    assert content_hash(policy_from(with_null)) == content_hash(policy_from(without))


def test_v1_and_v2_hash_differently() -> None:
    v1 = policy_from((FIXTURES / "policies" / "acme_v1.json").read_text())
    v2 = policy_from((FIXTURES / "policies" / "acme_v2.json").read_text())
    assert content_hash(v1) != content_hash(v2)


@pytest.mark.parametrize(
    "path",
    [
        ["rules", 2, "when", "all", 1, "value"],  # threshold
        ["rules", 0, "effect", "stage"],
        ["rules", 0, "priority"],
    ],
)
def test_any_semantic_edit_changes_hash(path: list[Any]) -> None:
    doc = acme_v1()
    original = content_hash(policy_from(doc))
    target: Any = doc
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] += 1
    assert content_hash(policy_from(doc)) != original


def test_rule_order_is_content() -> None:
    doc = acme_v1()
    original = content_hash(policy_from(doc))
    doc["rules"].reverse()
    assert content_hash(policy_from(doc)) != original


def test_request_hash_is_stable() -> None:
    data = {
        "id": "req-1",
        "requester_id": "emp_0042",
        "requester_roles": ["manager", "finance"],
        "department": "engineering",
        "category": "software",
        "amount_minor": 1250000,
        "currency": "USD",
        "vendor_id": "ven_0007",
        "vendor_risk": "low",
        "is_new_vendor": False,
        "requested_at": "2026-11-10T15:00:00Z",
    }
    a = PurchaseRequest.model_validate_json(json.dumps(data))
    data["requester_roles"] = ["finance", "manager"]  # same set, different order
    b = PurchaseRequest.model_validate_json(json.dumps(data, indent=2))
    assert content_hash(a) == content_hash(b)
