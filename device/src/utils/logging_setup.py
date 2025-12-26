"""
Logging configuration for OPTIC-SHIELD.
Supports console and file logging with rotation.
"""

import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler
from typing import Optional

from ..core.config import Config


def setup_logging(config: Config) -> logging.Logger:
    """
    Configure logging based on configuration.
    
    Args:
        config: Application configuration
        
    Returns:
        Root logger instance
    """
    log_config = config.logging
    
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_config.level.upper(), logging.INFO))
    
    root_logger.handlers.clear()
    
    formatter = logging.Formatter(log_config.format)
    
    if log_config.console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        console_handler.setLevel(getattr(logging, log_config.level.upper(), logging.INFO))
        root_logger.addHandler(console_handler)
    
    if log_config.file:
        log_path = config.get_base_path() / log_config.file_path
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = RotatingFileHandler(
            log_path,
            maxBytes=config.storage.logs_max_size_mb * 1024 * 1024,
            backupCount=5
        )
        file_handler.setFormatter(formatter)
        file_handler.setLevel(getattr(logging, log_config.level.upper(), logging.INFO))
        root_logger.addHandler(file_handler)
    
    logging.getLogger("ultralytics").setLevel(logging.WARNING)
    logging.getLogger("PIL").setLevel(logging.WARNING)
    
    return root_logger


def get_logger(name: str) -> logging.Logger:
    """Get a logger with the specified name."""
    return logging.getLogger(name)
