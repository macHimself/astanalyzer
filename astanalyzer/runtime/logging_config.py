"""
Logging configuration for astanalyzer.

This module provides a helper function to configure application-wide logging
with a consistent format and log level. The log level can be controlled either
explicitly or via the ASTANALYZER_LOGLEVEL environment variable.
"""

import logging
import os


def setup_logging(level=None):
    """
    Configure global logging settings for the application.

    The log level can be provided explicitly or taken from the
    ASTANALYZER_LOGLEVEL environment variable (defaults to INFO).
    The function sets a consistent log format and updates all existing
    handlers to use the selected log level.

    Args:
        level (str | None): Logging level (e.g. 'DEBUG', 'INFO').
            If None, the value is read from the environment.

    Side Effects:
        - Reconfigures the root logger.
        - Overrides existing logging configuration.
        - Updates all handlers to use the selected log level.
    """
    level = level or os.getenv("ASTANALYZER_LOGLEVEL", "INFO")

    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)-7s | %(name)-16s | %(message)s",
        datefmt="%H:%M:%S",
        force=True,
    )

    root = logging.getLogger()
    root.setLevel(level)

    for h in root.handlers:
        h.setLevel(level)
