"""
Test suite for orchestrator
"""
import pytest
import asyncio
from unittest.mock import patch, MagicMock
from app.orchestrator import Orchestrator
from app.models import (
    QueryRequest, ExecutionPlan, ExecutionStep, 
    ToolType, StepStatus
)


@pytest.fixture
def orchestrator():
    """Create orchestrator instance"""
    return Orchestrator()


@pytest.fixture 
def sample_query_request():
    """Create sample query request"""
    return QueryRequest(
        query="Analyze sales data from last month",
        context={"data_source": "sales_db"}
    )


@pytest.fixture
def sample_execution_plan():
    """Create sample execution plan"""
    steps = [
        ExecutionStep(
            step_id=1,
            tool=ToolType.LOAD_LOCAL,
            params={"file_path": "/data/sales.csv"},
            expected_output="Sales data loaded"
        ),
        ExecutionStep(
            step_id=2,
            tool=ToolType.ANALYZE,
            params={"operation": "summary"},
            expected_output="Sales summary statistics"
        )
    ]
    return ExecutionPlan(steps=steps)


class TestOrchestrator:
    
    @pytest.mark.asyncio
    async def test_process_query_success(self, orchestrator, sample_query_request):
        """Test successful query processing"""
        mock_plan = ExecutionPlan(steps=[
            ExecutionStep(
                step_id=1,
                tool=ToolType.LOAD_LOCAL,
                params={"file_path": "test.csv"},
                expected_output="Data"
            )
        ])
        
        with patch('planner.planner_client.planner_client.generate_plan') as mock_planner:
            with patch.object(orchestrator, '_execute_plan') as mock_execute:
                mock_planner.return_value = mock_plan
                mock_execute.return_value = {"success": True}
                
                response = await orchestrator.process_query(sample_query_request)
                
                assert response.status == "success"
                assert response.result == {"success": True}
                assert len(response.steps) == 1
    
    @pytest.mark.asyncio
    async def test_execute_step_success(self, orchestrator):
        """Test successful step execution"""
        step = ExecutionStep(
            step_id=1,
            tool=ToolType.ANALYZE,
            params={"operation": "summary", "data": [{"a": 1}]},
            expected_output="Summary"
        )
        
        mock_tool_result = {"status": "success", "data": {"mean": 1.0}}
        mock_verification = MagicMock()
        mock_verification.passed = True
        mock_verification.score = 0.9
        
        with patch('tools.tool_registry.execute_tool') as mock_tool:
            with patch('tools.verifier.verifier_tool.verify_step') as mock_verify:
                mock_tool.return_value = mock_tool_result
                mock_verify.return_value = mock_verification
                
                result = await orchestrator._execute_step(step, {})
                
                assert result == mock_tool_result
                assert step.status == StepStatus.SUCCESS
                assert step.verification_score == 0.9
    
    @pytest.mark.asyncio
    async def test_execute_step_verification_failure(self, orchestrator):
        """Test step execution with verification failure"""
        step = ExecutionStep(
            step_id=1,
            tool=ToolType.FETCH_WEB,
            params={"query": "test"},
            expected_output="Data"
        )
        
        mock_tool_result = {"status": "success", "data": "some data"}
        mock_verification = MagicMock()
        mock_verification.passed = False
        mock_verification.score = 0.3
        mock_verification.issues = ["Data quality low"]
        
        with patch('tools.tool_registry.execute_tool') as mock_tool:
            with patch('tools.verifier.verifier_tool.verify_step') as mock_verify:
                mock_tool.return_value = mock_tool_result
                mock_verify.return_value = mock_verification
                
                result = await orchestrator._execute_step(step, {})
                
                assert result is None
                assert step.status == StepStatus.FAILED
                assert "Verification failed" in step.error
    
    @pytest.mark.asyncio
    async def test_handle_step_failure(self, orchestrator, sample_execution_plan):
        """Test step failure handling and replanning"""
        failed_step = sample_execution_plan.steps[0]
        failed_step.status = StepStatus.FAILED
        failed_step.error = "File not found"
        
        # Mock replanner response
        new_plan = ExecutionPlan(steps=[
            ExecutionStep(
                step_id=3,
                tool=ToolType.FETCH_WEB,
                params={"query": "sales data API"},
                expected_output="Sales data from API"
            )
        ])
        
        with patch('planner.planner_client.replanner_client.replan_step') as mock_replan:
            with patch.object(orchestrator, '_execute_step') as mock_execute:
                mock_replan.return_value = new_plan
                mock_execute.return_value = {"success": True}
                
                success = await orchestrator._handle_step_failure(
                    sample_execution_plan, failed_step, {}
                )
                
                assert success is True
    
    def test_get_plan_status(self, orchestrator, sample_execution_plan):
        """Test getting plan status"""
        plan_id = sample_execution_plan.plan_id
        orchestrator.active_plans[plan_id] = sample_execution_plan
        
        # Mark first step as completed
        sample_execution_plan.steps[0].status = StepStatus.SUCCESS
        
        status = orchestrator.get_plan_status(plan_id)
        
        assert status["plan_id"] == plan_id
        assert status["total_steps"] == 2
        assert status["completed_steps"] == 1
        assert status["failed_steps"] == 0
    
    def test_get_plan_status_not_found(self, orchestrator):
        """Test getting status of non-existent plan"""
        status = orchestrator.get_plan_status("nonexistent")
        assert status is None
