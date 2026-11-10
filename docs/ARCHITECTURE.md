# Architecture

The frontend is a Vite React/TypeScript single-page application. In development Vite forwards `/api` to FastAPI; in Compose nginx proxies that prefix to the backend. FastAPI validates requests, extracts allowed document types, stores source text and chunks through SQLAlchemy, then creates deterministic report payloads with source references. SQLite is the local default; set a PostgreSQL `DATABASE_URL` for another SQLAlchemy-supported deployment.

Project deletion is explicit and removes associated documents, chunks, reports, and stored uploads. Analysis reports are persisted as JSON snapshots. Graph nodes and edges are computed from the project's source documents and are not native graph storage.

## Analysis modes

All modes use processed text only. Project resurrection produces evidence-cited claim candidates, decisions, requirements, questions, a transparent inventory score, and potential conflicts. Decision time machine sorts by source insertion metadata. Integrity returns possible conflicting requirement candidates. Impact analysis uses token overlap and requires human confirmation. Knowledge audit reports a labeled coverage indicator. Gravitational extract lists repeated capitalized terms. Topological summarize groups statements by source document. Matrix organize groups candidates by document and classification.

## Model provider boundary

`AIProvider` defines structured JSON generation, with optional Ollama and OpenAI-compatible adapters. The current analysis path does not invoke a model provider. This avoids presenting model output as source-verified evidence before schema, retry, and evidence validation controls are integrated.
