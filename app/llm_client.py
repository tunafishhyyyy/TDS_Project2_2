"""
LLM Client for direct OpenAI API calls
"""
import json
import re
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
            # Enable JSON mode if requested
            response_format = {"type": "json_object"} if json_mode else None
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature or self.temperature,
                max_tokens=max_tokens or self.max_tokens,
                response_format=response_format  # Pass response format
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
                json_mode=False  # Disable JSON mode for better compatibility
            )
            
            # Clean and parse the JSON response
            cleaned_text = self._clean_json_response(response_text)
            return json.loads(cleaned_text)
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {response_text}")
            logger.error(f"Cleaned text was: {cleaned_text}")
            # Return a default structure to prevent complete failure
            return self._get_fallback_response(response_text)
    
    def _clean_json_response(self, response_text: str) -> str:
        """Clean the response text to extract valid JSON"""
        cleaned = response_text.strip()
        
        # Remove markdown code blocks
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        elif cleaned.startswith("```"):
            cleaned = cleaned[3:]
        
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        
        cleaned = cleaned.strip()
        
        # If response starts with a property but no opening brace, add braces
        if cleaned.startswith('"') and not cleaned.startswith('{'):
            cleaned = '{' + cleaned + '}'
        
        # Try to find JSON content within the response
        import re
        
        # Look for the main JSON structure - more comprehensive patterns
        patterns = [
            r'\{(?:[^{}]|{[^{}]*})*\}',  # Simple nested braces
            r'\{.*?\}(?=\s*$)',          # JSON to end of string
            r'\{[\s\S]*\}',              # Any content between braces
            r'(\{[\s\S]*\})',            # Capture group for full JSON
        ]
        
        for pattern in patterns:
            json_match = re.search(pattern, cleaned, re.DOTALL | re.MULTILINE)
            if json_match:
                candidate = json_match.group(0)
                # Test if it's valid JSON
                try:
                    json.loads(candidate)
                    cleaned = candidate
                    break
                except (json.JSONDecodeError, Exception):
                    continue
        
        return cleaned
    
    def _get_fallback_response(self, original_response: str) -> Dict[str, Any]:
        """Generate a fallback response when JSON parsing fails"""
        logger.warning(f"Using fallback response due to JSON parsing failure")
        
        # Try to extract meaningful information from the response
        if "score" in original_response.lower():
            # For verification responses
            return {
                "score": 0.5,
                "confidence": 0.5,
                "issues": ["JSON parsing failed, using fallback"],
                "passed": False
            }
        elif "steps" in original_response.lower():
            # For planning responses
            return {
                "steps": []
            }
        else:
            # Generic fallback
            return {"error": "JSON parsing failed", "raw_response": original_response}
    
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
