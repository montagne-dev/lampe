from __future__ import annotations

import logging

import typer

from lampe.cli.commands.describe import describe
from lampe.cli.commands.healthcheck import healthcheck
from lampe.core.loggingconfig import LAMPE_LOGGER_NAME

logger = logging.getLogger(name=LAMPE_LOGGER_NAME)

app = typer.Typer(help="Lampe CLI")


@app.command()
def version() -> None:
    """Show version information."""
    import importlib.metadata

    version = importlib.metadata.version("lampe-cli")
    logger.info(f"🔦 Lampe CLI v{version}")
    logger.info("   Put some light on your codebase! ✨")


def main():
    app.command("describe")(describe)
    app.command("healthcheck")(healthcheck)
    app()


if __name__ == "__main__":
    main()
