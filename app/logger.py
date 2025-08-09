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
    # Always add execution and llm logs with filters
    logger.add(
        "logs/execution.log",
        level="INFO",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
        rotation="10 MB",
        retention="30 days",
        filter=lambda record: record["extra"].get("log_type") == "execution"
    )
    logger.add(
        "logs/llm.log",
        level="INFO",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
        rotation="10 MB",
        retention="30 days",
        filter=lambda record: record["extra"].get("log_type") == "llm"
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



# Additional loggers for execution and LLM queries
from loguru import logger as loguru_logger

loguru_logger.add("logs/execution.log", level="INFO", format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}", rotation="10 MB", retention="30 days")
loguru_logger.add("logs/llm.log", level="INFO", format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}", rotation="10 MB", retention="30 days")

setup_logging()

def execution_logger_info(step_id, tool, status, error=None):
    msg = f"EXE step_id={step_id} tool={tool} status={status}"
    if error:
        msg += f" error={error}"
    msg = msg.replace('\n', ' ').replace('\r', ' ')
    logger.bind(log_type="execution").info(msg)

def llm_logger_info(question, answer):
    q = str(question).replace('\n', ' ').replace('\r', ' ')
    if len(q) > 120:
        q = q[:120] + '...'
    a = str(answer).replace('\n', ' ').replace('\r', ' ')
    if len(a) > 200:
        a = a[:200] + '...'
    logger.bind(log_type="llm").info(f"LLM QUESTION: {q}")
    logger.bind(log_type="llm").info(f"LLM ANSWER: {a}")
