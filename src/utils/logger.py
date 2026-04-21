"""
Logging utilities for the Competitive Reasoning Video Generator
"""

import sys
from pathlib import Path
from loguru import logger

_logger_configured = False


def setup_logger(
    log_level: str = "INFO",
    log_file: str = None,
    rotation: str = "10 MB",
    retention: str = "7 days"
) -> None:
    global _logger_configured
    if _logger_configured:
        return

    logger.remove()

    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level=log_level,
        colorize=True
    )

    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        logger.add(
            log_file,
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
            level=log_level,
            rotation=rotation,
            retention=retention,
            compression="zip"
        )

    _logger_configured = True
    logger.info(f"Logger initialized with level: {log_level}")


def get_logger(name: str = None):
    if not _logger_configured:
        setup_logger()
    if name:
        return logger.bind(name=name)
    return logger
