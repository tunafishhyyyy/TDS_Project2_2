"""
FastAPI application entry point
"""
from fastapi import (FastAPI, HTTPException, BackgroundTasks, 
                     File, UploadFile, Form)
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Any, Optional, List
import uvicorn
import tempfile
import os

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


@app.post("/api/")
async def process_data_analysis(
    files: List[UploadFile] = File(...),
    question_text: Optional[str] = Form(None)
):
    """
    Main API endpoint for data analysis tasks
    Accepts multiple files and returns JSON array of answers
    """
    try:
        logger.info(f"Received API request with {len(files)} files")
        
        # Process uploaded files
        file_data = {}
        query_text = question_text
        
        for file in files:
            filename = file.filename or "unknown"
            content = await file.read()
            
            # Handle different file types
            if filename.endswith(('.txt', '.md')):
                # Text files contain the questions
                text_content = content.decode('utf-8')
                if not query_text:
                    query_text = text_content
                file_data[filename] = text_content
                
            elif filename.endswith(('.csv', '.json', '.xlsx')):
                # Data files - save temporarily and add to context
                temp_path = f"/tmp/{filename}"
                with open(temp_path, 'wb') as f:
                    f.write(content)
                file_data[filename] = temp_path
                
            elif filename.endswith(('.png', '.jpg', '.jpeg')):
                # Image files - save temporarily
                temp_path = f"/tmp/{filename}"
                with open(temp_path, 'wb') as f:
                    f.write(content)
                file_data[filename] = temp_path
        
        if not query_text:
            raise HTTPException(
                status_code=400, 
                detail="No query text found in uploaded files or form data"
            )
        
        # Create request with file context
        request = QueryRequest(
            query=query_text,
            context={"files": file_data},
            files=list(file_data.keys())
        )
        
        # Process the query
        response = await orchestrator.process_query(request)
        
        # Return JSON array format as expected
        if response.status == "success" and response.result:
            if isinstance(response.result, list):
                return response.result
            else:
                return [str(response.result)]
        else:
            error_msg = response.error or "Processing failed"
            logger.error(f"API processing failed: {error_msg}")
            raise HTTPException(status_code=500, detail=error_msg)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"API request failed: {str(e)}")
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
