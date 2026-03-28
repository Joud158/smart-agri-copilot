# Architecture-to-Rubric Mapping

## 1. Two independent agent systems
- **Agent System A:** `agent-system-a/` uses **LangGraph** and owns orchestration.
- **Agent System B:** `agent-system-b/` is a separate FastAPI service with its own logic and its own dependency set.
- Communication happens through **HTTP** only.

## 2. RAG pipeline
- Data is stored under `data/`
- `scripts/ingest_to_qdrant.py` performs:
  - file loading
  - metadata parsing
  - heading-aware chunking
  - embedding
  - upload to Qdrant
- Retrieval is handled in `agent-system-a/app/rag/retriever.py`

## 3. MCP server
- `mcp-server/` is a standalone MCP-capable service
- Canonical tools:
  - `analyze_soil`
  - `calculate_fertilizer`
  - `estimate_water_usage`
- REST bridge is included for easy integration from Agent A

## 4. Supervisor and specialists
Agent A uses:
- supervisor
- crop specialist
- pest specialist
- market specialist
- irrigation bridge
- soil bridge
- synthesizer

## 5. API layer
- Agent A: `/chat`, `/chat/stream`, `/health`
- Agent B: `/chat`, `/health`
- MCP bridge: `/bridge/*`, `/health`
- Session history persists through SQLite

## 6. Guardrails
- input scope check
- domain restriction
- disclaimer injection
- timeout-based service calls
- graceful degradation when dependencies fail

## 7. Docker and deployment
- one `docker-compose.yml`
- one Dockerfile per service
- public and internal networks separated

## 8. CI/CD
- CI validates Python syntax, frontend build, and Docker builds
- CD publishes images to GHCR on `main` or tags
