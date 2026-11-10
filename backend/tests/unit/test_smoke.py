from typer.testing import CliRunner

from antegraph import EVALUATOR_VERSION
from antegraph.cli import app


def test_version_is_semver() -> None:
    assert len(EVALUATOR_VERSION.split(".")) == 3


def test_cli_version() -> None:
    result = CliRunner().invoke(app, ["version"])
    assert result.exit_code == 0
    assert result.stdout.strip() == EVALUATOR_VERSION
