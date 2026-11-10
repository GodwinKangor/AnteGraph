import pytest

from antegraph.domain.money import format_usd


@pytest.mark.parametrize(
    ("minor", "expected"),
    [
        (0, "$0.00"),
        (1, "$0.01"),
        (1000000, "$10,000.00"),
        (1000001, "$10,000.01"),
        (1250000, "$12,500.00"),
        (1_000_000_000_000, "$10,000,000,000.00"),
    ],
)
def test_format_usd(minor: int, expected: str) -> None:
    assert format_usd(minor) == expected


@pytest.mark.parametrize("bad", [1.5, True, "100"])
def test_format_usd_rejects_non_int(bad: object) -> None:
    with pytest.raises(TypeError):
        format_usd(bad)  # type: ignore[arg-type]
