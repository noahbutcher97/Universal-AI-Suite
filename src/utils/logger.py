import logging
import os
import sys
from logging.handlers import RotatingFileHandler

def setup_logger(name="UniversalAISuite", log_file="app.log", level=logging.INFO):
    """
    Sets up a thread-safe logger with console and file handlers.
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Prevent adding handlers multiple times
    if logger.hasHandlers():
        return logger

    # Formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # Console Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File Handler (Rotating)
    try:
        log_dir = os.path.join(os.path.expanduser("~"), ".universal_ai_suite", "logs")
        os.makedirs(log_dir, exist_ok=True)
        file_handler = RotatingFileHandler(
            os.path.join(log_dir, log_file), maxBytes=5*1024*1024, backupCount=3
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except Exception as e:
        print(f"Failed to setup file logging: {e}")

    return logger

log = setup_logger()
