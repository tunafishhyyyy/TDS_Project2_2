# Modular LLM Orchestration Framework for Data Analysis

A robust, modular framework for LLM-driven data analysis with transparent execution plans, verification, and fallback mechanisms.

## Features

- **Modular Architecture**: Independent, reusable components (planner, tools, verifier, orchestrator)
- **Observable**: Every step logged with context & results
- **Testable**: Each tool and LLM prompt tested separately
- **Fallback-safe**: Automatic replanning on failure
- **Minimal vendor lock-in**: Direct LLM calls without LangChain
- **Human-auditable**: Plans, intermediate results, and verification output stored

## Architecture

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

## Quick Start

### Prerequisites

- Python 3.11+
- OpenAI API key
- Docker (optional)

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd TDS_Project2_2
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure environment:
```bash
cp .env.example .env
# Edit .env with your API keys
```

4. Run the application:
```bash
python main.py
```

The API will be available at `http://localhost:8080`

### Docker Deployment

1. Build and run with Docker:
```bash
docker-compose up --build
```

2. Or run with production profile:
```bash
docker-compose --profile with-proxy up
```

## API Usage

### Process a Query

```bash
curl -X POST "http://localhost:8080/query" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Analyze sales data from Q4 and show trends",
    "context": {"data_source": "sales"}
  }'
```

### Check Plan Status

```bash
curl "http://localhost:8080/plan/{plan_id}/status"
```

### List Available Tools

```bash
curl "http://localhost:8080/tools"
```

## Available Tools

- **fetch_web**: Web scraping and API data retrieval
- **load_local**: Load local files (CSV, JSON, Excel, etc.)
- **duckdb_runner**: Execute SQL queries on data
- **analyze**: Statistical analysis and data transformations
- **visualize**: Create charts and visualizations
- **verifier**: LLM-based and rule-based verification

## Examples

### Example 1: Analyze CSV Data

```json
{
  "query": "Load sales.csv and show summary statistics",
  "context": {"files": ["data/sales.csv"]}
}
```

### Example 2: Web Data Analysis

```json
{
  "query": "Scrape movie data from IMDB and create a bar chart of top 10 grossing films",
  "context": {"data_source": "web"}
}
```

### Example 3: Data Visualization

```json
{
  "query": "Create a correlation heatmap of financial metrics",
  "context": {"data": "financial_data.xlsx"}
}
```

## Configuration

Environment variables (set in `.env`):

- `OPENAI_API_KEY`: Your OpenAI API key
- `SEARCH_API_KEY`: Search API key (optional)
- `ENV`: Environment (dev/prod)
- `LOG_LEVEL`: Logging level (debug/info/warning/error)
- `LLM_MODEL`: LLM model to use (default: gpt-4)
- `MAX_RETRIES`: Maximum retry attempts
- `MIN_VERIFICATION_SCORE`: Minimum verification score for steps

## Development

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov=tools --cov=planner

# Run specific test file
pytest tests/test_orchestrator.py
```

### Code Quality

```bash
# Format code
black app/ tools/ planner/ tests/

# Check linting
flake8 app/ tools/ planner/ tests/

# Type checking
mypy app/ tools/ planner/
```

### Adding New Tools

1. Create a new tool in `tools/` directory
2. Implement the tool function with proper type hints
3. Register the tool in `tools/__init__.py`
4. Add tests in `tests/test_tools.py`
5. Update documentation

### Project Structure

```
TDS_Project2_2/
├── app/                    # Core application
│   ├── __init__.py
│   ├── config.py          # Configuration
│   ├── formatter.py       # Response formatting
│   ├── llm_client.py      # Direct LLM API calls
│   ├── logger.py          # Logging utilities
│   ├── models.py          # Data models
│   └── orchestrator.py    # Main orchestration logic
├── planner/               # Planning components
│   └── planner_client.py  # Planner and replanner
├── tools/                 # Tool implementations
│   ├── __init__.py        # Tool registry
│   ├── analyze.py         # Data analysis
│   ├── duckdb_runner.py   # SQL queries
│   ├── fetch_web.py       # Web scraping
│   ├── load_local.py      # File loading
│   ├── verifier.py        # Output verification
│   └── visualize.py       # Data visualization
├── prompts/               # LLM prompts
│   ├── clarifier_prompt.md
│   ├── planner_prompt.md
│   ├── replanner_prompt.md
│   └── verifier_prompt.md
├── tests/                 # Test suite
│   ├── conftest.py        # Test configuration
│   ├── test_orchestrator.py
│   ├── test_planner.py
│   └── test_tools.py
├── main.py                # FastAPI application
├── requirements.txt       # Python dependencies
├── Dockerfile            # Docker configuration
├── docker-compose.yml    # Docker Compose
└── .env.example          # Environment template
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Run the test suite
6. Submit a pull request

## License

[MIT License](LICENSE)

## References

- [Design Document](design_document.md) - Detailed technical specification
- [OpenAI API Documentation](https://platform.openai.com/docs)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [DuckDB Documentation](https://duckdb.org/docs/)