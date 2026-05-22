# Architecture Notes

## System Design

This system implements a lightweight inference logging and ingestion pipeline for LLM applications,
following an event-driven architecture pattern.

## Ingestion Flow

```
User Request → FastAPI → LLM SDK Wrapper → Provider (Gemini/OpenAI)
                                    │
                                    ▼ (async, non-blocking)
                              Redis LPUSH
                                    │
                                    ▼
                          Ingestion Worker (BRPOP)
                                    │
                            ┌───────┼───────┐
                            ▼       ▼       ▼
                        Validate  Redact  Store
                                            │
                                            ▼
                                       PostgreSQL
```

### Key Design Decisions:

1. **Fire-and-forget logging**: The SDK logger pushes to Redis without waiting for confirmation.
   This ensures logging never adds latency to the inference path. The tradeoff is potential log loss
   if Redis is unavailable (acceptable for observability data).

2. **BRPOP consumption**: The worker uses blocking pop with timeout, ensuring efficient consumption
   without busy-waiting while allowing graceful shutdown.

3. **In-process worker**: For simplicity, the ingestion worker runs as an asyncio task within the
   FastAPI process. For production, this should be a separate service.

## Logging Strategy

### What We Log:
- Model and provider identification
- Request/response timestamps
- End-to-end latency
- Time to first token (streaming)
- Token usage (input/output/total)
- Request status and errors
- Truncated input/output previews (500 chars, PII-redacted)
- Conversation/session context

### Design Principles:
- **Zero-impact logging**: Never block or slow down the inference call
- **Structured data**: All logs pass through Pydantic validation
- **Privacy-first**: PII redaction applied before any persistence
- **Extensible metadata**: JSON column for provider-specific data

## Scaling Considerations

### Current Architecture (Single Node):
- Handles ~100-500 concurrent conversations comfortably
- PostgreSQL handles the query load for dashboard aggregations
- Redis queue depth stays near zero under normal load

### Scaling Path:
1. **Multiple backend instances** behind load balancer (stateless)
2. **Dedicated worker pool** consuming from shared Redis queue
3. **Read replicas** for dashboard queries to avoid impacting writes
4. **Time-based partitioning** on inference_logs table for query performance
5. **Redis Cluster** if queue throughput becomes a bottleneck
6. **CDN** for frontend static assets

### Bottleneck Analysis:
- **Primary**: Database write throughput under high log volume
- **Mitigation**: Batch inserts in worker, connection pooling, partitioning
- **Secondary**: Dashboard aggregation queries on large datasets
- **Mitigation**: Materialized views, pre-computed rollups, caching

## Failure Handling

| Failure Mode | Behavior | Recovery |
|--------------|----------|----------|
| LLM provider timeout | Error logged, user notified | Retry with backoff (not implemented) |
| LLM provider error | Error captured in inference_log | User sees error message |
| Redis unavailable | Log silently dropped | Inference continues normally |
| Worker crash | Items remain in Redis queue | Picked up on worker restart |
| Database unavailable | Worker fails, items stay in queue | Auto-retry when DB recovers |
| Frontend disconnect | Partial stream lost | Conversation can be resumed |
| High queue depth | Logs delayed, not lost | Workers catch up; alerts at threshold |

### Guarantees:
- **At-least-once processing** for logs in the happy path
- **Best-effort delivery** when Redis is down (graceful degradation)
- **No data corruption** — Pydantic validation rejects malformed payloads
- **Conversation integrity** — Messages stored synchronously in the request path

## Event-Based Architecture

The system uses Redis as a lightweight event bus:

```
Event Producer (SDK Logger) → Redis List → Event Consumer (Ingestion Worker)
```

Benefits:
- Decouples log production from log processing
- Natural backpressure via queue depth
- Easy to add new consumers (e.g., alerting, analytics)
- Graceful handling of processing slowdowns

Future extensions:
- Add pub/sub channels for real-time dashboard updates
- Dead letter queue for failed processing
- Event replay for reprocessing historical logs
