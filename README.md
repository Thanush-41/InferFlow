# LLM Inference Logging & Ingestion System

A full-stack, production-ready inference logging and ingestion system for LLM applications.  
Built with FastAPI · React · PostgreSQL · Redis · Nginx · Docker Compose.

---

## Features

| Requirement | Status | Detail |
|---|---|---|
| Multi-turn chatbot | ✅ | Gemini 2.5 Flash + OpenAI GPT-4.1 |
| Conversational context | ✅ | Sliding window (configurable, default 20 msgs) |
| Simple UI | ✅ | React + TailwindCSS |
| Lightweight SDK wrapper | ✅ | Transparent instrumentation — latency, tokens, timestamps, status, previews |
| Near real-time log ingestion | ✅ | Redis LPUSH → BRPOP pipeline |
| Ingestion validation & parsing | ✅ | Pydantic-validated payloads |
| PostgreSQL storage | ✅ | 3-table schema |
| Multi-provider support | ✅ | Gemini, OpenAI — extensible base class |
| Streaming responses | ✅ | Server-Sent Events (SSE) with TTFT tracking |
| Latency / Throughput / Errors dashboards | ✅ | P95/P99 latency, RPM, error rate, per-provider stats |
| Docker Compose one-command setup | ✅ | `docker-compose up --build` |
| Event-based architecture | ✅ | Redis queue decouples logging from inference path |
| PII redaction | ✅ | Regex-based — email, phone, SSN, credit card, IP, dates |
| Cancel / List / Resume conversations | ✅ | Full conversation lifecycle in UI + API |

---

## Quick Start

### Prerequisites

- **Docker & Docker Compose** (Docker Desktop ≥ 4.x)
- **Gemini API key** ([get one free](https://aistudio.google.com/app/apikey))

### One-Command Setup

```bash
# 1. Clone and configure
git clone <repo-url>
cd full-stack
cp .env.example .env
```

Edit `.env` — at minimum set:
```env
GEMINI_API_KEY=your-key-here
POSTGRES_PASSWORD=your-secure-password
```

```bash
# 2. Start all 5 services
docker-compose up --build

# 3. Open in browser
# Full app (via nginx):  http://localhost:80
# Backend API + Swagger: http://localhost:8000/docs
# Frontend direct:       http://localhost:3000
```

> **Port conflicts?** Override any host port in `.env` — no compose file edits needed:
> ```env
> BACKEND_PORT=8001
> FRONTEND_PORT=3001
> POSTGRES_PORT=5433
> REDIS_PORT=6380
> NGINX_PORT=8090
> ```

### Local Development (without Docker)

```bash
# Backend
cd backend
python -m venv .venv && source .venv/bin/activate   # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Frontend
cd frontend
npm install
npm run dev
```

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                     Nginx (port 80)                     │
│          /  → frontend:3000    /api/ → backend:8000     │
└───────────────────┬──────────────────────┬──────────────┘
                    │                      │
        ┌───────────▼──────────┐   ┌──────▼──────────────┐
        │   React Frontend     │   │   FastAPI Backend    │
        │  Chat · Convs · Dash │   │                      │
        └──────────────────────┘   │  ┌───────────────┐   │
                                   │  │  Chat API      │   │
                                   │  │  Convs API     │   │
                                   │  │  Dashboard API │   │
                                   │  │  Ingest API    │   │
                                   │  └──────┬────────┘   │
                                   │         │             │
                                   │  ┌──────▼────────┐   │
                                   │  │  LLM Wrapper  │   │
                                   │  │  (SDK)        │   │
                                   │  │  + Logger     │   │
                                   │  └──────┬────────┘   │
                                   └─────────┼─────────────┘
                                             │ fire-and-forget
                                   ┌─────────▼─────────┐
                                   │   Redis Queue     │
                                   │  (LPUSH / BRPOP)  │
                                   └─────────┬─────────┘
                                             │
                                   ┌─────────▼─────────┐
                                   │ Ingestion Worker  │
                                   │  Validate (Pydantic)│
                                   │  PII Redact       │
                                   │  Store            │
                                   └─────────┬─────────┘
                                             │
                                   ┌─────────▼─────────┐
                                   │   PostgreSQL 16   │
                                   │  conversations    │
                                   │  chat_messages    │
                                   │  inference_logs   │
                                   └───────────────────┘
```

---

## Configuration

All settings are driven by environment variables — nothing is hardcoded in source.

| Variable | Default | Description |
|---|---|---|
| `GEMINI_API_KEY` | *(required)* | Gemini API key |
| `OPENAI_API_KEY` | *(optional)* | OpenAI API key |
| `DATABASE_URL` | *(required)* | asyncpg DSN |
| `REDIS_URL` | *(required)* | Redis DSN |
| `POSTGRES_PASSWORD` | *(required)* | DB password |
| `CORS_ORIGINS` | `http://localhost:3000,...` | Comma-separated allowed origins |
| `DEFAULT_MODEL` | `gemini-2.5-flash` | Default LLM model |
| `DEFAULT_PROVIDER` | `gemini` | Default LLM provider |
| `DEFAULT_OPENAI_MODEL` | `gpt-4.1` | Default OpenAI model |
| `PREVIEW_MAX_LENGTH` | `500` | Max chars stored for input/output previews |
| `REDIS_QUEUE_KEY` | `inference_logs` | Redis list key for the log queue |
| `MAX_CONTEXT_MESSAGES` | `20` | Sliding context window size |
| `BACKEND_PORT` | `8000` | Host port for the backend |
| `FRONTEND_PORT` | `3000` | Host port for the frontend |
| `POSTGRES_PORT` | `5432` | Host port for PostgreSQL |
| `REDIS_PORT` | `6379` | Host port for Redis |
| `NGINX_PORT` | `80` | Host port for Nginx |

---

## Schema Design

### `conversations`
| Column | Type | Notes |
|---|---|---|
| id | VARCHAR(36) | UUID primary key |
| title | VARCHAR(255) | Auto-set from first message (first 50 chars) |
| status | VARCHAR(20) | `active` · `cancelled` · `completed` |
| created_at | TIMESTAMP | — |
| updated_at | TIMESTAMP | Auto-updated on change |

### `chat_messages`
| Column | Type | Notes |
|---|---|---|
| id | VARCHAR(36) | UUID PK |
| conversation_id | VARCHAR(36) FK | Indexed |
| role | VARCHAR(20) | `user` · `assistant` · `system` |
| content | TEXT | Raw message |
| content_redacted | TEXT | PII-redacted copy |
| created_at | TIMESTAMP | — |

### `inference_logs`
| Column | Type | Notes |
|---|---|---|
| id | VARCHAR(36) | UUID PK |
| conversation_id | VARCHAR(36) FK | Indexed |
| request_id | VARCHAR(36) | Unique per LLM call |
| model | VARCHAR(100) | e.g. `gemini-2.5-flash` |
| provider | VARCHAR(50) | `gemini` · `openai` |
| request_timestamp | TIMESTAMP | When request was sent |
| response_timestamp | TIMESTAMP | When response completed |
| latency_ms | FLOAT | End-to-end latency |
| input_tokens | INT | Prompt token count |
| output_tokens | INT | Completion token count |
| total_tokens | INT | Total token usage |
| status | VARCHAR(20) | `success` · `error` |
| error_message | TEXT | Error details (nullable) |
| input_preview | TEXT | Truncated, PII-redacted input |
| output_preview | TEXT | Truncated, PII-redacted output |
| is_streaming | BOOLEAN | Whether SSE was used |
| time_to_first_token_ms | FLOAT | TTFT for streaming calls |
| extra_metadata | JSON | Extensible catch-all |

**Design decisions:**
- `extra_metadata` (not `metadata`) — SQLAlchemy reserves the `metadata` attribute name; renamed to avoid `InvalidRequestError` at startup
- Separate `content_redacted` alongside `content` — preserves raw message for debugging while storing scrubbed version for auditing
- `request_id` is unique per LLM call (not per message) — supports batch/multi-call patterns

---

## Architecture Notes

### Ingestion Flow

```
Chat request
  → Chat API creates/loads conversation
  → LLM Wrapper calls provider (Gemini/OpenAI)
  → SDK Logger.start_request() records timestamp + request ID
  → Response / stream returned to user immediately
  → SDK Logger.end_request() calculates latency, truncates previews, builds payload
  → Redis LPUSH (O(1), non-blocking, fire-and-forget)
  → Ingestion Worker (BRPOP, runs in-process as asyncio task)
     → Pydantic validates payload
     → PII redactor scrubs previews
     → INSERT into inference_logs
```

### Logging Strategy

- **Non-blocking**: `LPUSH` is O(1); logging never adds latency to the user-facing response
- **At-least-once delivery**: Redis queue survives transient backend restarts; items remain until consumed
- **Structured payloads**: Pydantic validates every log before storage — malformed logs are dropped with error logging rather than crashing the worker
- **Truncated previews**: Input/output stored up to `PREVIEW_MAX_LENGTH` chars (default 500) — balances debuggability vs storage
- **PII before persistence**: Redaction happens in the worker, not the LLM path — redacted version goes to DB, raw version is never persisted

### Scaling Considerations

| Layer | Current | Path to Scale |
|---|---|---|
| Backend | Single process | Stateless FastAPI → horizontal scale behind load balancer |
| Ingestion Worker | In-process asyncio task | Extract to separate container; multiple workers share one Redis queue |
| Redis Queue | Single node | Redis Cluster or AWS ElastiCache for HA |
| PostgreSQL | Single node | Read replicas for dashboard; TimescaleDB hypertables for time-series at high volume |
| Streaming | SSE per connection | WebSocket pool or managed streaming for >10k concurrent streams |

### Failure Handling

| Failure | Behavior |
|---|---|
| LLM API error | Caught in wrapper → `status=error` logged → HTTP 500 returned to user |
| Redis unavailable | Logger silently swallows exception → inference succeeds, log is lost (acceptable) |
| Worker crashes | Unprocessed items remain in Redis queue → picked up on restart |
| Database unavailable | Worker retries with 0.5s backoff; queue acts as durable buffer |
| Invalid log payload | Pydantic validation error → log dropped, error printed → worker continues |
| Client disconnects mid-stream | Partial content saved; conversation can be resumed |

---

## Tradeoffs

| Decision | Tradeoff |
|---|---|
| Redis queue vs. synchronous DB write | Adds one infrastructure component; eliminates logging latency from hot path |
| Regex PII vs. Presidio/spaCy NER | Fast zero-overhead startup, no ML models; lower recall on edge cases |
| Single in-process worker | Simpler deployment; for production, separate worker container for independent scaling |
| PostgreSQL for time-series | General-purpose, no extra ops; TimescaleDB partitioning needed above ~10M rows/day |
| Truncated previews | Saves storage; loses full context — supplement with separate trace store if needed |
| SSE over WebSocket | Simpler browser/server contract for unidirectional streaming; sufficient for chat |
| Pydantic-settings for config | All settings validated at startup with types — bad config fails fast rather than silently |

---

## What I Would Improve With More Time

1. **Kubernetes manifests** — Helm chart with HPA for backend/worker; separate Deployment for ingestion worker
2. **Dead letter queue** — Failed log payloads moved to Redis DLQ for forensic review
3. **Presidio NER for PII** — Entity recognition beyond regex; support for custom entity types
4. **Authentication** — JWT/API-key middleware for multi-tenant deployments
5. **Rate limiting** — Per-conversation and per-IP throttling with Redis token bucket
6. **Observability** — OpenTelemetry traces, Prometheus `/metrics` endpoint, Grafana dashboard
7. **Log retention policies** — Configurable TTL; archive to S3-compatible storage
8. **Alembic migrations** — Version-controlled schema migrations instead of `create_all()`
9. **Integration test suite** — Full pipeline tests with testcontainers (Postgres + Redis in CI)
10. **Streaming cancel propagation** — Cancel signal sent to active LLM stream via asyncio event

---

## API Reference

| Method | Path | Description |
|---|---|---|
| POST | `/api/chat/send` | Send message, receive full response |
| POST | `/api/chat/send/stream` | Send message, receive SSE stream |
| GET | `/api/conversations/` | List conversations (filterable by status) |
| GET | `/api/conversations/:id` | Get conversation + messages |
| POST | `/api/conversations/:id/cancel` | Cancel conversation |
| POST | `/api/conversations/:id/resume` | Resume cancelled conversation |
| DELETE | `/api/conversations/:id` | Delete conversation |
| POST | `/api/ingest/logs` | Direct single-log ingestion |
| POST | `/api/ingest/logs/batch` | Batch log ingestion |
| GET | `/api/ingest/queue/status` | Redis queue depth |
| GET | `/api/dashboard/metrics` | Aggregate metrics (total reqs, avg/P95/P99 latency, error rate, RPM) |
| GET | `/api/dashboard/latency` | Latency time-series buckets |
| GET | `/api/dashboard/throughput` | Throughput time-series buckets |
| GET | `/api/dashboard/errors` | Recent error log entries |
| GET | `/api/dashboard/providers` | Per-provider breakdown |
| GET | `/health` | Health check |

---

## Tech Stack

- **Backend**: Python 3.11, FastAPI 0.115, SQLAlchemy 2.0 (async), Pydantic 2.9, asyncpg
- **LLM SDKs**: `google-genai` 1.14 (new Client API), `openai` 1.51
- **Event Queue**: Redis 7 (`redis[hiredis]` 5.1)
- **Database**: PostgreSQL 16
- **Frontend**: React 18, TypeScript, Vite 5, TailwindCSS
- **Proxy**: Nginx 1.27
- **Containerisation**: Docker Compose v2


## Features

- **Multi-turn Chatbot** with streaming responses (Gemini, OpenAI)
- **Lightweight SDK** that transparently captures inference metadata
- **Event-based Ingestion Pipeline** via Redis queue
- **Real-time Dashboard** with latency, throughput, and error metrics
- **PII Redaction** on stored messages
- **Multi-provider Support** (Gemini, OpenAI — extensible)
- **Conversation Management** (list, cancel, resume)
- **Docker Compose** one-command setup

## Architecture Overview

```
┌─────────────┐     ┌──────────────────────────────────────┐
│   React UI  │────▶│         FastAPI Backend               │
│  (Vite/TS)  │◀────│                                      │
└─────────────┘     │  ┌─────────────┐  ┌──────────────┐  │
                    │  │  Chat API   │  │ Dashboard API │  │
                    │  └──────┬──────┘  └──────────────┘  │
                    │         │                             │
                    │  ┌──────▼──────┐                     │
                    │  │ LLM Wrapper │ (SDK)                │
                    │  │  + Logger   │                      │
                    │  └──────┬──────┘                     │
                    │         │                             │
                    └─────────┼─────────────────────────────┘
                              │ (async event)
                    ┌─────────▼─────────┐
                    │   Redis Queue     │
                    └─────────┬─────────┘
                              │
                    ┌─────────▼─────────┐
                    │ Ingestion Worker  │
                    │  - Validate       │
                    │  - PII Redact     │
                    │  - Store          │
                    └─────────┬─────────┘
                              │
                    ┌─────────▼─────────┐
                    │   PostgreSQL      │
                    │  - conversations  │
                    │  - chat_messages  │
                    │  - inference_logs │
                    └───────────────────┘
```

## Quick Start

### Prerequisites
- Docker & Docker Compose
- A Gemini API key

### One-Command Setup

```bash
# 1. Clone and configure
cp .env.example .env
# Edit .env and add your GEMINI_API_KEY

# 2. Start everything
docker-compose up --build

# 3. Open browser
# Frontend: http://localhost:3000
# Backend API: http://localhost:8000/docs
# Full app (nginx): http://localhost
```

## Schema Design

### conversations
| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| title | VARCHAR(255) | Auto-generated from first message |
| status | ENUM | active, cancelled, completed |
| created_at | TIMESTAMP | Creation time |
| updated_at | TIMESTAMP | Last activity |

### chat_messages
| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| conversation_id | UUID FK | Links to conversation |
| role | VARCHAR | user, assistant, system |
| content | TEXT | Raw message content |
| content_redacted | TEXT | PII-redacted version |
| created_at | TIMESTAMP | Message timestamp |

### inference_logs
| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| conversation_id | UUID FK | Links to conversation |
| request_id | UUID | Unique per LLM call |
| model | VARCHAR | Model name (e.g., gemini-2.0-flash) |
| provider | VARCHAR | Provider (gemini, openai) |
| request_timestamp | TIMESTAMP | When request was sent |
| response_timestamp | TIMESTAMP | When response completed |
| latency_ms | FLOAT | End-to-end latency |
| input_tokens | INT | Prompt tokens |
| output_tokens | INT | Completion tokens |
| total_tokens | INT | Total token usage |
| status | VARCHAR | success, error, cancelled |
| error_message | TEXT | Error details if failed |
| input_preview | TEXT | Truncated input (PII-redacted) |
| output_preview | TEXT | Truncated output (PII-redacted) |
| is_streaming | BOOLEAN | Whether streaming was used |
| time_to_first_token_ms | FLOAT | TTFT for streaming |
| metadata | JSON | Extensible metadata |

## Architecture Notes

### Ingestion Flow
1. User sends message → Chat API handles request
2. LLM Wrapper calls provider (Gemini/OpenAI) and instruments the call
3. SDK Logger captures timing, tokens, status metadata
4. Logger pushes structured log to Redis queue (fire-and-forget, non-blocking)
5. Ingestion Worker consumes from queue via BRPOP
6. Worker validates payload, applies PII redaction, stores to PostgreSQL
7. Dashboard API queries PostgreSQL for aggregated metrics

### Logging Strategy
- **Non-blocking**: Logging never slows down the inference path. Redis LPUSH is O(1).
- **At-least-once delivery**: Redis queue ensures logs aren't lost during transient failures
- **Structured payloads**: Pydantic validates all log entries before storage
- **Truncated previews**: Input/output stored as truncated previews (500 chars max) to manage storage
- **PII Redaction**: Applied before persistence — emails, phones, SSNs, credit cards are scrubbed

### Scaling Considerations
- **Horizontal scaling**: Backend is stateless — scale behind load balancer
- **Worker scaling**: Multiple ingestion workers can consume from the same Redis queue
- **Database**: PostgreSQL handles moderate load; for high volume, consider TimescaleDB for time-series queries or partition by date
- **Redis**: Can be clustered for high throughput; queue depth monitoring available via `/api/ingest/queue/status`
- **Streaming**: SSE keeps connections lightweight; for massive concurrent streams, consider WebSocket pooling

### Failure Handling
- **LLM call failure**: Error is logged to inference_logs with status="error", error returned to user
- **Redis unavailable**: Logger catches exceptions silently — inference continues, log is lost (acceptable tradeoff)
- **Worker crash**: Unprocessed items remain in Redis queue, picked up on restart
- **Database unavailable**: Worker retries with backoff; queue acts as buffer
- **Frontend disconnect during stream**: Partial response saved, conversation can be resumed

## Tradeoffs Made

| Decision | Tradeoff |
|----------|----------|
| Redis queue vs. direct DB write | Adds infrastructure but decouples logging from inference path |
| Regex PII redaction vs. Presidio NER | Less accurate but zero ML model overhead, faster startup |
| Single worker in-process | Simpler deployment; for production, separate worker process |
| PostgreSQL for logs | Good enough for moderate scale; TimescaleDB for high-volume |
| Truncated previews (500 chars) | Saves storage but loses full context for debugging |
| SSE over WebSocket | Simpler, sufficient for chat streaming, less client complexity |

## What I Would Improve With More Time

1. **Separate worker process** — Run ingestion worker as independent service for true horizontal scaling
2. **Dead letter queue** — Failed log processing should go to DLQ for investigation
3. **Presidio NER for PII** — Better entity recognition than regex patterns
4. **Rate limiting** — Per-user/per-conversation rate limits on the API
5. **Authentication** — JWT-based auth for multi-tenant support
6. **Observability** — OpenTelemetry traces, Prometheus metrics, Grafana dashboards
7. **Log retention policies** — Auto-archive/delete old logs based on configurable TTL
8. **Batch token counting** — Pre-compute token counts client-side for budget tracking
9. **Kubernetes manifests** — Helm charts for k8s deployment with HPA
10. **Integration tests** — Full pipeline tests with testcontainers

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | /api/chat/send | Send message (non-streaming) |
| POST | /api/chat/send/stream | Send message (streaming SSE) |
| GET | /api/conversations/ | List conversations |
| GET | /api/conversations/:id | Get conversation + messages |
| POST | /api/conversations/:id/cancel | Cancel conversation |
| POST | /api/conversations/:id/resume | Resume conversation |
| DELETE | /api/conversations/:id | Delete conversation |
| POST | /api/ingest/logs | Direct log ingestion |
| POST | /api/ingest/logs/batch | Batch log ingestion |
| GET | /api/ingest/queue/status | Queue depth |
| GET | /api/dashboard/metrics | Aggregate metrics |
| GET | /api/dashboard/latency | Latency time series |
| GET | /api/dashboard/throughput | Throughput time series |
| GET | /api/dashboard/errors | Recent errors |
| GET | /api/dashboard/providers | Per-provider stats |
| GET | /health | Health check |

## Tech Stack

- **Backend**: Python 3.11, FastAPI, SQLAlchemy (async), Pydantic
- **Frontend**: React 18, TypeScript, Vite, TailwindCSS
- **Database**: PostgreSQL 16
- **Queue**: Redis 7
- **Proxy**: Nginx
- **Containerization**: Docker Compose
