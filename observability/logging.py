"""Logging configuration for ARGUS."""
import logging
import sys

def setup_logging(level: str = "INFO") -> None:
    """Configure root logger for ARGUS."""
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(
        fmt="[%(asctime)s] %(levelname)s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    handler.setFormatter(formatter)
    logger.handlers = [handler]
    # Prevent propagation to avoid duplicate logs in some contexts
    logger.propagate = False