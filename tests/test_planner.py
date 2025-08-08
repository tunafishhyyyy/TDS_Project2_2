"""
Test suite for the planner module
"""
import pytest
from unittest.mock import patch, MagicMock
from planner.planner_client import PlannerClient, ReplannerClient
from app.models import ExecutionStep, StepStatus, ToolType


@pytest.fixture
def planner_client():
    """Create planner client instance"""
    return PlannerClient()


@pytest.fixture
def replanner_client():
    """Create replanner client instance"""  
    return ReplannerClient()


class TestPlannerClient:
    
    def test_generate_plan_success(self, planner_client):
        """Test successful plan generation"""
        mock_response = {
            "steps": [
                {
                    "step_id": 1,
                    "tool": "fetch_web",
                    "params": {"query": "test query"},
                    "expected_output": "Web data"
                }
            ]
        }
        
        with patch('app.llm_client.llm_client.generate_json_response') as mock_llm:
            mock_llm.return_value = mock_response
            
            plan = planner_client.generate_plan("test query")
            
            assert len(plan.steps) == 1
            assert plan.steps[0].step_id == 1
            assert plan.steps[0].tool == ToolType.FETCH_WEB
            assert plan.steps[0].status == StepStatus.PENDING
    
    def test_generate_plan_with_context(self, planner_client):
        """Test plan generation with context"""
        mock_response = {
            "steps": [
                {
                    "step_id": 1,
                    "tool": "load_local", 
                    "params": {"file_path": "/data/test.csv"},
                    "expected_output": "CSV data"
                }
            ]
        }
        
        with patch('app.llm_client.llm_client.generate_json_response') as mock_llm:
            mock_llm.return_value = mock_response
            
            context = {"files": ["test.csv"]}
            plan = planner_client.generate_plan("analyze data", context)
            
            assert len(plan.steps) == 1
            assert plan.steps[0].tool == ToolType.LOAD_LOCAL


class TestReplannerClient:
    
    def test_replan_step_success(self, replanner_client):
        """Test successful step replanning"""
        from app.models import ExecutionPlan
        
        original_plan = ExecutionPlan(steps=[])
        failed_step = ExecutionStep(
            step_id=1,
            tool=ToolType.FETCH_WEB,
            params={"query": "test"},
            expected_output="data",
            status=StepStatus.FAILED,
            error="Connection timeout"
        )
        
        mock_response = {
            "steps": [
                {
                    "step_id": 2,
                    "tool": "load_local",
                    "params": {"file_path": "/backup/data.csv"},
                    "expected_output": "Backup data"
                }
            ]
        }
        
        with patch('app.llm_client.llm_client.generate_json_response') as mock_llm:
            mock_llm.return_value = mock_response
            
            new_plan = replanner_client.replan_step(
                original_plan, failed_step, "Connection timeout"
            )
            
            assert len(new_plan.steps) == 1
            assert new_plan.steps[0].step_id == 2
            assert new_plan.steps[0].tool == ToolType.LOAD_LOCAL
