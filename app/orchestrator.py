"""
Main Orchestrator - Central control logic
"""
import time
from typing import Dict, Any, List, Optional
from app.models import (
    ExecutionPlan, ExecutionStep, StepStatus, QueryRequest, QueryResponse
)
from planner.planner_client import planner_client, replanner_client
from tools import tool_registry
from tools.verifier import verifier_tool
from app.formatter import response_formatter
from app.config import config
from app.logger import logger, log_step_execution


class Orchestrator:
    """Central orchestration engine"""
    
    def __init__(self):
        self.active_plans: Dict[str, ExecutionPlan] = {}
        self.execution_history: List[Dict[str, Any]] = []
    
    async def process_query(self, request: QueryRequest) -> QueryResponse:
        """Main entry point for query processing"""
        start_time = time.time()
        
        try:
            logger.info(f"Processing query: {request.query}")
            
            # Step 1: Generate execution plan
            plan = planner_client.generate_plan(
                query=request.query,
                context=request.context
            )
            
            self.active_plans[plan.plan_id] = plan
            
            # Step 2: Execute plan
            final_result = await self._execute_plan(plan)
            
            # Step 3: Format response
            execution_time = time.time() - start_time
            
            response = QueryResponse(
                plan_id=plan.plan_id,
                status="success" if final_result else "failed",
                result=final_result,
                steps=plan.steps,
                execution_time=execution_time
            )
            
            logger.info(f"Query completed in {execution_time:.2f}s")
            return response
            
        except Exception as e:
            logger.error(f"Query processing failed: {str(e)}")
            return QueryResponse(
                plan_id="error",
                status="failed",
                error=str(e),
                steps=[],
                execution_time=time.time() - start_time
            )
    
    async def _execute_plan(self, plan: ExecutionPlan) -> Any:
        """Execute all steps in the plan"""
        try:
            logger.info(f"Executing plan {plan.plan_id} with {len(plan.steps)} steps")
            
            previous_context = {}
            final_result = None
            
            for step in plan.steps:
                result = await self._execute_step(step, previous_context)
                
                if result is None:
                    # Step failed, try to replan
                    success = await self._handle_step_failure(plan, step, previous_context)
                    if not success:
                        logger.error(f"Plan execution failed at step {step.step_id}")
                        return None
                else:
                    # Update context for next steps
                    previous_context[f"step_{step.step_id}"] = result
                    final_result = result
            
            return final_result
            
        except Exception as e:
            logger.error(f"Plan execution failed: {str(e)}")
            return None
    
    async def _execute_step(
        self, 
        step: ExecutionStep, 
        previous_context: Dict[str, Any]
    ) -> Optional[Any]:
        """Execute a single step"""
        try:
            logger.info(f"Executing step {step.step_id}: {step.tool}")
            
            step.status = StepStatus.RUNNING
            step_start_time = time.time()
            
            # Execute the tool
            result = tool_registry.execute_tool(step.tool, step.params)
            
            if isinstance(result, dict) and result.get("status") == "error":
                step.status = StepStatus.FAILED
                step.error = result.get("error")
                log_step_execution(
                    step.step_id, str(step.tool), step.params, 
                    error=step.error
                )
                return None
            
            # Verify the result
            verification_result = verifier_tool.verify_step(
                step_id=step.step_id,
                tool=str(step.tool),
                params=step.params,
                output=result,
                expected_output=step.expected_output,
                previous_context=previous_context
            )
            
            step.verification_score = verification_result.score
            step.execution_time = time.time() - step_start_time
            
            if not verification_result.passed:
                step.status = StepStatus.FAILED
                step.error = f"Verification failed: {', '.join(verification_result.issues)}"
                log_step_execution(
                    step.step_id, str(step.tool), step.params,
                    error=step.error,
                    verification_score=verification_result.score
                )
                return None
            
            # Success
            step.status = StepStatus.SUCCESS
            step.output = result
            
            log_step_execution(
                step.step_id, str(step.tool), step.params,
                result=result,
                verification_score=verification_result.score
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Step {step.step_id} execution failed: {str(e)}")
            step.status = StepStatus.FAILED
            step.error = str(e)
            step.execution_time = time.time() - step_start_time if 'step_start_time' in locals() else 0
            return None
    
    async def _handle_step_failure(
        self, 
        plan: ExecutionPlan, 
        failed_step: ExecutionStep, 
        previous_context: Dict[str, Any]
    ) -> bool:
        """Handle failed step by replanning"""
        try:
            logger.info(f"Handling failure for step {failed_step.step_id}")
            
            # Check if we should retry
            if failed_step.status != StepStatus.RETRYING:
                failed_step.status = StepStatus.RETRYING
                
                # Generate alternative plan
                new_plan = replanner_client.replan_step(
                    original_plan=plan,
                    failed_step=failed_step,
                    error_details=failed_step.error or "Unknown error",
                    verification_issues={"score": failed_step.verification_score}
                )
                
                # Replace the failed step with new steps
                step_index = plan.steps.index(failed_step)
                plan.steps = plan.steps[:step_index] + new_plan.steps + plan.steps[step_index + 1:]
                
                # Try executing the new steps
                for new_step in new_plan.steps:
                    result = await self._execute_step(new_step, previous_context)
                    if result is not None:
                        previous_context[f"step_{new_step.step_id}"] = result
                        return True
            
            return False
            
        except Exception as e:
            logger.error(f"Replanning failed: {str(e)}")
            return False
    
    def get_plan_status(self, plan_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a plan"""
        if plan_id not in self.active_plans:
            return None
        
        plan = self.active_plans[plan_id]
        
        return {
            "plan_id": plan.plan_id,
            "total_steps": len(plan.steps),
            "completed_steps": len([s for s in plan.steps if s.status == StepStatus.SUCCESS]),
            "failed_steps": len([s for s in plan.steps if s.status == StepStatus.FAILED]),
            "current_step": next(
                (s.step_id for s in plan.steps if s.status == StepStatus.RUNNING), None
            ),
            "steps": [
                {
                    "step_id": s.step_id,
                    "tool": str(s.tool),
                    "status": s.status,
                    "verification_score": s.verification_score,
                    "execution_time": s.execution_time,
                    "error": s.error
                }
                for s in plan.steps
            ]
        }


# Global orchestrator instance
orchestrator = Orchestrator()
