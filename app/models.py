"""
Data Models and Types for the Orchestration Framework
"""
import time
from typing import List, Dict, Any, Optional, Union
from pydantic import BaseModel, Field
from enum import Enum


class StepStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    RETRYING = "retrying"


class ToolType(str, Enum):
    FETCH_WEB = "fetch_web"
    LOAD_LOCAL = "load_local"
    DUCKDB_RUNNER = "duckdb_runner"
    ANALYZE = "analyze"
    VISUALIZE = "visualize"
    VERIFIER = "verifier"


class ExecutionStep(BaseModel):
    step_id: int
    tool: ToolType
    params: Dict[str, Any]
    expected_output: str
    step_type: str = "action"  # can be "action", "llm_query", "refine"
    status: StepStatus = StepStatus.PENDING
    output: Optional[Any] = None
    error: Optional[str] = None
    verification_score: Optional[float] = None
    execution_time: Optional[float] = None


class ExecutionPlan(BaseModel):
    steps: List[ExecutionStep]
    plan_id: str = Field(default_factory=lambda: f"plan_{int(time.time())}")
    created_at: Optional[str] = None
    planning_stats: Optional[Dict[str, Any]] = None  # Planning statistics and metadata


class QueryRequest(BaseModel):
    query: str
    context: Optional[Dict[str, Any]] = None
    files: Optional[List[str]] = None


class QueryResponse(BaseModel):
    plan_id: str
    status: str
    result: Optional[Any] = None
    steps: List[ExecutionStep]
    error: Optional[str] = None
    execution_time: Optional[float] = None


class VerificationResult(BaseModel):
    score: float = Field(ge=0.0, le=1.0)
    confidence: float = Field(ge=0.0, le=1.0)
    issues: List[str] = []
    passed: bool
