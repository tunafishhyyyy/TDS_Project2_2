"""
Test configuration
"""
import pytest
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Test configuration
pytest_plugins = [
    "pytest_asyncio"
]

# Async test configuration
@pytest.fixture
def event_loop():
    """Create an instance of the default event loop for the test session."""
    import asyncio
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# Mock configuration for tests
@pytest.fixture(autouse=True)
def mock_config():
    """Mock configuration for tests"""
    with pytest.MonkeyPatch().context() as m:
        m.setattr("app.config.config.OPENAI_API_KEY", "test-key")
        m.setattr("app.config.config.ENV", "test")
        m.setattr("app.config.config.LOG_LEVEL", "debug")
        m.setattr("app.config.config.MAX_RETRIES", 2)
        m.setattr("app.config.config.MIN_VERIFICATION_SCORE", 0.7)
        yield


# Disable actual LLM calls in tests
@pytest.fixture(autouse=True)
def mock_llm_client():
    """Mock LLM client for tests"""
    from unittest.mock import MagicMock
    
    mock_client = MagicMock()
    mock_client.generate_json_response.return_value = {
        "steps": [
            {
                "step_id": 1,
                "tool": "analyze",
                "params": {"operation": "summary"},
                "expected_output": "Summary statistics"
            }
        ]
    }
    
    with pytest.MonkeyPatch().context() as m:
        m.setattr("app.llm_client.llm_client", mock_client)
        yield mock_client
