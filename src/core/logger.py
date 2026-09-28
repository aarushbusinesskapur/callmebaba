import logging
import sys
import os

def setup_logger(name: str = "quant_system", level: str = "INFO") -> logging.Logger:
    """Sets up a structured logger for the quantitative system."""
    logger = logging.getLogger(name)
    
    if not logger.handlers:
        numeric_level = getattr(logging, level.upper(), logging.INFO)
        logger.setLevel(numeric_level)
        
        # Console handler
        ch = logging.StreamHandler(sys.stdout)
        ch.setLevel(numeric_level)
        
        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        ch.setFormatter(formatter)
        logger.addHandler(ch)
        
    return logger

logger = setup_logger(level=os.getenv("LOG_LEVEL", "INFO"))
