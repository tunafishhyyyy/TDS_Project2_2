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



# Gemini API integration
import requests

class GeminiClient:
    """Google Gemini API client for LLM orchestration"""
    def __init__(self):
        self.api_key = getattr(config, "GEMINI_API_KEY", None)
        # Use the latest Gemini model as default
        self.model = getattr(config, "GEMINI_MODEL", "gemini-1.0-pro-latest")
        # Endpoint should not include :generateContent in the format string
        self.endpoint = getattr(
            config,
            "GEMINI_ENDPOINT",
            "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        )

    def generate_json_response(self, messages: List[Dict[str, str]], temperature: Optional[float] = None) -> Dict[str, Any]:
        """Generate JSON response from Gemini API"""
        # Compose prompt from messages
        prompt = "\n".join([m["content"] for m in messages])
        url = self.endpoint.format(model=self.model)
        headers = {"Content-Type": "application/json"}
        payload = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": temperature or 0.2,
                "maxOutputTokens": 2048
            }
        }
        params = {"key": self.api_key}
        try:
            response = requests.post(url, headers=headers, params=params, json=payload, timeout=30)
            response.raise_for_status()
            data = response.json()
            # Gemini returns candidates[0]["content"]["parts"][0]["text"]
            text = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
            # Try to parse as JSON
            try:
                return json.loads(text)
            except Exception:
                logger.error(f"Gemini response not valid JSON: {text}")
                return {"steps": []}
        except Exception as e:
            logger.error(f"Gemini API error: {str(e)}")
            return {"steps": []}

# Global LLM client instances
# Hugging Face Inference API integration
import requests

class HuggingFaceClient:
    """Hugging Face Inference API client for LLM orchestration"""

    def __init__(self):
        from app.config import config
        self.api_token = getattr(config, "HF_API_TOKEN", None)
        self.model = getattr(config, "HF_MODEL", "meta-llama/Meta-Llama-3-8B-Instruct")
        self.api_url = getattr(config, "HF_API_URL", "https://api-inference.huggingface.co/models/")

    def generate_json_response(self, messages, temperature: Optional[float] = None) -> Dict[str, Any]:
        """Generate JSON response from Hugging Face Inference API"""
        # Accept either a string or a list of dicts
        if isinstance(messages, str):
            inputs = messages
        elif isinstance(messages, list):
            # Detect chat-style vs. plain text models
            is_chat_model = any(
                name in self.model.lower()
                for name in ["gpt", "llama", "mistral", "chat"]
            )
            if is_chat_model:
                # Preserve role/content structure
                inputs = [{"role": m["role"], "content": m["content"]} for m in messages]
            else:
                # Fallback to concatenated text
                inputs = "\n".join([m["content"] for m in messages])
        else:
            raise ValueError("messages must be a string or a list of dicts")

        url = f"{self.api_url}{self.model}"
        headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json"
        }
        payload = {
            "inputs": inputs,
            "parameters": {
                "temperature": temperature or 0.2,
                "max_new_tokens": 512,
                "return_full_text": False
            }
        }

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=60)
            response.raise_for_status()
            data = response.json()

            # Extract generated text from HF response
            if isinstance(data, list) and data:
                text = (
                    data[0].get("generated_text")
                    or data[0].get("text")
                    or str(data[0])
                )
            elif isinstance(data, dict):
                text = (
                    data.get("generated_text")
                    or data.get("text")
                    or str(data)
                )
            else:
                text = str(data)

            # Attempt to parse JSON output
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                logger.error(f"Hugging Face response is not valid JSON: {text}")
                return {"steps": []}

        except Exception as e:
            logger.error(f"Hugging Face API error: {str(e)}")
            return {"steps": []}

            
# Global LLM client instances
llm_client = LLMClient()
gemini_client = GeminiClient()
huggingface_client = HuggingFaceClient()
