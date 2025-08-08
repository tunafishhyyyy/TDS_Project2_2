"""
FastAPI application entry point
"""
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Any, Optional
import uvicorn

from app.models import QueryRequest, QueryResponse
from app.orchestrator import orchestrator
from app.config import config
from app.logger import logger
import asyncio

# Initialize FastAPI app
app = FastAPI(
    title="LLM Orchestration Framework",
    description="Modular framework for LLM-driven data analysis",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    """Application startup"""
    logger.info("Starting LLM Orchestration Framework")
    config.validate()


@app.on_event("shutdown") 
async def shutdown_event():
    """Application shutdown"""
    logger.info("Shutting down LLM Orchestration Framework")


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "LLM Orchestration Framework",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": str(asyncio.get_event_loop().time())
    }


@app.post("/query", response_model=QueryResponse)
async def process_query(request: QueryRequest):
    """Process a natural language query"""
    try:
        logger.info(f"Received query: {request.query}")
        response = await orchestrator.process_query(request)
        return response
        
    except Exception as e:
        logger.error(f"Query processing failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/plan/{plan_id}/status")
async def get_plan_status(plan_id: str):
    """Get status of a specific execution plan"""
    try:
        status = orchestrator.get_plan_status(plan_id)
        if status is None:
            raise HTTPException(status_code=404, detail="Plan not found")
        return status
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get plan status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/tools")
async def list_tools():
    """List all available tools"""
    try:
        from tools import tool_registry
        return {
            "tools": tool_registry.list_tools(),
            "count": len(tool_registry.tools)
        }
        
    except Exception as e:
        logger.error(f"Failed to list tools: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/test-tool/{tool_name}")
async def test_tool(tool_name: str, params: Dict[str, Any]):
    """Test a specific tool with given parameters"""
    try:
        from tools import tool_registry
        from app.models import ToolType
        
        tool_type = ToolType(tool_name)
        result = tool_registry.execute_tool(tool_type, params)
        
        return {
            "tool": tool_name,
            "params": params,
            "result": result
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid tool: {str(e)}")
    except Exception as e:
        logger.error(f"Tool test failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/config")
async def get_config():
    """Get application configuration (non-sensitive)"""
    return {
        "env": config.ENV,
        "log_level": config.LOG_LEVEL,
        "llm_model": config.LLM_MODEL,
        "max_retries": config.MAX_RETRIES,
        "min_verification_score": config.MIN_VERIFICATION_SCORE
    }


if __name__ == "__main__":
    # Run the application
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8080,
        reload=config.ENV == "dev",
        log_level=config.LOG_LEVEL.lower()
    )
