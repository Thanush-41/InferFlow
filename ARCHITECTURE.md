# Architecture Notes — InferFlow

Detailed design decisions, data flows, and operational characteristics for the
LLM Inference Logging & Ingestion System.

---

## System Overview

InferFlow implements an event-driven inference observability pipeline:

```
User Request
    |
    v
FastAPI Backend
    |-- Chat API         (conversation management, message persistence)
    |-- LLM Wrapper      (Gemini / OpenAI SDK with transparent instrumentation)
    |-- Ingestion API    (direct log submission endpoint)
    |-- Dashboard API    (aggregation queries over inference_logs)
    |
    +-- Redis LPUSH -->  Redis Queue  -->  BRPOP  -->  Ingestion Worker
                                                            |
                                                       Pydantic validate
                                                       PII redact
                                                       PostgreSQL INSERT
```

The critical invariant: **logging never touches the hot path**.  
The `LPUSH` call in the SDK logger is O(1) and fire-and-forget. If Redis is
unavailable, the exception is swallowed and inference continues normally.

---

## Ingestion Flow (Step by Step)

```
1.  POST /api/chat/send  (or /stream)
        |
2.  Chat API loads or creates Conversation row in PostgreSQL (synchronous)
        |
3.  LLM Wrapper.generate() called
        |
4.  SDK Logger records:
        request_id        = uuid4()
        request_timestamp = utcnow()
        model / provider  = from config
        |
5.  HTTP call to Gemini / OpenAI
        |
6.  Response returned to caller immediately
        |
7.  SDK Logger.end_request() calculates:
        latency_ms              = now - request_timestamp
        time_to_first_token_ms  = (streaming only)
        input/output previews   = content[:500]
        status                  = success / error
        |
8.  Redis LPUSH "inference_logs" <json_payload>    <- O(1), non-blocking
        |
9.  Response delivered to frontend
```

```
Separately, concurrently:

10. Ingestion Worker (asyncio task) BRPOP "inference_logs" (blocking, 1s timeout)
        |
11. JSON decoded -> Pydantic InferenceLogCreate validated
        |  (malformed payload -> logged as error, worker continues)
        |
12. PII redactor scrubs input_preview + output_preview
        |  Patterns: email, phone, SSN, credit card, IP, date of birth
        |
13. SQLAlchemy INSERT into inference_logs
        |
14. Worker loops back to step 10
```

---

## Logging Strategy

### What Gets Logged

| Field | Source | Notes |
|---|---|---|
| `model` / `provider` | Config at call time | Immutable after the call |
| `request_timestamp` | SDK — before HTTP call | Wall clock, UTC |
| `response_timestamp` | SDK — after last byte received | Wall clock, UTC |
| `latency_ms` | Derived | `(response - request).total_seconds() * 1000` |
| `time_to_first_token_ms` | SDK — streaming only | Time to first yielded chunk |
| `input_tokens` / `output_tokens` | Provider response metadata | Not all providers return these |
| `status` | SDK — exception vs. success | `success` or `error` |
| `error_message` | Exception message | Truncated to 1000 chars |
| `input_preview` | First 500 chars of prompt | PII-redacted before storage |
| `output_preview` | First 500 chars of response | PII-redacted before storage |
| `conversation_id` | Call context | Ties log to chat session |
| `request_id` | `uuid4()` per LLM call | Unique even for retries |
| `extra_metadata` | Provider-specific | JSON blob; future extensibility |

### Design Principles

- **Non-blocking**: `LPUSH` is O(1). No lock, no wait, no DB round-trip in the inference path.
- **Structured payloads**: Pydantic `InferenceLogCreate` validates every field with types. Malformed payloads are dropped without crashing the worker.
- **Privacy-first**: PII redaction runs in the worker before `INSERT`. The raw preview never touches the database.
- **Truncated storage**: 500-char previews balance debuggability against storage costs. Full prompts can be supplemented with an external trace store (e.g. Langfuse) if needed.
- **Separate `request_id`**: A single user message may trigger multiple LLM calls (retries, tool use). Tracking them per-call is more accurate than per-message.

### PII Redaction Patterns

```python
PATTERNS = [
    (r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL]'),
    (r'\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b',                    '[PHONE]'),
    (r'\b\d{3}-\d{2}-\d{4}\b',                                 '[SSN]'),
    (r'\b(?:\d{4}[-\s]?){3}\d{4}\b',                           '[CREDIT_CARD]'),
    (r'\b(?:\d{1,3}\.){3}\d{1,3}\b',                           '[IP_ADDRESS]'),
    (r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b',                    '[DATE]'),
]
```

Known limitation: name-based PII (e.g. "John Smith") requires NER (Presidio/spaCy).
Regex approach was chosen to avoid ML model startup overhead.

---

## Scaling Considerations

### Current Capacity (Single Node)

| Component | Approximate Ceiling | Bottleneck |
|---|---|---|
| FastAPI backend | ~1,000 concurrent users | Python GIL on CPU-bound ops |
| Ingestion Worker | ~500 logs/sec | DB write throughput |
| PostgreSQL | ~1,000 writes/sec | Disk I/O |
| Redis Queue | ~100,000 LPUSH/sec | Near-unlimited for this use case |
| Dashboard queries | ~50 concurrent | Full-table scan on inference_logs |

### Horizontal Scaling Path

```
Step 1 — Multiple Backend Instances
    FastAPI is stateless -> scale behind any load balancer
    Each instance runs its own in-process ingestion worker
    All workers share the same Redis queue (safe; BRPOP is atomic)

Step 2 — Extract Ingestion Workers
    Move worker to a separate Deployment in Kubernetes
    Scale workers independently from the API
    Enables different resource profiles (worker = memory, API = CPU)

Step 3 — Database Read/Write Split
    Dashboard queries -> read replica (eventual consistency acceptable)
    Inference log writes -> primary
    Chat message writes -> primary

Step 4 — PostgreSQL Partitioning
    Range partition inference_logs on request_timestamp (monthly)
    DROP old partitions for retention without expensive DELETEs
    TimescaleDB hypertables as drop-in upgrade

Step 5 — Redis High Availability
    Redis Sentinel or Redis Cluster for HA
    AWS ElastiCache / Upstash as managed options
```

### Kubernetes HPA (Configured in `k8s/backend.yaml`)

```yaml
minReplicas: 2
maxReplicas: 10
targetCPUUtilizationPercentage: 70
```

At 70% CPU the HPA adds pods. With stateless FastAPI this is safe at any time.

---

## Failure Handling

### Failure Mode Matrix

| Failure | Immediate Effect | Recovery |
|---|---|---|
| LLM API timeout | Exception caught in wrapper; `status=error` logged to queue | Inference returns HTTP 500 to user; log stored for analysis |
| LLM API rate limit | Same as timeout | Retry with exponential backoff (not yet implemented) |
| Redis `LPUSH` failure | Exception swallowed in SDK logger | Inference continues; log is **lost** (acceptable for observability data) |
| Ingestion Worker crash | In-process asyncio task terminates | Items stay in Redis queue; picked up on next startup |
| PostgreSQL `INSERT` failure | Worker catches `SQLAlchemyError`; retries with 0.5s backoff | Queue acts as durable buffer; no data lost while Redis is up |
| Pydantic validation failure | Payload dropped; error logged | Worker continues; bad payload never reaches DB |
| Database connection lost | Worker retries; backend returns 503 on new requests | Reconnects automatically via SQLAlchemy pool |
| Redis connection lost | Queue unavailable; logs dropped | Worker restarts connection; catch-up resumes when Redis recovers |
| Client disconnects mid-stream | Partial SSE stream cut | Conversation ID preserved; user can resume from last message |
| Cold start (serverless) | DB/Redis connect in lifespan; each step wrapped in try-except | Partial degradation rather than total startup failure |

### Guarantees

- **At-least-once log delivery** — once an item is in Redis, it will be processed eventually (worker restart, DB recovery)
- **Best-effort when Redis is down** — inference works; logs are dropped; no user-facing impact
- **Conversation integrity** — chat messages are written synchronously in the request path, not via queue; never lost
- **No data corruption** — Pydantic validates every log; invalid payloads are dropped, not partially stored
- **Idempotent startup** — `create_all()` is safe to run on every cold start; existing tables are not modified

---

## Event-Based Architecture

Redis is used as a lightweight event bus between the SDK logger (producer) and the ingestion worker (consumer):

```
Producer                Queue              Consumer
--------                -----              --------
SDK Logger              Redis List         Ingestion Worker
  |                      |                   |
  |-- LPUSH payload -->  |                   |
  |                      |<-- BRPOP (block) -|
  |                      |-- payload ------->|
  |                      |                   |-- Validate
  |                      |                   |-- Redact
  |                      |                   |-- INSERT
```

**Why a list not pub/sub?**

Redis pub/sub is ephemeral — subscribers miss messages that arrive while they are down.
A list persists until consumed, acting as a durable buffer. This matches the
at-least-once delivery requirement.

**Why BRPOP not polling?**

`BRPOP` blocks on the server side until an item arrives (or timeout). This means zero
CPU usage when the queue is empty, versus busy-polling which wastes cycles.

**Future Extensions**

| Extension | Mechanism |
|---|---|
| Real-time dashboard updates | Pub/sub channel alongside the list; dashboard subscribes |
| Dead-letter queue | On `INSERT` failure, `RPUSH` to `inference_logs:dlq` |
| Event replay | Re-push DLQ items to main list after fixing root cause |
| Multi-tenant routing | Separate list per tenant key; worker selects by priority |
| Alerting on error spike | Secondary consumer reads same queue via `LRANGE`; triggers webhook |

---

## Vercel Serverless Architecture

The live demo runs on Vercel's hobby plan. Key adaptations:

| Problem | Solution |
|---|---|
| No persistent background tasks | `SERVERLESS_MODE=true` disables the ingestion worker; logs ingested synchronously |
| 10-second function timeout | SSE streaming disabled (`stream=false`); non-streaming chat used |
| ASGI not supported natively | `a2wsgi.ASGIMiddleware` wraps FastAPI; `BaseHTTPRequestHandler` bridges to Vercel's runtime |
| Connection pool unusable | `NullPool` for asyncpg; new connection per request |
| Cold start validation errors | `pydantic-settings` with `extra="ignore"` allows Docker-specific env vars to coexist |
| Static files on same domain | Root `package.json` + `@vercel/static-build` serves `frontend/dist/` at `/` |

### a2wsgi Response Pattern

A critical bug encountered: `a2wsgi.ASGIMiddleware` returns a lazy generator.
`start_response` (which sets the status code) is only called during iteration.
The fix:

```python
# WRONG — status_holder is empty here; response_body is never consumed
status_code = int(status_holder[0].split(" ")[0])  # KeyError!
response_body = b"".join(result)

# CORRECT — exhaust the generator first, THEN read status
response_body = b"".join(chunk for chunk in result if chunk)
status_code = int(status_holder[0].split(" ", 1)[0]) if status_holder else 500
```

---

## Data Flow Diagrams

### Chat Message (Non-Streaming)

```
Browser
  POST /api/chat/send
        |
        v
  FastAPI: load/create Conversation
        |
        v
  Store user ChatMessage (sync)
        |
        v
  LLMWrapper.generate(messages)
        |
        +---- Redis LPUSH (async, fire-and-forget)
        |
        v
  Store assistant ChatMessage (sync)
        |
        v
  Return JSON { conversation_id, message, ... }
        |
        v
Browser renders assistant message
```

### Dashboard Metrics Query

```
Browser
  GET /api/dashboard/metrics?hours=24
        |
        v
  FastAPI Dashboard Router
        |
        v
  SQLAlchemy async query:
    SELECT
      COUNT(*),
      AVG(latency_ms),
      PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY latency_ms),
      PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY latency_ms),
      SUM(total_tokens),
      SUM(CASE WHEN status='error' THEN 1 ELSE 0 END)
    FROM inference_logs
    WHERE request_timestamp > NOW() - INTERVAL '24 hours'
        |
        v
  Return aggregated JSON
        |
        v
Browser renders metric cards + charts
```
