"""Policy DSL models (docs/SEMANTICS.md §3).

Policies are data, never code: every condition is checked against a closed
field -> operator -> value table, and anything outside it is rejected with
UNSUPPORTED_CONSTRUCT rather than ignored.

Models must be validated from JSON (``model_validate_json``) so that strict mode
accepts enum strings and ISO dates while still refusing coercions like 1.0 -> 1.
"""

from datetime import date
from enum import StrEnum
from typing import Annotated, Any, Literal, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictInt,
    ValidationInfo,
    field_validator,
    model_validator,
)
from pydantic_core import PydanticCustomError

from antegraph.domain.enums import (
    Category,
    Currency,
    Department,
    EvidenceType,
    Role,
    VendorRisk,
)
from antegraph.domain.money import MAX_AMOUNT_MINOR

SCHEMA_VERSION = "1.0"
MAX_RULES = 200
MAX_CONDITIONS = 10
MAX_IN_VALUES = 20


class ConditionField(StrEnum):
    AMOUNT_MINOR = "amount_minor"
    CATEGORY = "category"
    DEPARTMENT = "department"
    VENDOR_RISK = "vendor_risk"
    IS_NEW_VENDOR = "is_new_vendor"


class Op(StrEnum):
    GT = "gt"
    GTE = "gte"
    LT = "lt"
    LTE = "lte"
    EQ = "eq"
    NEQ = "neq"
    IN = "in"
    NOT_IN = "not_in"


NUMERIC_OPS = frozenset({Op.GT, Op.GTE, Op.LT, Op.LTE, Op.EQ})
ENUM_SCALAR_OPS = frozenset({Op.EQ, Op.NEQ})
ENUM_SET_OPS = frozenset({Op.IN, Op.NOT_IN})

ENUM_FIELDS: dict[ConditionField, type[StrEnum]] = {
    ConditionField.CATEGORY: Category,
    ConditionField.DEPARTMENT: Department,
    ConditionField.VENDOR_RISK: VendorRisk,
}

ALLOWED_OPS: dict[ConditionField, frozenset[Op]] = {
    ConditionField.AMOUNT_MINOR: NUMERIC_OPS,
    ConditionField.CATEGORY: ENUM_SCALAR_OPS | ENUM_SET_OPS,
    ConditionField.DEPARTMENT: ENUM_SCALAR_OPS | ENUM_SET_OPS,
    ConditionField.VENDOR_RISK: ENUM_SCALAR_OPS | ENUM_SET_OPS,
    ConditionField.IS_NEW_VENDOR: frozenset({Op.EQ}),
}

_FROZEN_STRICT = ConfigDict(strict=True, extra="forbid", frozen=True)


def _error(code: str, message: str, **ctx: Any) -> PydanticCustomError:
    return PydanticCustomError(code, message, ctx or None)


def _choices(enum: type[StrEnum]) -> str:
    return ", ".join(m.value for m in enum)


class Condition(BaseModel):
    """``field op value``; the allowed combinations are fixed (SEMANTICS §3.1)."""

    model_config = _FROZEN_STRICT

    field: ConditionField
    op: Op
    value: Any

    # "before" validators raise our own error codes, then pydantic's strict enum
    # validation still runs (plain validators break enum serialization).
    @field_validator("field", mode="before")
    @classmethod
    def _check_field(cls, raw: Any) -> Any:
        if not isinstance(raw, str):
            raise _error("TYPE_ERROR", "field must be a string")
        if raw not in ConditionField.__members__.values():
            raise _error(
                "UNSUPPORTED_CONSTRUCT",
                f"unsupported field {raw!r}; supported: {_choices(ConditionField)}",
            )
        return raw

    @field_validator("op", mode="before")
    @classmethod
    def _check_op(cls, raw: Any, info: ValidationInfo) -> Any:
        if not isinstance(raw, str):
            raise _error("TYPE_ERROR", "op must be a string")
        if raw not in Op.__members__.values():
            raise _error("UNSUPPORTED_CONSTRUCT", f"unsupported op {raw!r}")
        op = Op(raw)
        field = info.data.get("field")
        if field is not None and op not in ALLOWED_OPS[field]:
            allowed = ", ".join(sorted(ALLOWED_OPS[field]))
            raise _error(
                "UNSUPPORTED_CONSTRUCT",
                f"op {raw!r} is not supported for {field.value!r}; allowed: {allowed}",
            )
        return raw

    @field_validator("value", mode="plain")
    @classmethod
    def _check_value(cls, raw: Any, info: ValidationInfo) -> Any:
        field: ConditionField | None = info.data.get("field")
        op: Op | None = info.data.get("op")
        if field is None or op is None:
            return raw  # the field/op error is already reported

        if field is ConditionField.AMOUNT_MINOR:
            if isinstance(raw, bool) or not isinstance(raw, int):
                raise _error("TYPE_ERROR", "amount values must be integer minor units (cents)")
            if not 0 <= raw <= MAX_AMOUNT_MINOR:
                raise _error("OUT_OF_RANGE", f"amount must be between 0 and {MAX_AMOUNT_MINOR}")
            return raw

        if field is ConditionField.IS_NEW_VENDOR:
            if not isinstance(raw, bool):
                raise _error("TYPE_ERROR", "is_new_vendor value must be a boolean")
            return raw

        enum = ENUM_FIELDS[field]
        if op in ENUM_SCALAR_OPS:
            return _enum_value(enum, raw, field)

        if not isinstance(raw, list):
            raise _error("TYPE_ERROR", f"op {op.value!r} requires a list of values")
        if not 1 <= len(raw) <= MAX_IN_VALUES:
            raise _error("OUT_OF_RANGE", f"list must contain 1 to {MAX_IN_VALUES} values")
        values = tuple(_enum_value(enum, item, field) for item in raw)
        if len(set(values)) != len(values):
            raise _error("SCHEMA_INVALID", "list values must be distinct")
        return values


def _enum_value(enum: type[StrEnum], raw: Any, field: ConditionField) -> StrEnum:
    if not isinstance(raw, str):
        raise _error("TYPE_ERROR", f"{field.value} values must be strings")
    if raw not in enum.__members__.values():
        raise _error(
            "INVALID_ENUM",
            f"{raw!r} is not a valid {field.value}; expected one of: {_choices(enum)}",
        )
    return enum(raw)


class Predicate(BaseModel):
    """Either ``{"all": [conditions]}`` (conjunction) or ``{"always": true}``."""

    model_config = _FROZEN_STRICT

    all: Annotated[list[Condition], Field(min_length=1, max_length=MAX_CONDITIONS)] | None = None
    always: Literal[True] | None = None

    @model_validator(mode="after")
    def _exactly_one(self) -> Self:
        if (self.all is None) == (self.always is None):
            raise _error("SCHEMA_INVALID", 'predicate must have exactly one of "all" or "always"')
        return self

    @property
    def conditions(self) -> list[Condition]:
        return self.all or []


class RequireApproval(BaseModel):
    model_config = _FROZEN_STRICT

    type: Literal["require_approval"]
    role: Role
    stage: Annotated[StrictInt, Field(ge=1, le=9)]


class RequireEvidence(BaseModel):
    model_config = _FROZEN_STRICT

    type: Literal["require_evidence"]
    evidence: EvidenceType


class Block(BaseModel):
    model_config = _FROZEN_STRICT

    type: Literal["block"]
    reason_code: Annotated[str, Field(pattern=r"^[A-Z][A-Z0-9_]{2,63}$")]


Effect = Annotated[RequireApproval | RequireEvidence | Block, Field(discriminator="type")]

RuleId = Annotated[str, Field(pattern=r"^[a-z0-9][a-z0-9-]{2,63}$")]


class Rule(BaseModel):
    model_config = _FROZEN_STRICT

    id: RuleId
    priority: Annotated[StrictInt, Field(ge=0, le=10_000)]
    when: Predicate
    effect: Effect
    explanation: Annotated[str, Field(min_length=1, max_length=500)]


class Policy(BaseModel):
    """A complete policy document. Immutable once validated."""

    model_config = _FROZEN_STRICT

    schema_version: Literal["1.0"]
    policy_id: RuleId
    version: Annotated[str, Field(pattern=r"^[A-Za-z0-9._-]{1,32}$")]
    currency: Currency
    effective_date: date | None = None
    rules: Annotated[list[Rule], Field(min_length=1, max_length=MAX_RULES)]
