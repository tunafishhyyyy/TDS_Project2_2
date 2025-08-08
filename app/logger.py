"""
Logging setup and utilities
"""
import sys
import json
from typing import Any, Dict
from loguru import logger
from app.config import config


def setup_logging():
    """Setup structured logging"""
    logger.remove()
    
    # Console logging
    logger.add(
        sys.stdout,
        level=config.LOG_LEVEL.upper(),
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
               "<level>{level: <8}</level> | "
               "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
               "<level>{message}</level>",
        colorize=True
    )
    
    # File logging for production
    if config.ENV == "prod":
        logger.add(
            "logs/app.log",
            level="INFO",
            format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} - {message}",
            rotation="10 MB",
            retention="30 days"
        )


def log_step_execution(step_id: int, tool: str, params: Dict[str, Any], 
                      result: Any = None, error: str = None, 
                      verification_score: float = None):
    """Log step execution details"""
    log_data = {
        "step_id": step_id,
        "tool": tool,
        "params": params,
        "status": "success" if error is None else "failed",
    }
    
    if result is not None:
        log_data["output_preview"] = str(result)[:200] + "..." if len(str(result)) > 200 else str(result)
    
    if error:
        log_data["error"] = error
        
    if verification_score is not None:
        log_data["verification_score"] = verification_score
    
    logger.info(f"Step execution: {json.dumps(log_data, indent=2)}")


# Initialize logging
setup_logging()
