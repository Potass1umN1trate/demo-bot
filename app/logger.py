import logging
import sys


def setup_logger(name: str, log_level: str = "INFO") -> logging.Logger:
    """
    Set up logger with console (stdout) output only.
    Levels: DEBUG, INFO, WARNING, ERROR, CRITICAL
    """
    logger = logging.getLogger(name)
    level = getattr(logging, log_level.upper(), logging.INFO)
    logger.setLevel(level)
    
    # If this is root logger, configure it and return
    if name == "root":
        # Avoid duplicate handlers
        if logger.handlers:
            return logger

        # Console handler - output to stdout
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)

        # Formatter
        formatter = logging.Formatter(
            "[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        console_handler.setFormatter(formatter)

        logger.addHandler(console_handler)
        logger.propagate = False
        return logger
    
    # For child loggers, just set the level and propagate to root
    logger.propagate = True
    return logger
