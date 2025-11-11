# Property Analytics Platform 2025

Minimal scaffold for a Swiss real-estate analytics platform (2025 stack).

- API: FastAPI (health and empty routers wired)
- AI engine: stubs for Claude client, agents, RAG
- Analytics engine: stubs for DuckDB and metrics
- Data pipeline: stubs for ingestion and pgvector management
- Semantic layer: placeholders for dbt and Cube.js
- Deployment: render.yaml and helper scripts

Run locally:

```bash
pip install -r requirements.txt
uvicorn api.app:app --host 0.0.0.0 --port 8000
```


