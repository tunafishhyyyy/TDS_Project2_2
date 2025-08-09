
import pytest
from app.llm_client import llm_client, gemini_client

OPENAI_TEST_QUERY = "Create a JSON plan to analyze sales data for Q4."
GEMINI_TEST_QUERY = "Create a JSON plan to analyze user engagement data for 2024."

@pytest.mark.parametrize("client,query,label", [
    (llm_client, OPENAI_TEST_QUERY, "OpenAI"),
    (gemini_client, GEMINI_TEST_QUERY, "Gemini")
])
def test_llm_generate_json_response(client, query, label):
    print(f"\n--- Testing {label} LLM Client ---")
    messages = [
        {"role": "system", "content": "You are an expert data analysis planner. Return only valid JSON."},
        {"role": "user", "content": query}
    ]
    response = client.generate_json_response(messages)
    print(f"{label} response steps: {response.get('steps')}")
    assert isinstance(response, dict)
    assert "steps" in response
    assert isinstance(response["steps"], list)


def test_generate_plan():
    from planner.planner_client import planner_client
    query = "Analyze website traffic trends for the last month."
    print("\n--- Testing generate_plan ---")
    plan = planner_client.generate_plan(query)
    print(f"Plan steps: {[step.tool for step in plan.steps]}")
    assert hasattr(plan, "steps")
    assert isinstance(plan.steps, list)
    assert len(plan.steps) > 0
    for step in plan.steps:
        assert hasattr(step, "tool")
        assert hasattr(step, "params")
        assert hasattr(step, "expected_output")
