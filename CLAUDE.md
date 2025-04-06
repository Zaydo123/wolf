# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Build and Run Commands
- Run backend: `cd backend && python -m uvicorn app.main:app --reload`
- Alternative: `cd backend && ./run.sh`
- Run tests: `cd backend && python -m app.tests.test_registration`
- Run single test: `cd backend && python -m app.tests.<test_file>`
- Run frontend: `cd frontend && npm run dev`

## Code Style Guidelines
- **Imports**: Group imports by standard lib, third-party, and local app modules
- **Async**: Prefer async/await for I/O bound operations with proper error handling 
- **Error Handling**: Use try/except with specific exceptions and logging
- **Type Hints**: Use Python type hints for function parameters and return values
- **Naming**: 
  - snake_case for variables and functions
  - PascalCase for classes 
  - ALL_CAPS for constants
- **API Endpoints**: Follow RESTful conventions with proper HTTP status codes
- **Logging**: Include context in log messages and appropriate log levels
- **Environment Variables**: Use .env files with python-dotenv, access via config.py

When making changes, maintain the existing code patterns and async flow.