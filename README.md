# InferFlow — LLM Inference Logging & Ingestion System

A full-stack, production-ready system for logging, ingesting, and observing LLM inference calls.  
Built with **FastAPI · React · PostgreSQL · Redis · Nginx · Docker Compose · Kubernetes**.

> **Live Demo:** [https://full-stack-seven-kappa.vercel.app](https://full-stack-seven-kappa.vercel.app)  
> **GitHub:** [https://github.com/Thanush-41/InferFlow](https://github.com/Thanush-41/InferFlow)

---

## Feature Coverage

| Requirement | Status | Implementation |
|---|---|---|
| Multi-turn chatbot | ✅ | Gemini 2.5 Flash + OpenAI GPT-4.1 |
| Conversational context | ✅ | Sliding window — configurable, default 20 messages |
| Simple UI | ✅ | React 18 + TypeScript + TailwindCSS |
| Lightweight SDK wrapper | ✅ | Captures model, provider, latency, tokens, timestamps, status, previews, session ID |
| Near real-time log ingestion | ✅ | Redis `LPUSH` → `BRPOP` pipeline — fire-and-forget, zero inference latency added |
| Ingestion validation & parsing | ✅ | Pydantic-validated payloads; malformed logs dropped cleanly |
| Database storage | ✅ | PostgreSQL 16 — 3-table normalised schema |
| Multi-provider support | ✅ | Gemini, OpenAI — extensible `BaseLLMProvider` abstract class |
| Streaming responses | ✅ | SSE endpoint with time-to-first-token (TTFT) tracking |
| Latency / Throughput / Errors dashboards | ✅ | P95/P99 latency, RPM, error rate, per-provider breakdown, time-series charts |
| Docker Compose one-command setup | ✅ | `docker-compose up --build` — 5 services, zero config |
| Event-based architecture | ✅ | Redis queue fully decouples SDK log production from ingestion processing |
| PII redaction | ✅ | Regex-based — email, phone, SSN, credit card, IP address, date of birth |
| Cancel / List / Resume conversations | ✅ | Full lifecycle management in UI and API |
| Self-hosted Kubernetes | ✅ | `k8s/` — Namespace, Deployments, Services, HPA, PVC, Ingress, deploy script |

---

## Architecture Overview

```
+------------------------------------------------------------------+
|                        Nginx  (port 80)                          |
|            /  ->  frontend:3000       /api/  ->  backend:8000    |
+------------------+-----------------------------------+-----------+
                   |                                   |
       +-----------+-----------+           +-----------+-----------+
       |     React Frontend    |           |     FastAPI Backend    |
       |  Chat / Convs / Dash  |           |                       |
       +-----------------------+           |  Chat API             |
                                           |  Conversations API    |
                                           |  Dashboard API        |
                                           |  Ingestion API        |
                                           |                       |
                                           |  +------------------+ |
                                           |  |   LLM Wrapper    | |
                                           |  | Gemini / OpenAI  | |
                                           |  | + Inference Log  | |
                                           |  +--------+---------+ |
                                           +-----------|-----------+
                                                       | LPUSH (non-blocking)
                                           +-----------+-----------+
                                           |     Redis Queue       |
                                           |  inference_logs list  |
                                           +-----------+-----------+
                                                       | BRPOP
                                           +-----------+-----------+
                                           |   Ingestion Worker    |
                                           |  Validate (Pydantic)  |
                                           |  PII Redact           |
                                           |  Batch INSERT         |
                                           +-----------+-----------+
                                                       |
                                           +-----------+-----------+
                                           |     PostgreSQL 16     |
                                           |  conversations        |
                                           |  chat_messages        |
                                           |  inference_logs       |
                                           +-----------------------+
```

---

## Quick Start

### Prerequisites
- **Docker Desktop >= 4.x** with Compose v2
- **Gemini API key** — [get one free](https://aistudio.google.com/app/apikey)

### One-Command Setup (Docker)

```bash
# 1. Clone
git clone https://github.com/Thanush-41/InferFlow.git
cd InferFlow

# 2. Configure — minimum required:
cp .env.example .env
#   GEMINI_API_KEY=your-key-here
#   POSTGRES_PASSWORD=your-secure-password

# 3. Start all 5 services
docker-compose up --build
```

| Service | URL |
|---|---|
| Full app (via Nginx) | http://localhost |
| Backend API + Swagger | http://localhost:8000/docs |
| Frontend (direct) | http://localhost:3000 |

> **Port conflict?** Override any port in `.env` without editing compose files:
> ```env
> BACKEND_PORT=8001
> FRONTEND_PORT=3001
> POSTGRES_PORT=5433
> REDIS_PORT=6380
> NGINX_PORT=8090
> ```

### Local Development (without Docker)

```bash
# Terminal 1 — Backend
cd backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Terminal 2 — Frontend
cd frontend
npm install
npm run dev                      # -> http://localhost:5173
```

### Kubernetes (Self-Hosted)

```bash
# Prerequisites: kubectl configured, nginx-ingress-controller installed on cluster

# 1. Set your secrets
#    Edit k8s/config.yaml -> replace GEMINI_API_KEY placeholder in the Secret

# 2. One-command deploy
chmod +x k8s/deploy.sh
./k8s/deploy.sh

# 3. Point DNS: inferflow.example.com -> your cluster ingress IP
```

The `k8s/` directory contains:

| File | Purpose |
|---|---|
| `namespace.yaml` | `inferflow` namespace isolation |
| `config.yaml` | Kubernetes Secret + ConfigMap for all env vars |
| `postgres.yaml` | PostgreSQL Deployment + Service + 5 Gi PVC |
| `redis.yaml` | Redis Deployment + Service with memory limits |
| `backend.yaml` | Backend Deployment (2 replicas) + Service + HPA (2-10 pods at 70% CPU) |
| `frontend.yaml` | Frontend Deployment (2 replicas) + Service |
| `ingress.yaml` | Nginx Ingress — path routing, TLS termination |
| `deploy.sh` | Orchestrated deploy script with readiness waits |

---

## Database Schema

### `conversations`

| Column | Type | Notes |
|---|---|---|
| `id` | VARCHAR(36) | UUID primary key |
| `title` | VARCHAR(255) | Auto-set from first 50 chars of first message |
| `status` | VARCHAR(20) | `active` / `cancelled` / `completed` |
| `created_at` | TIMESTAMP | — |
| `updated_at` | TIMESTAMP | Updated on every message |

### `chat_messages`

| Column | Type | Notes |
|---|---|---|
| `id` | VARCHAR(36) | UUID PK |
| `conversation_id` | VARCHAR(36) FK | Indexed |
| `role` | VARCHAR(20) | `user` / `assistant` / `system` |
| `content` | TEXT | Raw message — kept for debugging |
| `content_redacted` | TEXT | PII-scrubbed copy — what is audited |
| `created_at` | TIMESTAMP | — |

### `inference_logs`

| Column | Type | Notes |
|---|---|---|
| `id` | VARCHAR(36) | UUID PK |
| `conversation_id` | VARCHAR(36) FK | Indexed |
| `request_id` | VARCHAR(36) | Unique per LLM call, not per message |
| `model` | VARCHAR(100) | e.g. `gemini-2.5-flash` |
| `provider` | VARCHAR(50) | `gemini` / `openai` |
| `request_timestamp` | TIMESTAMP | When call was initiated |
| `response_timestamp` | TIMESTAMP | When response completed |
| `latency_ms` | FLOAT | End-to-end wall-clock latency |
| `input_tokens` | INT | Prompt token count |
| `output_tokens` | INT | Completion token count |
| `total_tokens` | INT | Combined total |
| `status` | VARCHAR(20) | `success` / `error` |
| `error_message` | TEXT | Populated on failure, null otherwise |
| `input_preview` | TEXT | First 500 chars, PII-redacted |
| `output_preview` | TEXT | First 500 chars, PII-redacted |
| `is_streaming` | BOOLEAN | True when SSE was used |
| `time_to_first_token_ms` | FLOAT | TTFT — streaming only |
| `extra_metadata` | JSON | Extensible catch-all for future fields |

**Key schema decisions:**

- **`extra_metadata` not `metadata`** — SQLAlchemy reserves `metadata` on every mapped class; using the standard name raises `InvalidRequestError` at startup.
- **`content` + `content_redacted` side-by-side** — preserves raw messages for internal debugging while the audited path always reads the scrubbed column.
- **`request_id` separate from message ID** — a single assistant turn may produce multiple LLM calls (retries, tool use). Tracking them separately is more accurate.
- **No DB-level foreign key constraints** — avoids cascading delete issues across async sessions; referential integrity is enforced at the application layer.

---

## Configuration Reference

All config is driven by environment variables — nothing is hardcoded in source.

| Variable | Default | Required | Description |
|---|---|---|---|
| `GEMINI_API_KEY` | — | Yes | Gemini API key |
| `OPENAI_API_KEY` | — | No | OpenAI API key (optional provider) |
| `DATABASE_URL` | — | Yes | asyncpg DSN for async SQLAlchemy |
| `DATABASE_URL_SYNC` | — | Yes | psycopg2 DSN (used by Alembic) |
| `REDIS_URL` | — | Yes | Redis DSN (`redis://` or `rediss://`) |
| `POSTGRES_PASSWORD` | — | Yes | PostgreSQL password |
| `APP_ENV` | `development` | No | `development` / `production` |
| `CORS_ORIGINS` | `http://localhost:3000,...` | No | Comma-separated allowed origins |
| `DEFAULT_MODEL` | `gemini-2.5-flash` | No | Default LLM model |
| `DEFAULT_PROVIDER` | `gemini` | No | Default LLM provider |
| `DEFAULT_OPENAI_MODEL` | `gpt-4.1` | No | Default OpenAI model |
| `PREVIEW_MAX_LENGTH` | `500` | No | Max chars for input/output previews |
| `REDIS_QUEUE_KEY` | `inference_logs` | No | Redis list key for the log queue |
| `MAX_CONTEXT_MESSAGES` | `20` | No | Sliding context window size |
| `SERVERLESS_MODE` | `false` | No | Disables background worker (Vercel) |
| `BACKGROUND_WORKER_ENABLED` | `true` | No | Toggle in-process ingestion worker |
| `BACKEND_PORT` | `8000` | No | Host port mapped to backend container |
| `FRONTEND_PORT` | `3000` | No | Host port mapped to frontend container |
| `POSTGRES_PORT` | `5432` | No | Host port mapped to PostgreSQL |
| `REDIS_PORT` | `6379` | No | Host port mapped to Redis |
| `NGINX_PORT` | `80` | No | Host port mapped to Nginx |

---

## Tradeoffs

| Decision | Why | Cost |
|---|---|---|
| Redis queue over synchronous DB write | Logging never adds latency to inference path | One extra infrastructure component |
| In-process ingestion worker | Simpler deployment, no extra container | Worker and API share CPU/memory; extract to own pod for production scale |
| Regex PII redaction over Presidio/spaCy | Zero startup overhead, no ML models to ship | Lower recall on edge cases (e.g. names) |
| PostgreSQL over time-series DB | Familiar ops, single DB to manage | Needs TimescaleDB hypertables or partitioning above ~10M rows/day |
| Truncated previews (500 chars) | Keeps storage predictable | Full prompt/completion not stored — supplement with a trace store if needed |
| SSE over WebSocket | Simpler browser contract for unidirectional streaming | Not suitable for very high concurrency (>10k streams) |
| `pydantic-settings` with `extra="ignore"` | Same `.env` works for Docker and serverless without validation errors | Unknown env vars silently ignored rather than failing loudly |

---

## What I Would Improve With More Time

1. **Helm chart** — Parameterise the K8s manifests; template image tags, replica counts, resource limits
2. **Separate ingestion worker Deployment** — Independent scaling from the API; own resource limits
3. **Dead-letter queue** — Failed log payloads pushed to a Redis DLQ for forensic replay
4. **Presidio NER for PII** — ML-based entity recognition; higher recall, custom entity types
5. **Alembic migrations** — Version-controlled schema changes instead of `create_all()` on startup
6. **Authentication** — JWT / API-key middleware for multi-tenant isolation
7. **OpenTelemetry + Prometheus** — Distributed traces, `/metrics` scrape endpoint, Grafana dashboard
8. **Log retention policies** — Configurable TTL with archival to S3-compatible object storage
9. **Integration test suite** — Full pipeline tests using `testcontainers` (Postgres + Redis in CI)
10. **Streaming cancel propagation** — Forward cancel signal to the active LLM stream via `asyncio.Event`

---

## API Reference

### Chat

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/chat/send` | Send message, receive full JSON response |
| `POST` | `/api/chat/send/stream` | Send message, receive SSE stream |

### Conversations

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/conversations/` | List all conversations (filter by `?status=`) |
| `GET` | `/api/conversations/:id` | Get conversation with full message history |
| `POST` | `/api/conversations/:id/cancel` | Mark conversation as cancelled |
| `POST` | `/api/conversations/:id/resume` | Reactivate a cancelled conversation |
| `DELETE` | `/api/conversations/:id` | Permanently delete conversation |

### Ingestion

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/ingest/logs` | Direct single-log ingestion |
| `POST` | `/api/ingest/logs/batch` | Batch log ingestion (up to 100 items) |
| `GET` | `/api/ingest/queue/status` | Redis queue depth and worker status |

### Dashboard

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/dashboard/metrics` | Aggregate stats — total requests, avg/P95/P99 latency, error rate, RPM, tokens |
| `GET` | `/api/dashboard/latency` | Latency time-series in 5-minute buckets |
| `GET` | `/api/dashboard/throughput` | Request throughput in 5-minute buckets |
| `GET` | `/api/dashboard/errors` | Recent error log entries |
| `GET` | `/api/dashboard/providers` | Per-provider breakdown |
| `GET` | `/health` | Health check |

All dashboard endpoints accept an optional `?hours=N` query param (default: 24).

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend API | Python 3.11 · FastAPI 0.115 · SQLAlchemy 2.0 (async) · Pydantic 2.9 |
| LLM SDKs | `google-genai` 1.14 (new async Client API) · `openai` 1.51 |
| Event Queue | Redis 7 · `redis[hiredis]` 5.1 |
| Database | PostgreSQL 16 · asyncpg 0.29 |
| Frontend | React 18 · TypeScript · Vite 5 · TailwindCSS · Lucide icons |
| Proxy | Nginx 1.27 |
| Containers | Docker Compose v2 · Kubernetes 1.28+ |
| Deployment | Vercel (serverless) · self-hosted K8s |
