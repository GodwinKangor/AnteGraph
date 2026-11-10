"""Shared test helpers."""

import copy
import json
from pathlib import Path
from typing import Any

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures"


def load_fixture_json(*parts: str) -> Any:
    return json.loads(FIXTURES.joinpath(*parts).read_text())


def acme_v1() -> dict[str, Any]:
    return copy.deepcopy(load_fixture_json("policies", "acme_v1.json"))
