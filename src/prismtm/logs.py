import logging
import os
import sys
from pathlib import Path

def setup_logging():
    """Set up logging configuration for prismtm package with environment-based levels."""
    # Determine log level from environment
    env_level = os.getenv('PRISMTM_LOG_LEVEL', '').upper()
    is_debug = os.getenv('PRISMTM_DEBUG', '').lower() in ('1', 'true', 'yes')

    # Set log level based on environment - default to WARNING for regular users
    if is_debug:
        level = logging.DEBUG
    elif env_level:
        level = getattr(logging, env_level, logging.WARNING)
    else:
        level = logging.WARNING  # Default: production mode (warnings and errors only)

    # Create logs directory if it doesn't exist
    log_dir = Path.home() / ".local" / "share" / "prismtm" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    # Standardized log format with more detail
    log_format = '[%(asctime)s] %(levelname)-8s [%(name)s:%(funcName)s:%(lineno)d] %(message)s'
    date_format = '%Y-%m-%d %H:%M:%S'

    # Configure formatters
    detailed_formatter = logging.Formatter(log_format, date_format)
    console_formatter = logging.Formatter(
        '%(levelname)-8s [%(name)s] %(message)s' if is_debug
        else '%(levelname)s: %(message)s'
    )

    # File handler (always detailed)
    file_handler = logging.FileHandler(log_dir / "prismtm.log")
    file_handler.setFormatter(detailed_formatter)
    file_handler.setLevel(logging.DEBUG)  # File gets all messages

    # Console handler (respects environment level)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(console_formatter)
    console_handler.setLevel(level)

    # Configure root logger for prismtm
    logger = logging.getLogger('prismtm')
    logger.setLevel(logging.DEBUG)  # Logger accepts all, handlers filter
    logger.handlers.clear()  # Remove any existing handlers
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    # Prevent propagation to root logger
    logger.propagate = False

    return logger

# Initialize logging when package is imported
setup_logging()

def get_logger(name: str = None):
    """Get a logger instance for a specific module."""
    if name:
        return logging.getLogger(f'prismtm.{name}')
    return logging.getLogger('prismtm')
