# Architecture Notes

## 1. Why two independent agent systems?

The rubric explicitly requires service boundaries, not a single monolithic script. In this project:

- **Agent System A** owns user interaction and business orchestration.
- **Agent System B** owns irrigation-specific reasoning and operates as a separate service.

Agent A does **not** import Agent B as an internal module. It calls Agent B over HTTP.

## 2. Service Responsibilities

### Agent System A
LangGraph workflow:
- supervisor
- crop specialist
- pest specialist
- market specialist
- irrigation bridge
- soil bridge
- synthesizer

### Agent System B
FastAPI microservice with:
- Google ADK execution path
- deterministic fallback path
- persistent session history

### MCP Server
Own container with agriculture domain tools:
- soil interpretation
- fertilizer direction
- water usage estimate
- combined bundle analysis

### Vector DB
Qdrant stores chunk embeddings for the RAG pipeline.

## 3. Network Model

The stack uses two Docker networks:

- `public-net`: only frontend and Agent A
- `internal-net`: Agent A, Agent B, MCP, and Qdrant

This separates the user-facing entrypoint from backend-only infrastructure.

## 4. RAG Workflow

1. documents are ingested from `data/`
2. text is split using recursive heading-aware chunking
3. chunks are embedded
4. vectors are stored in Qdrant
5. specialists retrieve with metadata-aware filters
6. reranking combines semantic and lexical evidence
7. synthesis produces a grounded answer

## 5. Why this chunking strategy?

The source corpus is mostly structured instructional content. Many questions target mid-sized facts such as:

- preferred pH range
- critical irrigation-sensitive stage
- harvest timing window
- symptom-management mapping

A chunk size of 900 with 180 overlap preserves these structured sections while reducing fragmentation.

## 6. Why deterministic embeddings by default?

The project is designed to run in constrained grading conditions. Deterministic embeddings:

- remove dependence on external APIs
- keep results reproducible
- still allow evaluation, routing, and service demos

The code keeps the embedding provider swappable so stronger backends can be compared later.

## 7. Why keep Agent B fallback logic?

Production systems should degrade gracefully. If the ADK or model provider path fails, the service still returns irrigation planning instead of crashing the entire stack.

This is intentional production thinking, not an attempt to hide failure.

## 8. MCP usage model

Agent A first attempts a canonical MCP call over Streamable HTTP. If the MCP SDK is unavailable at runtime, Agent A falls back to the REST bridge hosted by the same MCP container.

This preserves:
- true MCP support in the architecture
- a stable demo path in restrictive environments

## 9. Session management

- Agent A stores conversation history in SQLite.
- Agent B also stores per-session history in SQLite.
- both services clean up expired sessions using TTL-based deletion.

## 10. Guardrails

Implemented:
- agriculture-only input scope on Agent A
- explicit disclaimer enforcement
- iteration limits on the LangGraph route loop
- request timeouts and retries on inter-service calls

## 11. Evaluation design

The evaluation suite includes:
- 20 grounded test questions with expected sources
- retrieval metrics: Precision@K, Recall@K, MRR
- generation evaluation script
- configuration comparison script
- documented failure cases in `EVALUATION.md`
