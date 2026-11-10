# API reference

FastAPI generates the detailed OpenAPI schema at `/openapi.json` and interactive docs at `/docs`.

- `GET /api/health`
- `GET, POST /api/projects`; `GET, DELETE /api/projects/{id}`
- `POST, GET /api/projects/{id}/documents`; `GET /api/documents/{id}`
- `POST /api/projects/{id}/analyze` with `{ "mode": "knowledge-audit", "question": "..." }`
- `POST /api/projects/{id}/resurrect`
- `GET /api/projects/{id}/analysis`, `/graph`, `/timeline`, `/integrity`, `/knowledge-debt`
- `POST /api/projects/{id}/impact-analysis`, `/handover`
- `GET /api/reports/{id}`, `/export`
- `POST /api/demo/seed`
- `GET /api/integrations/uliya/status`, `/capabilities`

List projects accepts `limit` (1–100) and `offset`. Uploads accept a multipart `files` list. Unsupported types and over-limit files are returned per file with explicit status instead of being silently skipped. Analysis requires at least one processed document.
