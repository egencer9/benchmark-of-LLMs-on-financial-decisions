import sys
from loguru import logger

def setup_logger():
    """
    Configures the logger for the application.
    """
    logger.remove() # Remove default handler
    logger.add(
        sys.stderr,
        level="INFO",
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
    )
    logger.add(
        "logs/app_{time}.log",
        level="DEBUG",
        rotation="10 MB", # New file every 10 MB
        retention="10 days", # Keep logs for 10 days
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}"
    )
    return logger

# Create a logger instance to be imported by other modules
log = setup_logger()
