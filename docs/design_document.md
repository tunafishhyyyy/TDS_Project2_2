# Design Document – Modular LLM Orchestration Framework for Data Analysis

## 1. Project Overview
We aim to build a **generic, modular orchestration framework** that can handle question-answering workflows using LLMs across diverse data sources, without tying the logic to specific pages or datasets. The system must:

- Dynamically determine the steps required to answer a query.
- Perform each step with validation, self-checks, and cross-verification.
- Work with multiple data ingestion methods (web scraping, CSV ingestion, API queries).
- Support pluggable modules for future extensibility.

## 1. Overview

This system provides an LLM-driven, tool-augmented framework for answering complex analytical queries involving data fetching, analysis, and visualization.
Unlike typical LangChain “chains”, the architecture here **decouples planning, execution, and verification** into clean modules to improve maintainability, debugging, and testability.

It is designed to:

- Accept **natural language queries** from users (via API or CLI)
- Plan execution steps **as structured JSON**
- Execute steps using **local or external tools**
- Self-verify results and replan if needed
- Return **final results in structured form** with provenance

---

## 2. Goals

- **Modular**: Independent, reusable components (planner, tools, verifier, orchestrator)
- **Observable**: Every step logged with context & results
- **Testable**: Each tool and LLM prompt tested separately
- **Fallback-safe**: Automatic replanning on failure
- **Minimal vendor lock-in**: LangChain removed; LLM calls are direct
- **Human-auditable**: Plans, intermediate results, and verification output stored

---

## 3. High-Level Architecture

```
         ┌────────────┐
         │ User Query │
         └─────┬──────┘
               │
         ┌─────▼────────┐
         │ Orchestrator │
         └─────┬────────┘
    ┌──────────┼──────────┐
    │          │          │
┌───▼───┐ ┌────▼─────┐ ┌──▼─────┐
│Planner│ │Executor  │ │Verifier│
└───┬───┘ └────┬─────┘ └──┬─────┘
    │          │          │
    │   ┌──────▼─────┐    │
    └──►Tools Layer  │◄───┘
        └────────────┘
```

---

## 4. Components

### 4.1 Orchestrator (`app/orchestrator.py`)

Central control logic:

1. Receives the user query and optional file/data context.
2. Invokes **Planner** to generate JSON execution plan.
3. Executes each step sequentially via **Tools**.
4. Sends results to **Verifier** after each step.
5. On failure, invokes **Replanner** for alternative strategy.
6. Aggregates final outputs & formats response.

**Responsibilities**:

- Flow control
- Error handling
- Logging and step-tracking
- Managing retries

### 4.2 Planner (`planner/planner_client.py`)

- Calls LLM with **`planner_prompt.md`**.
- Returns JSON with:

  - `step_id`
  - `tool` (name of tool to run)
  - `params` (arguments for tool)
  - `expected_output` (short description)
- No execution — only planning.

**Schema Example**:

```json
{
  "steps": [
    {
      "step_id": 1,
      "tool": "fetch_web",
      "params": {"query": "top-grossing movies 2024"},
      "expected_output": "Table of top 10 movies with revenue"
    }
  ]
}
```

### 4.3 Replanner (`planner/replanner_client.py`)

- Triggered when a step fails or verifier gives low confidence.
- Uses **`replanner_prompt.md`** to replan only the failed step or adjust the whole plan.
- Returns revised JSON plan.

### 4.4 Verifier (`tools/verifier.py`)

- Uses **`verifier_prompt.md`** to cross-check intermediate output.
- Confidence scoring (0–1) for:

  - Factual correctness
  - Consistency with prior steps
  - Data completeness
- Low score triggers replanning.

### 4.5 Tools Layer (`tools/`)

Reusable Python modules for specific actions:

- **`fetch_web.py`** – web scraping / API queries
- **`load_local.py`** – load local CSV/JSON/DB files
- **`duckdb_runner.py`** – run SQL queries on in-memory datasets
- **`analyze.py`** – statistical summaries, transformations
- **`visualize.py`** – charts (Matplotlib/Plotly)
- **`verifier.py`** – LLM-based and rule-based checks

**Rules**:

- Each tool has a **pure Python function** with typed inputs/outputs.
- No direct LLM calls inside tools (except verifier).

### 4.6 Response Formatter (`app/formatter.py`)

- Converts internal Python objects to:

  - JSON API response
  - Markdown/HTML (for notebooks)
  - CLI-friendly text

### 4.7 Prompts (`prompts/`)

- **`planner_prompt.md`** – step-by-step plan request
- **`replanner_prompt.md`** – recovery strategy
- **`verifier_prompt.md`** – structured checks
- **`clarifier_prompt.md`** – for ambiguous queries

---

## 5. Data Flow Example

**User query**:
*"Find the highest grossing film of 2024 and show a bar chart of its top 5 cast members’ screen time."*

1. **Planner** returns:

```json
{
  "steps": [
    {"step_id": 1, "tool": "fetch_web", "params": {"query": "highest grossing film 2024"}},
    {"step_id": 2, "tool": "fetch_web", "params": {"query": "cast members of <film> with screen time"}},
    {"step_id": 3, "tool": "visualize", "params": {"type": "bar", "x": "actor", "y": "screen_time"}}
  ]
}
```

2. **Executor** runs step 1, passes to **Verifier**.
3. If verification passes, moves to step 2.
4. On a failed verification, invokes **Replanner**.
5. Final result formatted and returned.

---

## 6. Error Handling & Fallbacks

- **Tool Failure** → retry with different params (via Replanner)
- **LLM Parse Error** → retry with stricter output formatting prompt
- **Verifier Low Score** → step re-execution or alternate tool

---

## 7. Observability & Logging

- Structured JSON logs for every step:

```json
{
  "step_id": 2,
  "tool": "fetch_web",
  "input": {"query": "cast members..."},
  "output_preview": "...",
  "verification_score": 0.92,
  "status": "success"
}
```

- Logs stored locally + optional Elastic/Prometheus integration.

---

## 8. Testing

- **Unit tests** for each tool
- **Prompt tests** with mocked LLM responses
- **End-to-end tests** with sample queries
- **Failure simulations** to test replanning

---

## 9. Deployment

- **Dockerfile** with multi-stage build (slim Python runtime)
- `.env.example` for API keys (OpenAI, search APIs)
- **docker-compose.yml** for local dev
- FastAPI exposed on port 8080

---

## 10. Example `.env.example`

```
OPENAI_API_KEY=your_key
SEARCH_API_KEY=your_key
ENV=dev
LOG_LEVEL=debug
```

---

## 11. Advantages Over Original LangChain Version

- **Transparent flow** instead of hidden chains
- **Easier debugging** (each step is visible & logged)
- **Better testability** (tools & planner separable)
- **More maintainable** (no nested callbacks/agents)
- **Vendor flexibility** (swap LLM providers easily)

---

## 12. Future Extensions

- Multi-turn conversational mode
- Caching of frequent queries
- Streaming partial results
- Interactive visualizations in the UI
- Offline mode using local LLM

---

## References
- [Jivraj-18/p2-demo-05-2025](https://github.com/Jivraj-18/p2-demo-05-2025)
- [TDS_Project2 – LangChain version of this project my initial attempt on this project, has multiple issues.](https://github.com/tunafishhyyyy/TDS_Project2/tree/main/Project2)
