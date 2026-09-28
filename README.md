# Quantitative Research and Market Analysis System

This is a professional quantitative research and market-analysis system. It is designed to evaluate multi-timeframe trading setups across various markets (Crypto, Forex, etc.) using deterministic technical analysis modules, statistical validation, and an AI-driven multi-agent analyst team.

## Architecture

The system is built in phases. The current state represents Phase 1: Foundation.

### Project Structure
- `data/`: Local storage for SQLite DB and historical market data.
- `src/core/`: Application core, configuration, logging.
- `src/data_providers/`: Market data provider abstractions.
- `src/strategies/`: Independent strategy modules.
- `src/analysis/`: Agents and regime classifiers.
- `tests/`: Automated tests.

## Setup

1. **Create Virtual Environment:**
   `python -m venv venv`
2. **Activate Virtual Environment:**
   - Windows: `venv\Scripts\activate`
   - Linux/Mac: `source venv/bin/activate`
3. **Install Requirements:**
   `pip install -r requirements.txt`
4. **Environment Variables:**
   Copy `.env.example` to `.env` and fill in the required values. DO NOT use keys with trading permissions.

## Health Check
Run `python health_check.py` to verify the environment.

## Phase 1 Status
- [x] Project structure initialized
- [x] Python environment configured
- [x] Logging & DB foundation (Planned)
- [x] Minimal health-check script created
- [x] Initial automated tests
