import logging
import os


def setup_logging(level=None):
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