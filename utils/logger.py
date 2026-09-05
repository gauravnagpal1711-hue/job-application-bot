"""Shared logger setup — plain stdout logging so Railway's log viewer
captures everything without needing a file volume."""
import logging
import sys

from utils.config import Config


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger  # already configured

    logger.setLevel(Config.LOG_LEVEL)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    )
    logger.addHandler(handler)
    logger.propagate = False
    return logger
