import pytest
from app.llm_client import huggingface_client
from dotenv import load_dotenv

HF_TEST_QUERY = "Create a JSON plan to analyze sales data for Q4."

def test_huggingface_generate_json_response():
    print("\n--- Testing Hugging Face LLM Client ---")
    load_dotenv()
    # Build a single string prompt for Hugging Face model
    prompt = (
        "You are an expert data analysis planner. Return only valid JSON.\n"
        f"User Query: {HF_TEST_QUERY}"
    )
    response = huggingface_client.generate_json_response(prompt)
    print(f"Hugging Face response steps: {response.get('steps')}")
    assert isinstance(response, dict)
    assert "steps" in response
    assert isinstance(response["steps"], list)
