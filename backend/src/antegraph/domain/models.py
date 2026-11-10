"""Purchase request model (docs/SEMANTICS.md §2)."""

from datetime import datetime, timedelta
from typing import Annotated

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    StrictBool,
    StrictInt,
    field_serializer,
)

from antegraph.domain.enums import Category, Currency, Department, Role, VendorRisk
from antegraph.domain.money import MAX_AMOUNT_MINOR

Identifier = Annotated[str, Field(pattern=r"^[A-Za-z0-9_-]{1,64}$")]
AmountMinor = Annotated[StrictInt, Field(ge=0, le=MAX_AMOUNT_MINOR)]


def _require_utc(value: datetime) -> datetime:
    if value.utcoffset() != timedelta(0):
        raise ValueError("requested_at must be a UTC timestamp (offset Z)")
    return value


def _unique_roles(value: list[Role]) -> list[Role]:
    if len(set(value)) != len(value):
        raise ValueError("requester_roles must not contain duplicates")
    return sorted(value)


class PurchaseRequest(BaseModel):
    """A single purchase request. All fields are required; nothing is coerced."""

    model_config = ConfigDict(strict=True, extra="forbid", frozen=True)

    id: Identifier
    requester_id: Identifier
    requester_roles: Annotated[list[Role], AfterValidator(_unique_roles)]
    department: Department
    category: Category
    amount_minor: AmountMinor
    currency: Currency
    vendor_id: Identifier
    vendor_risk: VendorRisk
    is_new_vendor: StrictBool
    requested_at: Annotated[datetime, AfterValidator(_require_utc)]

    @field_serializer("requested_at")
    def _serialize_requested_at(self, value: datetime) -> str:
        return value.strftime("%Y-%m-%dT%H:%M:%SZ")
