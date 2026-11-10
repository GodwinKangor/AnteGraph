"""Policy validation with stable error codes and JSON pointers (docs/SEMANTICS.md §9).

``validate_policy`` never raises for bad input: it returns every problem it can
find at once, so an author can fix a draft in one pass.
"""

import json
from collections.abc import Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Literal

from pydantic import ValidationError

from antegraph.domain.enums import Category, Department, VendorRisk
from antegraph.domain.money import MAX_AMOUNT_MINOR
from antegraph.dsl.policy import (
    ConditionField,
    Op,
    Policy,
    Rule,
)

MAX_POLICY_BYTES = 64 * 1024
EFFECT_TAGS = frozenset({"require_approval", "require_evidence", "block"})

_OUR_CODES = frozenset(
    {
        "SCHEMA_INVALID",
        "TYPE_ERROR",
        "MISSING_FIELD",
        "UNKNOWN_FIELD",
        "INVALID_ENUM",
        "OUT_OF_RANGE",
        "DUPLICATE_RULE_ID",
        "UNSUPPORTED_CONSTRUCT",
        "UNSUPPORTED_SCHEMA_VERSION",
    }
)

_PYDANTIC_TO_CODE = {
    "missing": "MISSING_FIELD",
    "union_tag_not_found": "MISSING_FIELD",
    "extra_forbidden": "UNKNOWN_FIELD",
    "enum": "INVALID_ENUM",
    "union_tag_invalid": "UNSUPPORTED_CONSTRUCT",
    "json_invalid": "SCHEMA_INVALID",
    "string_pattern_mismatch": "SCHEMA_INVALID",
    "too_short": "OUT_OF_RANGE",
    "too_long": "OUT_OF_RANGE",
    "greater_than": "OUT_OF_RANGE",
    "greater_than_equal": "OUT_OF_RANGE",
    "less_than": "OUT_OF_RANGE",
    "less_than_equal": "OUT_OF_RANGE",
    "string_too_short": "OUT_OF_RANGE",
    "string_too_long": "OUT_OF_RANGE",
}


@dataclass(frozen=True)
class Issue:
    code: str
    pointer: str
    message: str
    severity: Literal["error", "warning"] = "error"


@dataclass(frozen=True)
class PolicyValidation:
    policy: Policy | None
    errors: tuple[Issue, ...] = field(default=())
    warnings: tuple[Issue, ...] = field(default=())

    @property
    def ok(self) -> bool:
        return self.policy is not None and not self.errors


def validate_policy(document: str | bytes | Any) -> PolicyValidation:
    """Validate a policy given as JSON text/bytes or as already-parsed JSON data."""
    if isinstance(document, str | bytes):
        raw = document.encode() if isinstance(document, str) else document
    else:
        try:
            raw = json.dumps(document, ensure_ascii=False, allow_nan=False).encode()
        except (TypeError, ValueError) as exc:
            return _fail(Issue("SCHEMA_INVALID", "", f"not JSON-serializable: {exc}"))

    if len(raw) > MAX_POLICY_BYTES:
        return _fail(Issue("OUT_OF_RANGE", "", f"policy exceeds {MAX_POLICY_BYTES} bytes"))

    try:
        policy = Policy.model_validate_json(raw)
    except ValidationError as exc:
        return PolicyValidation(policy=None, errors=_sorted(_from_pydantic(exc)))

    errors = _duplicate_rule_ids(policy.rules)
    warnings = [w for i, rule in enumerate(policy.rules) if (w := _unsatisfiable(i, rule))]
    return PolicyValidation(
        policy=None if errors else policy,
        errors=_sorted(errors),
        warnings=_sorted(warnings),
    )


def _fail(issue: Issue) -> PolicyValidation:
    return PolicyValidation(policy=None, errors=(issue,))


def _sorted(issues: Sequence[Issue]) -> tuple[Issue, ...]:
    return tuple(sorted(issues, key=lambda i: (i.pointer, i.code, i.message)))


def to_pointer(loc: Sequence[int | str]) -> str:
    """RFC 6901 JSON pointer from a pydantic error location."""
    parts = []
    for i, part in enumerate(loc):
        # Discriminated unions add the tag value to the location; it is not a JSON key.
        if i > 0 and loc[i - 1] == "effect" and part in EFFECT_TAGS:
            continue
        parts.append(str(part).replace("~", "~0").replace("/", "~1"))
    return "".join(f"/{p}" for p in parts)


def _code_for(error_type: str, loc: Sequence[int | str]) -> str:
    if error_type in _OUR_CODES:
        return error_type
    if error_type == "literal_error":
        if loc and loc[-1] == "schema_version":
            return "UNSUPPORTED_SCHEMA_VERSION"
        return "UNSUPPORTED_CONSTRUCT"
    if error_type in _PYDANTIC_TO_CODE:
        return _PYDANTIC_TO_CODE[error_type]
    if error_type.endswith(("_type", "_parsing")) or error_type.startswith("int_from"):
        return "TYPE_ERROR"
    return "SCHEMA_INVALID"


def _from_pydantic(exc: ValidationError) -> list[Issue]:
    issues = []
    for err in exc.errors(include_url=False):
        loc = err["loc"]
        issues.append(Issue(_code_for(err["type"], loc), to_pointer(loc), err["msg"]))
    return issues


def _duplicate_rule_ids(rules: Sequence[Rule]) -> list[Issue]:
    first_seen: dict[str, int] = {}
    issues = []
    for i, rule in enumerate(rules):
        if rule.id in first_seen:
            issues.append(
                Issue(
                    "DUPLICATE_RULE_ID",
                    f"/rules/{i}/id",
                    f"rule id {rule.id!r} already used by /rules/{first_seen[rule.id]}",
                )
            )
        else:
            first_seen[rule.id] = i
    return issues


_ENUM_DOMAINS: dict[ConditionField, frozenset[StrEnum]] = {
    ConditionField.CATEGORY: frozenset(Category),
    ConditionField.DEPARTMENT: frozenset(Department),
    ConditionField.VENDOR_RISK: frozenset(VendorRisk),
    ConditionField.IS_NEW_VENDOR: frozenset(),  # handled separately (booleans)
}


def _unsatisfiable(index: int, rule: Rule) -> Issue | None:
    """Warn when a rule's conditions can never hold together (it would never fire)."""
    lo, hi = 0, MAX_AMOUNT_MINOR
    allowed: dict[ConditionField, set[Any]] = {}
    for cond in rule.when.conditions:
        f, op, v = cond.field, cond.op, cond.value
        if f is ConditionField.AMOUNT_MINOR:
            if op is Op.GT:
                lo = max(lo, v + 1)
            elif op is Op.GTE:
                lo = max(lo, v)
            elif op is Op.LT:
                hi = min(hi, v - 1)
            elif op is Op.LTE:
                hi = min(hi, v)
            elif op is Op.EQ:
                lo, hi = max(lo, v), min(hi, v)
            continue
        domain: set[Any] = (
            {True, False} if f is ConditionField.IS_NEW_VENDOR else set(_ENUM_DOMAINS[f])
        )
        current = allowed.setdefault(f, domain)
        if op is Op.EQ:
            current &= {v}
        elif op is Op.NEQ:
            current -= {v}
        elif op is Op.IN:
            current &= set(v)
        elif op is Op.NOT_IN:
            current -= set(v)

    if lo > hi or any(not values for values in allowed.values()):
        return Issue(
            "UNSATISFIABLE_RULE",
            f"/rules/{index}/when",
            f"rule {rule.id!r} can never match: its conditions contradict each other",
            severity="warning",
        )
    return None
