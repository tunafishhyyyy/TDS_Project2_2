"""
Planner module for generating execution plans
"""
import json
from typing import Dict, Any, Optional
from app.models import ExecutionPlan, ExecutionStep, ToolType, StepStatus
from app.llm_client import llm_client
from app.logger import execution_logger_info, llm_logger_info, logger


class PlannerClient:
    """Generates execution plans from user queries"""
    
    def __init__(self):
        self.prompt_template = self._load_prompt_template()
    
    def _load_prompt_template(self) -> str:
        """Load the planner prompt template"""
        try:
            with open("prompts/planner_prompt.md", "r") as f:
                return f.read()
        except FileNotFoundError:
            logger.error("Planner prompt template not found")
            return self._get_default_prompt()
    
    def _get_default_prompt(self) -> str:
        """Default prompt if template file is missing"""
        return """
        You are a step-by-step planner for data analysis tasks.
        Create a JSON plan with steps to answer the user query.
        
        Response format:
        {
          "steps": [
            {
              "step_id": 1,
              "tool": "tool_name",
              "params": {"param": "value"},
              "expected_output": "description"
            }
          ]
        }
        
        User Query: {query}
        """
    
    def generate_plan_backup(self, query: str, context: Optional[Dict[str, Any]] = None) -> ExecutionPlan:
        """Backup of the original generate_plan method for reference."""
        # ...existing code...
        pass

    def generate_plan(self, query: str, context: Optional[Dict[str, Any]] = None) -> ExecutionPlan:
        """Generate execution plan using only the primary LLM client."""
        # Prepare prompt
        prompt = self.prompt_template.format(
            query=query,
            context=json.dumps(context or {}, indent=2)
        )

        messages = [
            {"role": "system", "content": "You are an expert data analysis planner. Return only valid JSON."},
            {"role": "user", "content": prompt}
        ]
        response = llm_client.generate_json_response(messages)
        llm_logger_info(prompt, response)

        # Parse response
        if isinstance(response, dict):
            try:
                response_json = json.loads(json.dumps(response))
            except Exception as e:
                execution_logger_info(0, "planner", "failed", error=f"Dict to JSON conversion failed: {str(e)}")
                response_json = None
        elif isinstance(response, str):
            try:
                response_json = json.loads(response)
            except Exception as e:
                execution_logger_info(0, "planner", "failed", error=f"String to JSON parsing failed: {str(e)}")
                response_json = None
        else:
            response_json = None

        # Parse and validate response_json
        steps = []
        if response_json:
            logger.info(f"Processing LLM response: {response_json}")
            # Handle case where LLM returns correct format with "steps" array
            if response_json.get("steps"):
                logger.info("Found 'steps' array in response")
                step_list = response_json["steps"]
            # Handle case where LLM returns a single step object (malformed)
            elif response_json.get("step_id") and response_json.get("tool"):
                logger.warning("LLM returned single step instead of steps array, wrapping it")
                step_list = [response_json]
            else:
                logger.error(f"LLM response has no 'steps' array or valid step format: {response_json}")
                step_list = []
            
            logger.info(f"Processing {len(step_list)} steps")
            for step_data in step_list:
                # Use keys from mock response directly, fallback if missing
                step_id = step_data.get("step_id", len(steps)+1)
                tool = step_data.get("tool", "analyze")
                params = step_data.get("params", {})
                expected_output = step_data.get("expected_output", "")
                try:
                    step = ExecutionStep(
                        step_id=step_id,
                        tool=ToolType(tool),
                        params=params,
                        expected_output=expected_output,
                        status=StepStatus.PENDING
                    )
                    steps.append(step)
                    execution_logger_info(step.step_id, step.tool, step.status)
                except Exception as e:
                    execution_logger_info(0, "planner", "failed", error=f"Step parsing error: {str(e)}")

        plan = ExecutionPlan(steps=steps)
        plan_str = str(plan)
        if len(plan_str) > 500:
            plan_str = plan_str[:500] + '...'
        execution_logger_info(0, "planner", f"plan={plan_str}")
        execution_logger_info(0, "planner", "success")
        return plan


class ReplannerClient:
    """Handles replanning when steps fail"""
    
    def __init__(self):
        self.prompt_template = self._load_prompt_template()
    
    def _load_prompt_template(self) -> str:
        """Load the replanner prompt template"""
        try:
            with open("prompts/replanner_prompt.md", "r") as f:
                return f.read()
        except FileNotFoundError:
            logger.error("Replanner prompt template not found")
            return self._get_default_prompt()
    
    def _get_default_prompt(self) -> str:
        """Default prompt if template file is missing"""
        return """
        You are a replanner that fixes failed steps.
        Create an alternative approach for the failed step.
        
        Original plan: {original_plan}
        Failed step: {failed_step}
        Error: {error_details}
        Verification issues: {verification_issues}
        
        Return updated JSON plan with 'steps' array.
        """
    
    def replan_step(
        self,
        original_plan: ExecutionPlan,
        failed_step: ExecutionStep,
        error_details: str,
        verification_issues: Optional[Dict[str, Any]] = None
    ) -> ExecutionPlan:
        """Generate alternative plan for failed step"""
        try:
            logger.info(f"Replanning failed step {failed_step.step_id}")
            
            # Prepare context
            prompt = self.prompt_template.format(
                original_plan=str(original_plan),
                failed_step=str(failed_step),
                error_details=error_details,
                verification_issues=str(verification_issues or {})
            )
            
            # Get LLM response
            messages = [
                {"role": "system",
                 "content": ("You are an expert replanner. Return only "
                             "valid JSON with 'steps' array.")},
                {"role": "user", "content": prompt}
            ]
            
            response = llm_client.generate_json_response(messages)
            
            # Parse response and create new plan
            steps = []
            response_steps = []
            if isinstance(response, dict) and "steps" in response:
                response_steps = response["steps"]
            # Handle empty response or fallback response
            if not response_steps or "JSON parsing failed" in str(response):
                logger.warning("Replanning response was empty or malformed, "
                               "creating simple retry step")
                # Create a simple retry step
                step = ExecutionStep(
                    step_id=failed_step.step_id,
                    tool=failed_step.tool,
                    params=failed_step.params,
                    expected_output=failed_step.expected_output,
                    status=StepStatus.PENDING
                )
                steps.append(step)
            else:
                for step_data in response_steps:
                    step_id = step_data.get("step_id", len(steps)+1)
                    tool = step_data.get("tool", "analyze")
                    params = step_data.get("params", {})
                    expected_output = step_data.get("expected_output", "")
                    try:
                        step = ExecutionStep(
                            step_id=step_id,
                            tool=ToolType(tool),
                            params=params,
                            expected_output=expected_output,
                            status=StepStatus.PENDING
                        )
                        steps.append(step)
                    except Exception as step_error:
                        logger.error(f"Failed to create step: {step_error}")
                        continue
            
            # If no steps were created and we had response_steps, create a fallback
            if not steps and response_steps:
                logger.warning("No valid steps created from response, using fallback retry step")
                step = ExecutionStep(
                    step_id=failed_step.step_id,
                    tool=failed_step.tool,
                    params=failed_step.params,
                    expected_output=failed_step.expected_output,
                    status=StepStatus.PENDING
                )
                steps.append(step)
            
            new_plan = ExecutionPlan(steps=steps)
            
            logger.info(f"Generated replan with {len(steps)} steps")
            return new_plan
            
        except Exception as e:
            logger.error(f"Failed to replan: {str(e)}")
            # Return a fallback retry plan instead of raising
            logger.info("Creating fallback replan with retry step")
            step = ExecutionStep(
                step_id=failed_step.step_id,
                tool=failed_step.tool,
                params=failed_step.params,
                expected_output=failed_step.expected_output,
                status=StepStatus.PENDING
            )
            return ExecutionPlan(steps=[step])


# Global instances
planner_client = PlannerClient()
replanner_client = ReplannerClient()
