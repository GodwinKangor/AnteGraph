from typing import Any

import pytest

from antegraph.domain.enums import Category, VendorRisk
from antegraph.dsl.policy import Block, ConditionField, Op, RequireApproval
from antegraph.dsl.validate import Issue, PolicyValidation, to_pointer, validate_policy
from tests.helpers import FIXTURES, acme_v1


def codes(result: PolicyValidation) -> set[tuple[str, str]]:
    return {(e.code, e.pointer) for e in result.errors}


def first_rule_cond(doc: dict[str, Any]) -> dict[str, Any]:
    cond: dict[str, Any] = doc["rules"][0]["when"]["all"][0]
    return cond


# --- valid documents -------------------------------------------------------


@pytest.mark.parametrize("name", ["acme_v1.json", "acme_v2.json"])
def test_fixture_policies_are_valid(name: str) -> None:
    result = validate_policy((FIXTURES / "policies" / name).read_text())
    assert result.ok, result.errors
    assert result.warnings == ()


def test_parsed_types() -> None:
    result = validate_policy(acme_v1())
    assert result.policy is not None
    rules = {r.id: r for r in result.policy.rules}

    finance = rules["finance-software-threshold"]
    assert isinstance(finance.effect, RequireApproval)
    assert finance.effect.stage == 3
    cat, amount = finance.when.conditions
    assert (cat.field, cat.op, cat.value) == (ConditionField.CATEGORY, Op.EQ, Category.SOFTWARE)
    assert (amount.op, amount.value) == (Op.GT, 1000000)

    risk = rules["high-risk-questionnaire"].when.conditions[0]
    assert risk.value == (VendorRisk.HIGH, VendorRisk.UNKNOWN)

    assert isinstance(rules["block-prohibited-vendor"].effect, Block)


def test_always_predicate() -> None:
    doc = acme_v1()
    doc["rules"][0]["when"] = {"always": True}
    assert validate_policy(doc).ok


def test_text_and_dict_inputs_agree() -> None:
    text = (FIXTURES / "policies" / "acme_v1.json").read_text()
    assert validate_policy(text).policy == validate_policy(acme_v1()).policy


# --- negative cases: one defect -> expected (code, pointer) -----------------


def _set(path: list[Any], value: Any) -> Any:
    def mutate(doc: dict[str, Any]) -> None:
        target: Any = doc
        for key in path[:-1]:
            target = target[key]
        target[path[-1]] = value

    return mutate


def _delete(path: list[Any]) -> Any:
    def mutate(doc: dict[str, Any]) -> None:
        target: Any = doc
        for key in path[:-1]:
            target = target[key]
        del target[path[-1]]

    return mutate


COND = ["rules", 2, "when", "all", 1]  # finance-software-threshold amount condition

NEGATIVE_CASES = [
    ("float amount", _set([*COND, "value"], 1500000.0), "TYPE_ERROR", "/rules/2/when/all/1/value"),
    ("string amount", _set([*COND, "value"], "1500000"), "TYPE_ERROR", "/rules/2/when/all/1/value"),
    ("negative amount", _set([*COND, "value"], -1), "OUT_OF_RANGE", "/rules/2/when/all/1/value"),
    (
        "unknown field",
        _set([*COND, "field"], "amount_gt_minor"),
        "UNSUPPORTED_CONSTRUCT",
        "/rules/2/when/all/1/field",
    ),
    (
        "unknown op",
        _set([*COND, "op"], "between"),
        "UNSUPPORTED_CONSTRUCT",
        "/rules/2/when/all/1/op",
    ),
    (
        "op not allowed for field",
        _set([*COND, "op"], "in"),
        "UNSUPPORTED_CONSTRUCT",
        "/rules/2/when/all/1/op",
    ),
    (
        "bad category",
        _set(["rules", 2, "when", "all", 0, "value"], "saas"),
        "INVALID_ENUM",
        "/rules/2/when/all/0/value",
    ),
    (
        "in needs list",
        _set(["rules", 4, "when", "all", 0, "value"], "high"),
        "TYPE_ERROR",
        "/rules/4/when/all/0/value",
    ),
    (
        "empty in list",
        _set(["rules", 4, "when", "all", 0, "value"], []),
        "OUT_OF_RANGE",
        "/rules/4/when/all/0/value",
    ),
    (
        "duplicate in values",
        _set(["rules", 4, "when", "all", 0, "value"], ["high", "high"]),
        "SCHEMA_INVALID",
        "/rules/4/when/all/0/value",
    ),
    (
        "bool as string",
        _set(["rules", 1, "when", "all", 1, "value"], "true"),
        "TYPE_ERROR",
        "/rules/1/when/all/1/value",
    ),
    ("empty all", _set(["rules", 0, "when", "all"], []), "OUT_OF_RANGE", "/rules/0/when/all"),
    (
        "both all and always",
        _set(["rules", 0, "when", "always"], True),
        "SCHEMA_INVALID",
        "/rules/0/when",
    ),
    (
        "stage zero",
        _set(["rules", 0, "effect", "stage"], 0),
        "OUT_OF_RANGE",
        "/rules/0/effect/stage",
    ),
    (
        "unknown role",
        _set(["rules", 0, "effect", "role"], "ceo"),
        "INVALID_ENUM",
        "/rules/0/effect/role",
    ),
    (
        "unknown effect type",
        _set(["rules", 0, "effect", "type"], "notify"),
        "UNSUPPORTED_CONSTRUCT",
        "/rules/0/effect",
    ),
    (
        "missing effect type",
        _delete(["rules", 0, "effect", "type"]),
        "MISSING_FIELD",
        "/rules/0/effect",
    ),
    (
        "bad reason code",
        _set(["rules", 5, "effect", "reason_code"], "nope"),
        "SCHEMA_INVALID",
        "/rules/5/effect/reason_code",
    ),
    (
        "missing explanation",
        _delete(["rules", 0, "explanation"]),
        "MISSING_FIELD",
        "/rules/0/explanation",
    ),
    ("extra rule field", _set(["rules", 0, "notes"], "x"), "UNKNOWN_FIELD", "/rules/0/notes"),
    ("bad rule id", _set(["rules", 0, "id"], "Manager Baseline"), "SCHEMA_INVALID", "/rules/0/id"),
    ("float priority", _set(["rules", 0, "priority"], 1.5), "TYPE_ERROR", "/rules/0/priority"),
    (
        "schema version",
        _set(["schema_version"], "2.0"),
        "UNSUPPORTED_SCHEMA_VERSION",
        "/schema_version",
    ),
    ("currency", _set(["currency"], "EUR"), "INVALID_ENUM", "/currency"),
    ("no rules", _set(["rules"], []), "OUT_OF_RANGE", "/rules"),
    ("bad date", _set(["effective_date"], "next week"), "TYPE_ERROR", "/effective_date"),
]


@pytest.mark.parametrize(
    ("mutate", "code", "pointer"),
    [case[1:] for case in NEGATIVE_CASES],
    ids=[case[0] for case in NEGATIVE_CASES],
)
def test_negative_case(mutate: Any, code: str, pointer: str) -> None:
    doc = acme_v1()
    mutate(doc)
    result = validate_policy(doc)
    assert not result.ok
    assert result.policy is None
    assert (code, pointer) in codes(result), result.errors


def test_all_errors_reported_at_once() -> None:
    doc = acme_v1()
    _set([*COND, "value"], 1.5)(doc)
    _set(["rules", 0, "effect", "role"], "ceo")(doc)
    _set(["currency"], "EUR")(doc)
    assert len(validate_policy(doc).errors) == 3


def test_duplicate_rule_id() -> None:
    doc = acme_v1()
    doc["rules"][3]["id"] = "manager-baseline"
    result = validate_policy(doc)
    assert not result.ok
    assert result.errors == (
        Issue(
            "DUPLICATE_RULE_ID",
            "/rules/3/id",
            "rule id 'manager-baseline' already used by /rules/0",
        ),
    )


def test_invalid_json_text() -> None:
    result = validate_policy('{"schema_version": ')
    assert [e.code for e in result.errors] == ["SCHEMA_INVALID"]


def test_size_limit() -> None:
    doc = acme_v1()
    doc["rules"][0]["explanation"] = "x" * 70_000
    result = validate_policy(doc)
    assert [(e.code, e.pointer) for e in result.errors] == [("OUT_OF_RANGE", "")]


def test_non_finite_number_rejected() -> None:
    doc = acme_v1()
    first_rule_cond(doc)["value"] = float("nan")
    assert [e.code for e in validate_policy(doc).errors] == ["SCHEMA_INVALID"]


# --- unsatisfiable-rule warnings -------------------------------------------


@pytest.mark.parametrize(
    "conditions",
    [
        [("amount_minor", "gt", 500), ("amount_minor", "lt", 300)],
        [("amount_minor", "gt", 500), ("amount_minor", "lte", 500)],
        [("amount_minor", "eq", 100), ("amount_minor", "eq", 200)],
        [("category", "eq", "software"), ("category", "eq", "hardware")],
        [("category", "in", ["software"]), ("category", "not_in", ["software"])],
        [("is_new_vendor", "eq", True), ("is_new_vendor", "eq", False)],
    ],
)
def test_unsatisfiable_rule_warns_but_validates(conditions: list[tuple[str, str, Any]]) -> None:
    doc = acme_v1()
    doc["rules"][0]["when"] = {"all": [{"field": f, "op": o, "value": v} for f, o, v in conditions]}
    result = validate_policy(doc)
    assert result.ok
    assert [(w.code, w.pointer, w.severity) for w in result.warnings] == [
        ("UNSATISFIABLE_RULE", "/rules/0/when", "warning")
    ]


@pytest.mark.parametrize(
    "conditions",
    [
        [("amount_minor", "gt", 500), ("amount_minor", "lt", 502)],  # only 501
        [("amount_minor", "gte", 500), ("amount_minor", "lte", 500)],
        [("category", "neq", "software"), ("category", "in", ["software", "hardware"])],
    ],
)
def test_narrow_but_satisfiable_rule_has_no_warning(conditions: list[tuple[str, str, Any]]) -> None:
    doc = acme_v1()
    doc["rules"][0]["when"] = {"all": [{"field": f, "op": o, "value": v} for f, o, v in conditions]}
    assert validate_policy(doc).warnings == ()


def test_pointer_escaping() -> None:
    assert to_pointer(["a/b", "c~d", 0]) == "/a~1b/c~0d/0"
    assert (
        to_pointer(["rules", 0, "effect", "block", "reason_code"]) == "/rules/0/effect/reason_code"
    )
