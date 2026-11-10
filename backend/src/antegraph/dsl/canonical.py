"""Canonical JSON and content hashing (docs/SEMANTICS.md §5).

The hash is computed over the *validated* document, so formatting, key order and
input spelling (e.g. ``"2026-01-01"`` vs a parsed date) cannot change it, while any
semantic edit does. Array order is preserved: rule order is part of a policy's
content even though it never changes behavior.
"""

import hashlib
import json
from collections.abc import Mapping, Sequence
from typing import Any

from pydantic import BaseModel

HASH_PREFIX = "sha256:"


def _check_json_value(value: Any, path: str = "") -> None:
    """Reject anything without a single canonical JSON spelling (floats, NaN, non-str keys)."""
    if value is None or isinstance(value, bool | int | str):
        return
    if isinstance(value, float):
        raise TypeError(f"floats are not allowed in canonical JSON (at {path or '/'})")
    if isinstance(value, Mapping):
        for key, item in value.items():
            if not isinstance(key, str):
                raise TypeError(f"object keys must be strings (at {path or '/'})")
            _check_json_value(item, f"{path}/{key}")
        return
    if isinstance(value, Sequence):
        for i, item in enumerate(value):
            _check_json_value(item, f"{path}/{i}")
        return
    raise TypeError(f"unsupported type {type(value).__name__} (at {path or '/'})")


def to_json_data(value: BaseModel | Any) -> Any:
    """Convert a model to plain JSON data; omitted optional fields stay omitted."""
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json", exclude_none=True)
    return value


def canonical_json(value: BaseModel | Any) -> str:
    data = to_json_data(value)
    _check_json_value(data)
    return json.dumps(
        data, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    )


def content_hash(value: BaseModel | Any) -> str:
    digest = hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()
    return HASH_PREFIX + digest
