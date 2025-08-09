"""
Planner module for generating execution plans
"""
import json
from typing import Dict, Any, Optional, List
from app.models import ExecutionPlan, ExecutionStep, ToolType, StepStatus
from app.llm_client import llm_client
from app.logger import execution_logger_info, llm_logger_info, logger


class PlannerClient:
    """Generates execution plans from user queries"""
    
    def __init__(self):
        self.prompt_template = self._load_prompt_template()
    
    def _load_prompt_template(self) -> str:
        """Load prompt template from file"""
        try:
            with open("prompts/planner_prompt.md", "r") as f:
                return f.read()
        except FileNotFoundError:
            return self._get_default_prompt()
            
    def _load_tool_refinement_template(self) -> str:
        """Load tool refinement prompt template from file"""
        try:
            with open("prompts/tool_refinement_prompt.md", "r") as f:
                return f.read()
        except FileNotFoundError:
            return self._get_default_tool_refinement_prompt()
    
    def _get_default_prompt(self) -> str:
        """Default prompt template if file loading fails"""
        return """
You are a data analysis task breakdown expert. 
Break down user queries into atomic tasks.
Return a JSON array of task description strings.
        """.strip()
        
    def _get_default_tool_refinement_prompt(self) -> str:
        """Default tool refinement prompt if file loading fails"""
        return """
Convert task descriptions into specific tool calls.
Available tools: fetch_web, load_local, duckdb_runner, analyze, visualize.
Return JSON: {"tool": "tool_name", "params": {...}, "reasoning": "..."}
        """.strip()

    def _refine_tasks_to_tools(self, steps: List[ExecutionStep], context: dict) -> List[ExecutionStep]:
        """Refine generic task descriptions into specific tool calls using LLM"""
        refined_steps = []
        
        for step in steps:
            if step.tool == ToolType.ANALYZE and "task" in step.params:
                task_description = step.params["task"]
                logger.info(f"Refining task: {task_description}")
                
                try:
                    # Load tool refinement prompt
                    refinement_prompt = self._load_tool_refinement_template()
                    
                    # Create messages for tool refinement
                    messages = [
                        {"role": "system", "content": refinement_prompt},
                        {"role": "user", "content": f"Task: {task_description}"}
                    ]
                    
                    # Get tool refinement from LLM
                    response = llm_client.generate_completion(messages, json_mode=True)
                    logger.info(f"Tool refinement response: {response}")
                    logger.info(f"Response type: {type(response)}")
                    
                    # Parse response if it's a string
                    if response and isinstance(response, str):
                        try:
                            response = json.loads(response)
                        except json.JSONDecodeError as e:
                            logger.error(f"Failed to parse JSON response: {e}")
                            response = None
                    
                    if response and isinstance(response, dict):
                        tool_name = response.get("tool", "analyze")
                        tool_params = response.get("params", {"task": task_description})
                        reasoning = response.get("reasoning", "")
                        
                        logger.info(f"Refined to tool: {tool_name}, reasoning: {reasoning}")
                        
                        # Create refined step
                        refined_step = ExecutionStep(
                            step_id=step.step_id,
                            tool=ToolType(tool_name),
                            params=tool_params,
                            expected_output=step.expected_output,
                            status=StepStatus.PENDING
                        )
                        refined_steps.append(refined_step)
                    else:
                        logger.warning(f"Tool refinement failed for task: {task_description}")
                        refined_steps.append(step)  # Keep original
                        
                except Exception as e:
                    logger.error(f"Error refining task '{task_description}': {str(e)}")
                    refined_steps.append(step)  # Keep original on error
            else:
                refined_steps.append(step)  # Keep non-generic steps as-is
                
        return refined_steps
    
    def generate_plan_backup(self, query: str, 
                           context: Optional[Dict[str, Any]] = None
                           ) -> ExecutionPlan:
        """Backup of the original generate_plan method for reference."""
        # ...existing code...
        pass

    def generate_plan(self, query: Optional[str] = None, 
                      context: Optional[Dict[str, Any]] = None, 
                      question_file: Optional[str] = None) -> ExecutionPlan:
        """Generate execution plan using only the primary LLM client. 
        Supports referencing question from a file."""
        # If question_file is provided, handle it with separate messages
        if question_file:
            try:
                with open(question_file, "r") as f:
                    question_text = f.read()
                logger.info(f"Read question from file: {question_file}")
                
                # Create system prompt with instructions only
                system_prompt = self.prompt_template.format(
                    context=json.dumps(context or {}, indent=2)
                )
                
                messages = [
                    {"role": "system", 
                     "content": system_prompt},
                    {"role": "user", 
                     "content": f"Here is the user's question from file {question_file}:\n\n{question_text}"}
                ]
                
            except Exception as e:
                error_msg = f"Failed to read question file {question_file}: {e}"
                logger.error(error_msg)
                # Fallback to standard approach
                prompt = (self.prompt_template + 
                         f"\n\nERROR: Could not read question file " +
                         f"{question_file}. Please ensure the file exists.")
                messages = [
                    {"role": "system",
                     "content": ("You are an expert data analysis planner. " +
                                "Return only valid JSON.")},
                    {"role": "user", "content": prompt}
                ]
        else:
            prompt = self.prompt_template.format(
                query=query or "",
                context=json.dumps(context or {}, indent=2)
            )
            messages = [
                {"role": "system",
                 "content": ("You are an expert data analysis planner. " +
                            "Return only valid JSON.")},
                {"role": "user", "content": prompt}
            ]
        response = llm_client.generate_json_response(messages)
        
        # Log the interaction - use appropriate format based on structure
        if question_file:
            log_content = f"Question file: {question_file}"
        else:
            log_content = prompt
        llm_logger_info(log_content, response)

        # Parse response
        logger.info(f"Raw response: {response}")
        logger.info(f"Response type: {type(response)}")
        
        if isinstance(response, dict):
            try:
                response_json = json.loads(json.dumps(response))
            except Exception as e:
                error_msg = f"Dict to JSON conversion failed: {str(e)}"
                execution_logger_info(0, "planner", "failed", error=error_msg)
                response_json = None
        elif isinstance(response, list):
            # Handle direct list response (already parsed by LLM client)
            response_json = response
        elif isinstance(response, str):
            # Strip markdown code blocks if present
            response_clean = response.strip()
            if response_clean.startswith("```json"):
                response_clean = response_clean[7:]  # Remove ```json
            if response_clean.startswith("```"):
                response_clean = response_clean[3:]   # Remove ```
            if response_clean.endswith("```"):
                response_clean = response_clean[:-3]  # Remove closing ```
            response_clean = response_clean.strip()
            
            try:
                response_json = json.loads(response_clean)
            except Exception as e:
                error_msg = f"String to JSON parsing failed: {str(e)}"
                execution_logger_info(0, "planner", "failed", error=error_msg)
                response_json = None
        else:
            response_json = None

        # Parse and validate response_json
        steps = []
        if response_json:
            logger.info(f"Processing LLM response: {response_json}")
            logger.info(f"Response type: {type(response_json)}")
            
            # Handle new simple task array format (list of strings)
            if isinstance(response_json, list) and all(isinstance(task, str) for task in response_json):
                logger.info(f"Found simple task array with {len(response_json)} tasks")
                for i, task_description in enumerate(response_json, 1):
                    # Convert simple task description to ExecutionStep
                    # For now, default to 'analyze' tool with task description
                    step = ExecutionStep(
                        step_id=i,
                        tool=ToolType("analyze"),
                        params={"task": task_description},
                        expected_output=f"Result for: {task_description}",
                        status=StepStatus.PENDING
                    )
                    steps.append(step)
                    execution_logger_info(step.step_id, step.tool, step.status)
                    
            # Handle case where LLM returns correct format with "steps" array
                    
            # Handle case where LLM returns correct format with "steps" array
            elif response_json.get("steps"):
                logger.info("Found 'steps' array in response")
                step_list = response_json["steps"]
                
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
                        error_msg = f"Step parsing error: {str(e)}"
                        execution_logger_info(0, "planner", "failed", error=error_msg)
                        
            # Handle case where LLM returns a single step object (malformed)
            elif response_json.get("step_id") and response_json.get("tool"):
                logger.warning("LLM returned single step instead of steps array, wrapping it")
                step_list = [response_json]
                
                for step_data in step_list:
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
                        error_msg = f"Step parsing error: {str(e)}"
                        execution_logger_info(0, "planner", "failed", error=error_msg)
            else:
                error_msg = (f"LLM response has no recognizable format (steps array, "
                           f"single step, or task array): {response_json}")
                logger.error(error_msg)

        # Refine steps if we have generic analyze steps
        if steps and all(step.tool == ToolType.ANALYZE and "task" in step.params for step in steps):
            logger.info("Refining generic tasks into specific tool calls")
            steps = self._refine_tasks_to_tools(steps, context)

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
            
            # If no steps were created and we had response_steps, 
            # create a fallback
            if not steps and response_steps:
                logger.warning("No valid steps created from response, " +
                              "using fallback retry step")
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
