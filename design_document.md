# Design Document – Modular LLM Orchestration Framework for Data Analysis

## 1. Project Overview
We aim to build a **generic, modular orchestration framework** that can handle question-answering workflows using LLMs across diverse data sources, without tying the logic to specific pages or datasets. The system must:

- Dynamically determine the steps required to answer a query.
- Perform each step with validation, self-checks, and cross-verification.
- Work with multiple data ingestion methods (web scraping, CSV ingestion, API queries).
- Support pluggable modules for future extensibility.
- Be containerized using **Docker**.
- Be served as an API using **FastAPI**.

---

## 2. High-Level Architecture
### Components:
1. **FastAPI Backend**
   - REST API endpoints for:
     - Submitting a question.
     - Uploading data (CSV, JSON).
     - Triggering web scraping.
     - Checking job status.
   - Async task handling for long-running workflows.

2. **LLM Orchestration Layer**
   - Uses **LangChain / custom orchestration** for:
     - Parsing user questions.
     - Identifying required steps.
     - Selecting tools (scraper, CSV loader, API fetcher, DuckDB queries).
     - Generating intermediate prompts.
     - Validating outputs.
   - Maintains a **prompt library** in `prompts/` directory.

3. **Data Ingestion Layer**
   - **Web Scraping Module**:
     - Use libraries like Playwright/Selenium + BeautifulSoup for HTML extraction.
     - For pages with dynamic data loading, intercept network calls (via Playwright or browser dev tools protocol) to detect API endpoints.
     - LLM prompt-assisted analysis to determine if HTML contains final data or if it is API-loaded.
     - If API endpoints are found → call them directly.
   - **CSV Loader**:
     - Reads and normalizes CSV into DuckDB.
   - **API Fetcher**:
     - Calls external APIs with authentication (API keys from `.env`).

4. **Data Storage & Query Layer**
   - **DuckDB** for:
     - Local analytics and SQL queries.
     - Joining data from multiple ingestion sources.
     - Serving as a fast intermediate store for structured data.
   - **Filesystem Storage**:
     - Store raw scraped HTML, API JSON, and uploaded CSVs.

5. **Cross-Verification & Self-Checks**
   - LLM-based answer validation.
   - Multiple retrieval paths for same query and result comparison.
   - If mismatch detected → request clarifications or run alternative queries.

6. **Test Suite**
   - Unit tests for each ingestion module.
   - Integration tests for end-to-end workflows.
   - Mocked test cases for LLM orchestration.

---

## 3. Data Scraping – Detailed Flow
1. **User submits a question** → saved to DB/log.
2. **LLM determines if web scraping is required** using prompt-based decision logic.
3. **If scraping is needed**:
   - Try static HTML extraction (BeautifulSoup).
   - If data is incomplete:
     - Use Playwright/Selenium to render page.
     - Intercept network traffic to detect API calls.
     - LLM analyzes intercepted URLs & responses to determine relevant API endpoints.
4. **Store scraped/API data** in DuckDB.
5. **Run SQL queries on DuckDB** to prepare answers.

---

## 4. Example Prompt Hints (for `prompts/question.txt`)
```
Your task is to determine if a webpage's data is loaded statically or via API calls.
Hints:
- If HTML contains placeholders like "Loading...", check network requests.
- Identify JSON responses in XHR/fetch requests.
- Use API endpoints directly when found.
```

---

## 5. Dockerization
**Dockerfile**
- Python 3.11 base.
- Install Playwright browsers in build step.
- Install all dependencies from `requirements.txt`.
- Copy project files.

**docker-compose.yml**
- FastAPI service.
- Optional DuckDB persistence volume.

---

## 6. Environment Variables (`.env` Example)
```
OPENAI_API_KEY=sk-xxxx
SCRAPER_HEADLESS=true
API_BASE_URL=https://example.com/api
```

---

## 7. Testing Strategy
**Test Script Structure** (`tests/` directory):
- `test_scraper.py`: Tests for HTML/API extraction.
- `test_csv_loader.py`: Tests for CSV → DuckDB.
- `test_orchestration.py`: Mocked LLM responses to verify step planning.
- `test_api.py`: API endpoint tests.

**Example Test Cases**
1. **Case 1**: CSV ingestion + SQL query in DuckDB.
2. **Case 2**: Web scraping of static table → answer generation.

---

## 8. File/Folder Structure
```
project/
│── main.py               # FastAPI entrypoint
│── orchestrator.py       # LLM orchestration logic
│── ingestion/
│   ├── scraper.py        # Web scraping module
│   ├── csv_loader.py     # CSV ingestion
│   ├── api_fetcher.py    # API ingestion
│── prompts/
│   ├── question.txt      # Prompt for scraping decision
│   ├── validation.txt    # Prompt for cross-verification
│── storage/
│   ├── duckdb_store.py   # DuckDB wrapper
│── tests/
│   ├── test_scraper.py
│   ├── test_csv_loader.py
│   ├── test_orchestration.py
│── requirements.txt
│── Dockerfile
│── docker-compose.yml
│── .env.example
```

---

## 9. References
- [Jivraj-18/p2-demo-05-2025](https://github.com/Jivraj-18/p2-demo-05-2025)
- [TDS_Project2 – LangChain Implementation](https://github.com/tunafishhyyyy/TDS_Project2/tree/main/Project2)
