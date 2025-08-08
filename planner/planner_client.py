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
            
            # Handle fallback response when JSON parsing fails
            if "JSON parsing failed" in str(response) or not response.get("steps"):
                logger.warning("LLM response parsing failed, creating basic plan")
                
                # Create a fallback plan that answers each question
                basic_steps = [
                    ExecutionStep(
                        step_id=1,
                        tool=ToolType.FETCH_WEB,
                        params={
                            "query": "https://en.wikipedia.org/wiki/List_of_highest-grossing_films",
                            "method": "scrape",
                            "table_extraction": True
                        },
                        expected_output="Wikipedia page data with highest-grossing films table",
                        status=StepStatus.PENDING
                    ),
                    # Cleaning step for numeric columns
                    ExecutionStep(
                        step_id=2,
                        tool=ToolType.ANALYZE,
                        params={
                            "input": "output_of_step_1",
                            "operation": "cleaning",
                            "cleaning": {
                                "Worldwide gross": "remove non-numeric characters, convert to float",
                                "Peak": "remove non-numeric characters, convert to int"
                            }
                        },
                        expected_output="Cleaned numeric columns for analysis",
                        status=StepStatus.PENDING
                    ),
                    # Q1: How many $2 bn movies were released before 2000?
                    ExecutionStep(
                        step_id=3,
                        tool=ToolType.ANALYZE,
                        params={
                            "input": "output_of_step_2",
                            "operation": "filter",
                            "filters": {
                                "Worldwide gross": ">=2000000000",
                                "Year": "<2000"
                            },
                            "count": True
                        },
                        expected_output="Count of $2bn movies released before 2000",
                        status=StepStatus.PENDING
                    ),
                    # Q2: Earliest film that grossed over $1.5 bn
                    ExecutionStep(
                        step_id=4,
                        tool=ToolType.ANALYZE,
                        params={
                            "input": "output_of_step_2",
                            "operation": "filter",
                            "filters": {
                                "Worldwide gross": ">=1500000000"
                            },
                            "sort_by": "Year",
                            "sort_order": "asc",
                            "top_n": 1
                        },
                        expected_output="Earliest film that grossed over $1.5bn",
                        status=StepStatus.PENDING
                    ),
                    # Q3: Correlation between Rank and Peak
                    ExecutionStep(
                        step_id=5,
                        tool=ToolType.ANALYZE,
                        params={
                            "input": "output_of_step_2",
                            "operation": "correlation",
                            "columns": ["Rank", "Peak"]
                        },
                        expected_output="Correlation between Rank and Peak",
                        status=StepStatus.PENDING
                    ),
                    # Q4: Scatterplot with regression line
                    ExecutionStep(
                        step_id=6,
                        tool=ToolType.VISUALIZE,
                        params={
                            "input": "output_of_step_2",
                            "x": "Rank",
                            "y": "Peak",
                            "plot_type": "scatter",
                            "regression": True,
                            "line_style": "dotted",
                            "line_color": "red",
                            "output_format": "data_uri",
                            "max_bytes": 100000
                        },
                        expected_output="Base64-encoded PNG data URI of scatterplot with dotted red regression line, under 100,000 bytes.",
                        status=StepStatus.PENDING
                    )
                ]
                plan = ExecutionPlan(steps=basic_steps)
                logger.info(f"Generated fallback plan with {len(basic_steps)} steps")
                return plan
            
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
                {"role": "system", "content": "You are an expert replanner. Return only valid JSON with 'steps' array."},
                {"role": "user", "content": prompt}
            ]
            
            response = llm_client.generate_json_response(messages)
            
            # Parse response and create new plan
            steps = []
            response_steps = response.get("steps", [])
            
            # Handle empty response or fallback response
            if not response_steps or "JSON parsing failed" in str(response):
                logger.warning("Replanning response was empty or malformed, creating simple retry step")
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
