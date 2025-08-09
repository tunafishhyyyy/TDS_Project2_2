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
from app.logger import logger, log_step_execution


import json

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
            question_file = request.context.get("question_file") if request.context else None
            
            if question_file:
                logger.info(f"Using question file: {question_file}")
                plan = planner_client.generate_plan(
                    context=request.context,
                    question_file=question_file
                )
            else:
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
        """Execute all steps in the plan and format answers as JSON array"""
        try:
            steps_count = len(plan.steps)
            plan_msg = f"Executing plan {plan.plan_id} with {steps_count} steps"
            logger.info(plan_msg)
            previous_context = {}
            answers = []
            schema = None
            i = 0
            while i < len(plan.steps):
                step = plan.steps[i]
                # If this is the data_analysis step, capture schema
                if step.tool == "analyze" and step.params.get("task") == "data_structure":
                    logger.info(f"[DEBUG] Running data structure analysis step (step_id={step.step_id})")
                    result = await self._execute_step(step, previous_context)
                    logger.info(f"[DEBUG] Data structure analysis step result: {result}")
                    if result is None:
                        logger.warning(f"[SCHEMA] Data structure analysis step failed to produce any result.")
                    elif not isinstance(result, dict):
                        logger.warning(f"[SCHEMA] Data structure analysis result is not a dict: {type(result)}")
                    elif "fields" not in result:
                        logger.warning(f"[SCHEMA] Data structure analysis result missing 'fields' key. Keys: {list(result.keys())}")
                    else:
                        schema = result["fields"]
                        previous_context["schema"] = schema
                        logger.info(f"[SCHEMA] Data structure analysis result: {json.dumps(schema, indent=2)}")
                    previous_context[f"step_{step.step_id}"] = result
                    formatted_result = self._format_step_result(step, result)
                    if formatted_result:
                        answers.append(str(formatted_result))
                    i += 1
                    continue
                # If step_type is 'llm_query', refine it before execution
                if hasattr(step, 'step_type') and step.step_type == "llm_query":
                    logger.info(f"Refining step {step.step_id} with LLM (step_type=llm_query)")
                    # Use planner_client to further decompose/refine this step
                    # Pass schema as context if available
                    refine_context = previous_context.copy()
                    if schema:
                        refine_context["schema"] = schema
                    refined_plan = planner_client.generate_plan(
                        query=step.expected_output,
                        context=refine_context
                    )
                    # Replace the llm_query step with its refined steps
                    plan.steps = plan.steps[:i] + refined_plan.steps + plan.steps[i+1:]
                    steps_count = len(plan.steps)
                    continue
                # For all other steps, pass schema in context if available
                exec_context = previous_context.copy()
                if schema:
                    exec_context["schema"] = schema
                result = await self._execute_step(step, exec_context)
                if result is None:
                    success = await self._handle_step_failure(
                        plan, step, exec_context)
                    if not success:
                        step_id = step.step_id
                        error_msg = f"Plan execution failed at step {step_id}"
                        logger.error(error_msg)
                        return answers if answers else ["Processing failed"]
                else:
                    previous_context[f"step_{step.step_id}"] = result
                    formatted_result = self._format_step_result(step, result)
                    if not formatted_result and step.tool == "analyze":
                        if isinstance(result, dict) and "data" in result:
                            import numpy as np
                            def safe_json(obj):
                                import pandas as pd
                                if isinstance(obj, (np.integer, np.int64, np.int32)):
                                    return int(obj)
                                if isinstance(obj, (np.floating, np.float64, np.float32)):
                                    return float(obj)
                                if isinstance(obj, np.dtype):
                                    return str(obj)
                                if isinstance(obj, pd.Series):
                                    return obj.tolist()
                                if isinstance(obj, pd.DataFrame):
                                    return obj.to_dict()
                                if hasattr(obj, 'tolist'):
                                    return obj.tolist()
                                return str(obj)
                            formatted_result = json.dumps(result["data"], default=safe_json)
                    if formatted_result:
                        answers.append(str(formatted_result))
                i += 1
            return answers if answers else ["Processing failed"]
        except Exception as e:
            logger.error(f"Plan execution failed: {str(e)}")
            return None

    def _format_step_result(self,
                            step: ExecutionStep,
                            result: Any) -> Optional[str]:
        """Format step result into a human-readable answer"""
        try:
            # For counting operations
            if isinstance(result, dict) and "count" in result:
                return f"Count result: {result['count']}"

            # For data filtering/analysis with metadata
            if (isinstance(result, dict) and "metadata" in result and
                    "filtered_rows" in result["metadata"]):
                count = result["metadata"]["filtered_rows"]
                return f"Filtered results count: {count}"

            # For correlation analysis
            if isinstance(result, dict) and "data" in result:
                data = result["data"]
                if isinstance(data, dict) and "correlation_matrix" in data:
                    # Extract correlation values generically
                    corr_matrix = data["correlation_matrix"]
                    correlations = []
                    for col1, values in corr_matrix.items():
                        for col2, corr_val in values.items():
                            if col1 != col2 and isinstance(corr_val, float):
                                corr_rounded = round(corr_val, 4)
                                corr_text = (f"{col1} vs {col2}: "
                                             f"{corr_rounded}")
                                correlations.append(corr_text)
                    if correlations:
                        return "Correlations: " + ", ".join(correlations)

            # For visualization results (data URIs)
            if (isinstance(result, dict) and "data" in result and
                    isinstance(result["data"], str) and
                    result["data"].startswith("data:image")):
                return f"Visualization: {result['data']}"

            # For data results with records
            if (isinstance(result, dict) and "data" in result and
                    isinstance(result["data"], list) and result["data"]):
                data_list = result["data"]
                if len(data_list) == 1:
                    # Single result - format nicely
                    item = data_list[0]
                    if isinstance(item, dict):
                        key_values = [f"{k}: {v}" for k, v in item.items()
                                      if k not in ['Ref']]  # Skip refs
                        # Limit to 5 fields
                        return "Result: " + ", ".join(key_values[:5])
                else:
                    # Multiple results
                    return f"Results: {len(data_list)} records found"

            # Fallback for any other result
            if isinstance(result, (str, int, float, bool)):
                return f"Result: {result}"

            # If we can't format it nicely, return None to skip
            return None

        except Exception as e:
            logger.warning(f"Failed to format step result: {str(e)}")
            return f"Step {step.step_id} completed"
    
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
            
            # Resolve step parameters from context
            resolved_params = self._resolve_parameters(
                step.params, previous_context
            )
            
            # Execute the tool
            result = tool_registry.execute_tool(step.tool, resolved_params)
            
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
            
            # Accept steps with score >= 0.3 or if issues contain JSON failure
            issues_str = str(verification_result.issues)
            json_fail = "JSON parsing failed" in issues_str
            should_accept = (verification_result.score >= 0.3 or json_fail)
            
            if not verification_result.passed and not should_accept:
                step.status = StepStatus.FAILED
                issues_str = ', '.join(verification_result.issues)
                step.error = f"Verification failed: {issues_str}"
                log_step_execution(
                    step.step_id, str(step.tool), step.params,
                    error=step.error,
                    verification_score=verification_result.score
                )
                return None
            
            # Success (either passed verification or met acceptance criteria)
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
            # Calculate execution time safely
            if 'step_start_time' in locals():
                elapsed = time.time() - step_start_time
            else:
                elapsed = 0
            step.execution_time = elapsed
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
                verification_data = {"score": failed_step.verification_score}
                new_plan = replanner_client.replan_step(
                    original_plan=plan,
                    failed_step=failed_step,
                    error_details=failed_step.error or "Unknown error",
                    verification_issues=verification_data
                )
                
                # Replace the failed step with new steps
                step_index = plan.steps.index(failed_step)
                before_steps = plan.steps[:step_index]
                after_steps = plan.steps[step_index + 1:]
                plan.steps = before_steps + new_plan.steps + after_steps
                
                # Try executing the new steps
                for new_step in new_plan.steps:
                    step_result = await self._execute_step(
                        new_step, previous_context)
                    if step_result is not None:
                        step_key = f"step_{new_step.step_id}"
                        previous_context[step_key] = step_result
                        return True
            
            return False
            
        except Exception as e:
            logger.error(f"Replanning failed: {str(e)}")
            return False
    
    def _resolve_parameters(
        self,
        params: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Resolve parameter references from context"""
        resolved = {}
        
        for key, value in params.items():
            if key == "input" and isinstance(value, str):
                # Convert 'input' parameter to 'data' parameter
                if value == "output_of_step_1" and "step_1" in context:
                    resolved["data"] = context["step_1"]
                elif value.startswith("output_of_step_"):
                    step_key = value.replace("output_of_", "")
                    if step_key in context:
                        resolved["data"] = context[step_key]
                    else:
                        resolved["data"] = value
                else:
                    resolved["data"] = value
            elif (isinstance(value, str) and
                  value.startswith("output_of_step_")):
                # Handle other parameter references
                step_key = value.replace("output_of_", "")
                if step_key in context:
                    step_output = context[step_key]
                    # If step output is a dict with 'data' field, extract it
                    if isinstance(step_output, dict) and "data" in step_output:
                        resolved[key] = step_output["data"]
                    else:
                        resolved[key] = step_output
                else:
                    resolved[key] = value
            else:
                resolved[key] = value
        
        return resolved
    
    def get_plan_status(self, plan_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a plan"""
        if plan_id not in self.active_plans:
            return None
        
        plan = self.active_plans[plan_id]
        
        success_steps = [s for s in plan.steps
                         if s.status == StepStatus.SUCCESS]
        failed_steps = [s for s in plan.steps
                        if s.status == StepStatus.FAILED]
        running_steps = (s.step_id for s in plan.steps
                         if s.status == StepStatus.RUNNING)
        
        return {
            "plan_id": plan.plan_id,
            "total_steps": len(plan.steps),
            "completed_steps": len(success_steps),
            "failed_steps": len(failed_steps),
            "current_step": next(running_steps, None),
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
