import logging
import sys
import os
from logging.handlers import RotatingFileHandler

def setup_logger(name: str, log_file: str = "pulse_pipeline.log", level=logging.INFO):
    """
    Sets up a logger with both console and rotating file handlers.
    """
    os.makedirs('logs', exist_ok=True)
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
    )

    # Console Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)

    # File Handler (Rotating)
    file_handler = RotatingFileHandler(
        os.path.join('logs', log_file), 
        maxBytes=10*1024*1024, 
        backupCount=5
    )
    file_handler.setFormatter(formatter)

    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Avoid duplicate handlers if setup_logger is called multiple times
    if not logger.handlers:
        logger.addHandler(console_handler)
        logger.addHandler(file_handler)
    
    return logger

# Default logger instance
logger = setup_logger("pulse_report")
