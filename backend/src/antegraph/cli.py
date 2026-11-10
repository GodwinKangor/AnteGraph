"""Command-line interface for Antegraph."""

import typer

from antegraph.version import EVALUATOR_VERSION

app = typer.Typer(help="See the consequences before they happen.", no_args_is_help=True)


@app.callback()
def main() -> None:
    """Antegraph command-line tools."""


@app.command()
def version() -> None:
    """Print the evaluator version."""
    typer.echo(EVALUATOR_VERSION)
