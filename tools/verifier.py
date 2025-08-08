"""
Verification tools for validating step outputs
"""
from typing import Dict, Any
from app.models import VerificationResult
from app.llm_client import llm_client
from app.logger import logger
import json


class VerifierTool:
    """LLM-based and rule-based verification"""
    
    def __init__(self):
        self.prompt_template = self._load_prompt_template()
    
    def _load_prompt_template(self) -> str:
        """Load the verifier prompt template"""
        try:
            with open("prompts/verifier_prompt.md", "r") as f:
                return f.read()
        except FileNotFoundError:
            logger.error("Verifier prompt template not found")
            return self._get_default_prompt()
    
    def _get_default_prompt(self) -> str:
        """Default prompt if template file is missing"""
        return """
        You are a verification expert. Analyze the step output for correctness.
        
        Step: {tool}
        Expected: {expected_output}
        Actual output: {output}
        
        Return JSON with score (0-1), confidence, issues list, and passed boolean.
        """
    
    def verify_step(
        self,
        step_id: int,
        tool: str,
        params: Dict[str, Any],
        output: Any,
        expected_output: str,
        previous_context: Dict[str, Any] = None
    ) -> VerificationResult:
        """Verify a step's output"""
        try:
            logger.info(f"Verifying step {step_id}: {tool}")
            
            # Combine rule-based and LLM-based verification
            rule_result = self._rule_based_verification(tool, params, output)
            llm_result = self._llm_based_verification(
                step_id, tool, params, output, expected_output, previous_context
            )
            
            # Combine results (weighted average)
            combined_score = (rule_result.score * 0.3) + (llm_result.score * 0.7)
            combined_confidence = min(rule_result.confidence, llm_result.confidence)
            
            combined_issues = rule_result.issues + llm_result.issues
            passed = combined_score >= 0.7 and not any("critical" in issue.lower() for issue in combined_issues)
            
            result = VerificationResult(
                score=combined_score,
                confidence=combined_confidence,
                issues=combined_issues,
                passed=passed
            )
            
            logger.info(f"Verification result: score={result.score:.2f}, passed={result.passed}")
            return result
            
        except Exception as e:
            logger.error(f"Verification failed: {str(e)}")
            return VerificationResult(
                score=0.0,
                confidence=0.0,
                issues=[f"Verification error: {str(e)}"],
                passed=False
            )
    
    def _rule_based_verification(self, tool: str, params: Dict[str, Any], output: Any) -> VerificationResult:
        """Rule-based verification checks"""
        issues = []
        score = 1.0
        
        # Basic output validation
        if output is None:
            issues.append("Output is None")
            score -= 0.5
        
        # Tool-specific validation
        if tool == "fetch_web":
            if isinstance(output, dict) and output.get("error"):
                issues.append(f"Web fetch error: {output['error']}")
                score -= 0.4
            elif isinstance(output, dict) and not output.get("data"):
                issues.append("No data returned from web fetch")
                score -= 0.3
        
        elif tool == "load_local":
            if isinstance(output, dict) and output.get("error"):
                issues.append(f"File load error: {output['error']}")
                score -= 0.4
            elif isinstance(output, dict) and not output.get("data"):
                issues.append("No data loaded from file")
                score -= 0.3
        
        elif tool == "duckdb_runner":
            if isinstance(output, dict):
                if output.get("status") == "error":
                    issues.append(f"SQL error: {output.get('error', 'Unknown')}")
                    score -= 0.5
                elif not output.get("data"):
                    issues.append("SQL query returned no results")
                    score -= 0.2
        
        elif tool == "analyze":
            if isinstance(output, dict) and output.get("status") == "error":
                issues.append(f"Analysis error: {output.get('error', 'Unknown')}")
                score -= 0.4
        
        elif tool == "visualize":
            if isinstance(output, dict) and output.get("status") == "error":
                issues.append(f"Visualization error: {output.get('error', 'Unknown')}")
                score -= 0.4
        
        score = max(0.0, score)
        
        return VerificationResult(
            score=score,
            confidence=0.8,  # Rule-based has high confidence
            issues=issues,
            passed=score >= 0.7
        )
    
    def _llm_based_verification(
        self,
        step_id: int,
        tool: str,
        params: Dict[str, Any],
        output: Any,
        expected_output: str,
        previous_context: Dict[str, Any]
    ) -> VerificationResult:
        """LLM-based verification"""
        try:
            # Prepare output for LLM (truncate if too long)
            output_str = str(output)
            if len(output_str) > 2000:
                output_str = output_str[:2000] + "... [truncated]"
            
            # Prepare prompt
            prompt = self.prompt_template.format(
                step_id=step_id,
                tool=tool,
                params=json.dumps(params, indent=2),
                output=output_str,
                expected_output=expected_output,
                previous_context=json.dumps(previous_context or {}, indent=2)
            )
            
            # Get LLM response
            messages = [
                {"role": "system", "content": "You are an expert data verification assistant. Return only valid JSON."},
                {"role": "user", "content": prompt}
            ]
            
            response = llm_client.generate_json_response(messages)
            
            # Parse response with fallback handling
            score = float(response.get("score", 0.5))
            confidence = float(response.get("confidence", 0.5))
            issues = response.get("issues", [])
            passed = response.get("passed", False)
            
            # If response was fallback, mark as failed with reasonable score
            if "JSON parsing failed" in str(issues):
                score = 0.5
                passed = False
            
            return VerificationResult(
                score=score,
                confidence=confidence,
                issues=issues,
                passed=passed
            )
            
        except Exception as e:
            logger.error(f"LLM verification failed: {str(e)}")
            return VerificationResult(
                score=0.5,
                confidence=0.0,
                issues=[f"LLM verification error: {str(e)}"],
                passed=False
            )


def verifier(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Verify step output
    
    Args:
        params: {
            "step_id": int,
            "tool": str,
            "tool_params": dict,
            "output": any,
            "expected_output": str,
            "previous_context": dict
        }
    """
    try:
        verifier_tool = VerifierTool()
        
        result = verifier_tool.verify_step(
            step_id=params.get("step_id"),
            tool=params.get("tool"),
            params=params.get("tool_params", {}),
            output=params.get("output"),
            expected_output=params.get("expected_output", ""),
            previous_context=params.get("previous_context", {})
        )
        
        return {
            "status": "success",
            "data": result.dict(),
            "passed": result.passed
        }
        
    except Exception as e:
        logger.error(f"Verifier tool failed: {str(e)}")
        return {
            "status": "error",
            "error": str(e),
            "passed": False
        }


# Global verifier instance
verifier_tool = VerifierTool()
