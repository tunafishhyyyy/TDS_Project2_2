# Copilot Instructions for TDS_Project2_2

## Overview
This project is a modular LLM orchestration framework designed for data analysis. It integrates multiple components such as planners, tools, and verifiers to process user queries and generate actionable insights. The application is containerized using Docker and exposes a FastAPI-based API for interaction.

## Architecture
- **Orchestrator**: Central component that coordinates the planner, tools, and verifier.
- **Planner**: Generates execution plans for user queries.
- **Tools Layer**: Executes specific tasks like data scraping or transformation.
- **Verifier**: Validates the results of executed plans.
- **FastAPI**: Provides API endpoints for user interaction and health checks.

Key files:
- `main.py`: Entry point for the FastAPI application.
- `orchestrator.py`: Implements the orchestration logic.
- `planner/`: Contains the planner logic.
- `tools/`: Houses modular tools for specific tasks.
- `tests/`: Includes unit tests for various components.

## Developer Workflows

### Running the Application
1. Ensure Docker is installed.
2. Start the application:
   ```bash
   docker-compose up -d
   ```
3. Stop the application:
   ```bash
   docker-compose down
   ```

### Testing
- Run tests from within the Docker container using `pytest`:
  ```bash
  docker exec -it llm_orchestrator pytest tests/
  ```

### Linting
- Activate the virtual environment:
  ```bash
  source venv/bin/activate
  ```
- Run `flake8` for linting:
  ```bash
  flake8
  ```
- Alternatively, use the `fix_lint.sh` script after modifying it appropriately.

### Debugging
- Check logs for the Docker container:
  ```bash
  docker logs llm_orchestrator
  ```

### Health Check
- Verify the application's health status:
  ```bash
  curl http://localhost:8080/health
  ```

## Project-Specific Conventions
- All commands and tests should be executed within the Docker container unless explicitly stated.
- Environment variables are managed via the `.env` file. Ensure it is correctly configured before starting the application.
- Prompts and scraping logic should be generic and adaptable to any table or use case.

## External Dependencies
- **OpenAI API**: Used for LLM integration. Ensure `OPENAI_API_KEY` is set in the `.env` file.
- **Docker**: Required for containerized deployment.
- **flake8**: Used for linting Python code.

## Key Patterns
- Modular design: Each component (planner, tools, verifier) is independent and reusable.
- Observability: Logs are generated for every step, ensuring transparency.
- Fallback mechanisms: Automatic replanning on failure.

For further details, refer to the `README.md` file or specific directories like `planner/` and `tools/`.

## Local Development
- When running Python commands locally, ensure the virtual environment is activated:
  ```bash
  source venv/bin/activate
  ```
