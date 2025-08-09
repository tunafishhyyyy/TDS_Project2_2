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
                logger.warning("LLM response parsing failed, creating generic fallback plan using LLM")
                # Check for DuckDB/Parquet/S3/SQL keywords in query/context
                keywords = ["parquet", "duckdb", "s3", "sql"]
                query_lower = query.lower()
                context_str = json.dumps(context or {}).lower()
                if any(k in query_lower or k in context_str for k in keywords):
                    # Try to extract a SQL query from the user query if present
                    import re
                    sql_match = re.search(
                        r"SELECT[\s\S]+?;", query, re.IGNORECASE
                    )
                    if sql_match:
                        # Use the extracted SQL query directly
                        basic_steps = [
                            ExecutionStep(
                                step_id=1,
                                tool=ToolType.DUCKDB_RUNNER,
                                params={
                                    "query": sql_match.group(0)
                                },
                                expected_output=(
                                    "Results from provided SQL query"
                                ),
                                status=StepStatus.PENDING
                            ),
                            ExecutionStep(
                                step_id=2,
                                tool=ToolType.ANALYZE,
                                params={
                                    "input": "output_of_step_1",
                                    "operation": "llm_answer",
                                    "query": query
                                },
                                expected_output=(
                                    "LLM answers using SQL query results"
                                ),
                                status=StepStatus.PENDING
                            )
                        ]
                    else:
                        # Generic fallback: run extracted SQL + analyze
                        # Try to find any SQL in context or use generic query
                        context_sql = None
                        if context:
                            context_str = json.dumps(context)
                            sql_in_context = re.search(
                                r"SELECT[\s\S]+?;", context_str, re.IGNORECASE
                            )
                            if sql_in_context:
                                context_sql = sql_in_context.group(0)
                        
                        # Use SQL from context/query, else generic sample
                        if context_sql:
                            query_to_run = context_sql
                        else:
                            query_to_run = "SELECT * FROM data LIMIT 100"
                        
                        basic_steps = [
                            ExecutionStep(
                                step_id=1,
                                tool=ToolType.DUCKDB_RUNNER,
                                params={
                                    "query": query_to_run
                                },
                                expected_output="Sample data and schema info",
                                status=StepStatus.PENDING
                            ),
                            ExecutionStep(
                                step_id=2,
                                tool=ToolType.ANALYZE,
                                params={
                                    "input": "output_of_step_1",
                                    "operation": "generate_sql",
                                    "query": query,
                                    "context": context
                                },
                                expected_output="SQL queries for analysis",
                                status=StepStatus.PENDING
                            ),
                            ExecutionStep(
                                step_id=3,
                                tool=ToolType.DUCKDB_RUNNER,
                                params={
                                    "query": "output_of_step_2"
                                },
                                expected_output="Analysis results",
                                status=StepStatus.PENDING
                            ),
                            ExecutionStep(
                                step_id=4,
                                tool=ToolType.ANALYZE,
                                params={
                                    "input": "output_of_step_3",
                                    "operation": "llm_answer",
                                    "query": query
                                },
                                expected_output=(
                                    "LLM answers using analysis results"
                                ),
                                status=StepStatus.PENDING
                            )
                        ]
                    plan = ExecutionPlan(steps=basic_steps)
                    logger.info(
                        f"Generated DuckDB fallback plan with "
                        f"{len(basic_steps)} steps"
                    )
                    return plan
                # Otherwise, fallback to web scraping
                import re
                url_pattern = r"https?://[\w\.-]+(?:/[\w\.-]*)*"
                url_match = re.search(url_pattern, query)
                url = url_match.group(0) if url_match else None
                if not url and context:
                    url_match = re.search(url_pattern, context_str)
                    url = url_match.group(0) if url_match else None
                if not url:
                    logger.error(
                        "No valid URL found in query or context "
                        "for fallback plan."
                    )
                    raise ValueError("No valid URL found for web scraping.")
                basic_steps = [
                    ExecutionStep(
                        step_id=1,
                        tool=ToolType.FETCH_WEB,
                        params={
                            "query": url,
                            "method": "scrape",
                            "table_extraction": True
                        },
                        expected_output="Data scraped from the web source",
                        status=StepStatus.PENDING
                    ),
                    ExecutionStep(
                        step_id=2,
                        tool=ToolType.ANALYZE,
                        params={
                            "input": "output_of_step_1",
                            "operation": "llm_answer",
                            "query": query
                        },
                        expected_output=(
                            "LLM answers to user questions "
                            "using the scraped data"
                        ),
                        status=StepStatus.PENDING
                    )
                ]
                plan = ExecutionPlan(steps=basic_steps)
                logger.info(
                    f"Generated generic fallback plan with "
                    f"{len(basic_steps)} steps"
                )
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
                {"role": "system",
                 "content": ("You are an expert replanner. Return only "
                             "valid JSON with 'steps' array.")},
                {"role": "user", "content": prompt}
            ]
            
            response = llm_client.generate_json_response(messages)
            
            # Parse response and create new plan
            steps = []
            response_steps = response.get("steps", [])
            
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
