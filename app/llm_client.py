"""
LLM Client for direct OpenAI API calls
"""
import json
from typing import Dict, Any, Optional, List
from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential
from app.config import config
from app.logger import logger


class LLMClient:
    """Direct OpenAI API client without LangChain"""
    
    def __init__(self):
        self.client = OpenAI(api_key=config.OPENAI_API_KEY)
        self.model = config.LLM_MODEL
        self.temperature = config.LLM_TEMPERATURE
        self.max_tokens = config.LLM_MAX_TOKENS
    
    @retry(
        stop=stop_after_attempt(config.MAX_RETRIES),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    def generate_completion(
        self, 
        messages: List[Dict[str, str]], 
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        json_mode: bool = False
    ) -> str:
        """Generate completion from OpenAI API"""
        try:
            response_format = {"type": "json_object"} if json_mode else None
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature or self.temperature,
                max_tokens=max_tokens or self.max_tokens,
                response_format=response_format
            )
            
            content = response.choices[0].message.content
            logger.debug(f"LLM Response: {content[:200]}...")
            
            return content
            
        except Exception as e:
            logger.error(f"LLM API error: {str(e)}")
            raise
    
    def generate_json_response(
        self, 
        messages: List[Dict[str, str]], 
        temperature: Optional[float] = None
    ) -> Dict[str, Any]:
        """Generate JSON response and parse it"""
        try:
            response_text = self.generate_completion(
                messages=messages,
                temperature=temperature,
                json_mode=True
            )
            
            return json.loads(response_text)
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {response_text}")
            raise ValueError(f"Invalid JSON response: {str(e)}")
    
    def generate_text_response(
        self, 
        prompt: str, 
        system_message: Optional[str] = None,
        temperature: Optional[float] = None
    ) -> str:
        """Generate text response from a prompt"""
        messages = []
        
        if system_message:
            messages.append({"role": "system", "content": system_message})
        
        messages.append({"role": "user", "content": prompt})
        
        return self.generate_completion(
            messages=messages,
            temperature=temperature
        )


# Global LLM client instance
llm_client = LLMClient()
