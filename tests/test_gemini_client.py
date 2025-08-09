import pytest
from app.llm_client import gemini_client
from dotenv import load_dotenv

GEMINI_TEST_QUERY = "Create a JSON plan to analyze sales data for Q4."

def test_gemini_generate_json_response():
    print("\n--- Testing Gemini LLM Client ---")
    load_dotenv()
    messages = [
        {"role": "system", "content": "You are an expert data analysis planner. Return only valid JSON."},
        {"role": "user", "content": GEMINI_TEST_QUERY}
    ]
    response = gemini_client.generate_json_response(messages)
    print(f"Gemini response steps: {response.get('steps')}")
    assert isinstance(response, dict)
    assert "steps" in response
    assert isinstance(response["steps"], list)
