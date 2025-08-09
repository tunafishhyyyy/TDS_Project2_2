"""
Configuration and environment setup
"""
import os
from typing import Optional
from dotenv import load_dotenv

load_dotenv()


class Config:
    # Gemini API
    GEMINI_API_KEY: Optional[str] = os.getenv("GEMINI_API_KEY")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-pro")
    GEMINI_ENDPOINT: str = os.getenv("GEMINI_ENDPOINT", "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent")
    """Application configuration"""
    
    # API Keys
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
    SEARCH_API_KEY: Optional[str] = os.getenv("SEARCH_API_KEY")
    
    # Environment
    ENV: str = os.getenv("ENV", "dev")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "info")
    
    # Database
    DATABASE_PATH: str = os.getenv("DATABASE_PATH", "./data/database.db")
    
    # LLM Settings
    LLM_MODEL: str = os.getenv("LLM_MODEL", "gpt-4")
    LLM_TEMPERATURE: float = float(os.getenv("LLM_TEMPERATURE", "0.1"))
    LLM_MAX_TOKENS: int = int(os.getenv("LLM_MAX_TOKENS", "4000"))

    # Hugging Face Inference API
    HF_API_TOKEN: Optional[str] = os.getenv("HF_API_TOKEN")
    HF_MODEL: str = os.getenv("HF_MODEL", "openai/gpt-oss-120b")
    HF_API_URL: str = os.getenv("HF_API_URL", "https://api-inference.huggingface.co/models/")

    # Retry settings
    MAX_RETRIES: int = int(os.getenv("MAX_RETRIES", "3"))
    RETRY_DELAY: int = int(os.getenv("RETRY_DELAY", "1"))

    # Verification thresholds
    MIN_VERIFICATION_SCORE: float = float(os.getenv("MIN_VERIFICATION_SCORE", "0.7"))
    
    @classmethod
    def validate(cls):
        """Validate required configuration"""
        if not cls.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY is required")


config = Config()
