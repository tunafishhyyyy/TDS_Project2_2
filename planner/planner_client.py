"""
Planner module for generating execution plans
"""
import json
from typing import Dict, Any, Optional
from app.models import ExecutionPlan, ExecutionStep, ToolType, StepStatus
from app.llm_client import llm_client
from app.logger import logger


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
    
    def generate_plan(
        self, 
        query: str, 
        context: Optional[Dict[str, Any]] = None
    ) -> ExecutionPlan:
        """Generate execution plan from user query"""
        try:
            logger.info(f"Generating plan for query: {query}")
            
            # Prepare prompt
            prompt = self.prompt_template.format(
                query=query,
                context=json.dumps(context or {}, indent=2)
            )
            
            # Get LLM response
            messages = [
                {"role": "system", "content": "You are an expert data analysis planner."},
                {"role": "user", "content": prompt}
            ]
            
            response = llm_client.generate_json_response(messages)
            
            # Parse and validate response
            steps = []
            for step_data in response.get("steps", []):
                step = ExecutionStep(
                    step_id=step_data["step_id"],
                    tool=ToolType(step_data["tool"]),
                    params=step_data["params"],
                    expected_output=step_data["expected_output"],
                    status=StepStatus.PENDING
                )
                steps.append(step)
            
            plan = ExecutionPlan(steps=steps)
            
            logger.info(f"Generated plan with {len(steps)} steps")
            return plan
            
        except Exception as e:
            logger.error(f"Failed to generate plan: {str(e)}")
            raise


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
        
        Failed step: {failed_step}
        Error: {error_details}
        
        Return updated JSON plan.
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
                original_plan=original_plan.model_dump_json(indent=2),
                failed_step=failed_step.model_dump_json(indent=2),
                error_details=error_details,
                verification_issues=json.dumps(verification_issues or {})
            )
            
            # Get LLM response
            messages = [
                {"role": "system", "content": "You are an expert replanner."},
                {"role": "user", "content": prompt}
            ]
            
            response = llm_client.generate_json_response(messages)
            
            # Parse response and create new plan
            steps = []
            for step_data in response.get("steps", []):
                step = ExecutionStep(
                    step_id=step_data["step_id"],
                    tool=ToolType(step_data["tool"]),
                    params=step_data["params"],
                    expected_output=step_data["expected_output"],
                    status=StepStatus.PENDING
                )
                steps.append(step)
            
            new_plan = ExecutionPlan(steps=steps)
            
            logger.info(f"Generated replan with {len(steps)} steps")
            return new_plan
            
        except Exception as e:
            logger.error(f"Failed to replan: {str(e)}")
            raise


# Global instances
planner_client = PlannerClient()
replanner_client = ReplannerClient()
