"""
Tool registry and dispatcher
"""
from typing import Dict, Any, Callable
from app.models import ToolType
from tools.fetch_web import fetch_web
from tools.load_local import load_local
from tools.duckdb_runner import duckdb_runner
from tools.analyze import analyze
from tools.visualize import visualize
from tools.verifier import verifier
from app.logger import logger


class ToolRegistry:
    """Registry for all available tools"""
    
    def __init__(self):
        self.tools: Dict[ToolType, Callable] = {
            ToolType.FETCH_WEB: fetch_web,
            ToolType.LOAD_LOCAL: load_local,
            ToolType.DUCKDB_RUNNER: duckdb_runner,
            ToolType.ANALYZE: analyze,
            ToolType.VISUALIZE: visualize,
            ToolType.VERIFIER: verifier
        }
    
    def get_tool(self, tool_type: ToolType) -> Callable:
        """Get tool function by type"""
        if tool_type not in self.tools:
            raise ValueError(f"Unknown tool type: {tool_type}")
        return self.tools[tool_type]
    
    def execute_tool(self, tool_type: ToolType, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool with parameters"""
        try:
            tool_func = self.get_tool(tool_type)
            logger.info(f"Executing tool: {tool_type}")
            
            result = tool_func(params)
            
            if isinstance(result, dict) and result.get("status") == "error":
                logger.error(f"Tool {tool_type} failed: {result.get('error')}")
            else:
                logger.info(f"Tool {tool_type} completed successfully")
            
            return result
            
        except Exception as e:
            logger.error(f"Tool execution failed: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "tool": str(tool_type)
            }
    
    def list_tools(self) -> Dict[str, str]:
        """List all available tools"""
        return {
            str(tool_type): tool_func.__doc__ or "No description"
            for tool_type, tool_func in self.tools.items()
        }


# Global tool registry
tool_registry = ToolRegistry()
