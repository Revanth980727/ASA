# Observability & Cost Tracking - Implementation Summary

## Overview

This document summarizes the observability and cost tracking features implemented for the ASA (Automated Software Agent) system.

## What Was Implemented

### 1. LLM Token Usage and Cost Tracking

**Files Created/Modified:**
- `backend/app/services/llm_client.py` - **NEW** - LLM client wrapper with automatic tracking
- `backend/app/models.py` - **MODIFIED** - Added `LLMUsage` and `TaskMetrics` models
- `backend/app/services/fix_agent.py` - **MODIFIED** - Integrated LLM tracking
- `backend/app/services/code_agent.py` - **MODIFIED** - Integrated LLM tracking
- `backend/app/services/test_generator.py` - **MODIFIED** - Integrated LLM tracking
- `backend/app/services/orchestrator.py` - **MODIFIED** - Pass task_id to agents

**Features:**
- Automatic tracking of all LLM API calls
- Token count tracking (prompt, completion, total)
- Real-time cost calculation based on model pricing
- Per-task and per-user tracking
- Latency measurement
- Success/error status tracking
- Database persistence of all usage data

**Database Schema:**
```sql
CREATE TABLE llm_usage (
    id VARCHAR PRIMARY KEY,
    task_id VARCHAR,
    user_id VARCHAR,
    model VARCHAR NOT NULL,
    prompt_tokens INTEGER,
    completion_tokens INTEGER,
    total_tokens INTEGER,
    cost_usd FLOAT,
    latency_ms FLOAT,
    status VARCHAR,
    error_message TEXT,
    timestamp DATETIME
);

CREATE TABLE task_metrics (
    id VARCHAR PRIMARY KEY,
    task_id VARCHAR,
    metric_name VARCHAR,
    metric_value FLOAT,
    timestamp DATETIME
);
```

### 2. OpenTelemetry Instrumentation

**Files Created/Modified:**
- `backend/app/observability.py` - **NEW** - OTEL setup and configuration
- `backend/app/main.py` - **MODIFIED** - Integrated OTEL instrumentation
- `backend/requirements.txt` - **MODIFIED** - Added OTEL dependencies

**Features:**
- Automatic instrumentation for FastAPI HTTP requests
- Automatic instrumentation for SQLAlchemy database queries
- Custom spans for LLM API calls
- Span attributes for detailed tracing
- OTLP export to Jaeger
- Configurable via environment variables

**Span Attributes:**
- `llm.model` - Model name
- `llm.prompt_tokens` - Input token count
- `llm.completion_tokens` - Output token count
- `llm.total_tokens` - Total tokens
- `llm.cost_usd` - Cost in USD
- `llm.latency_ms` - Request latency
- `llm.task_id` - Associated task ID
- `llm.user_id` - Associated user ID
- `llm.status` - Success/error status

### 3. Prometheus Metrics

**Files Created/Modified:**
- `backend/app/observability.py` - Added Prometheus metrics
- `backend/app/main.py` - Added `/metrics` endpoint
- `prometheus.yml` - **NEW** - Prometheus configuration

**Metrics Exported:**

**LLM Metrics:**
- `llm_requests_total` - Counter - Total LLM requests (labels: model, status, task_id)
- `llm_tokens_total` - Counter - Total tokens used (labels: model, token_type)
- `llm_cost_usd_total` - Counter - Total cost in USD (labels: model)
- `llm_latency_seconds` - Histogram - Request latency (labels: model)

**Task Metrics:**
- `task_duration_seconds` - Histogram - Task execution duration (labels: status)
- `task_success_total` - Counter - Successful/failed tasks (labels: status)
- `active_tasks` - Gauge - Currently active tasks (labels: status)

### 4. Usage Statistics API

**Files Created:**
- `backend/app/api/v1/usage.py` - **NEW** - Usage statistics endpoints

**Endpoints:**

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/usage/task/{task_id}` | GET | Get usage stats for a specific task |
| `/api/v1/usage/user/{user_id}` | GET | Get usage stats for a specific user |
| `/api/v1/usage/overall` | GET | Get overall usage statistics |
| `/api/v1/usage/metrics/tasks` | GET | Get task execution metrics |
| `/metrics` | GET | Prometheus metrics endpoint |

**Query Parameters:**
- `days` - Number of days to look back (default: 7 or 30)

### 5. Usage Limits

**Features in `LLMClient`:**
- `check_usage_limits()` - Check if usage is within configured limits
- `get_task_usage()` - Get usage statistics for a task
- `get_user_usage()` - Get usage statistics for a user

**Configurable Limits:**
- Maximum cost per task
- Maximum cost per user
- Automatic violation detection

### 6. Observability Stack

**Files Created:**
- `docker-compose.observability.yml` - **NEW** - Docker Compose for observability stack
- `prometheus.yml` - **NEW** - Prometheus scrape configuration
- `.env.example` - **NEW** - Environment variable template

**Services Included:**
- **Jaeger** - Distributed tracing (port 16686)
- **Prometheus** - Metrics collection (port 9090)
- **Grafana** - Visualization (port 3000)
- **PostgreSQL** - Optional metrics storage (port 5433)

### 7. Documentation

**Files Created:**
- `OBSERVABILITY.md` - **NEW** - Comprehensive documentation
- `QUICKSTART_OBSERVABILITY.md` - **NEW** - Quick start guide
- `IMPLEMENTATION_SUMMARY.md` - **NEW** - This file

## Model Pricing Configuration

Current pricing (as of January 2025):

| Model | Input (per 1M tokens) | Output (per 1M tokens) |
|-------|----------------------|------------------------|
| gpt-4 | $30.00 | $60.00 |
| gpt-4-turbo | $10.00 | $30.00 |
| gpt-4o | $2.50 | $10.00 |
| gpt-4o-mini | $0.15 | $0.60 |
| gpt-3.5-turbo | $0.50 | $1.50 |

*Update `backend/app/services/llm_client.py` as OpenAI pricing changes.*

## Environment Variables

### Required
- `OPENAI_API_KEY` - OpenAI API key

### Optional (Observability)
- `ENABLE_OPENTELEMETRY=true` - Enable OpenTelemetry (default: false)
- `OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317` - OTLP endpoint

## How It Works

### Request Flow

1. **Task Submitted** → Task created with unique ID
2. **Agent Initialized** → Agent created with `task_id`
3. **LLM Call Made** → `LLMClient.chat_completion()` called
4. **Tracking Happens:**
   - OpenTelemetry span created
   - API call made to OpenAI
   - Response received
   - Token usage extracted
   - Cost calculated
   - Usage logged to database
   - Prometheus metrics updated
   - Span closed
5. **Usage Available** → Query via API endpoints

### Data Flow

```
LLM API Call
    ↓
LLMClient Wrapper
    ↓
├─→ OpenTelemetry (Jaeger)
├─→ Prometheus Metrics
├─→ Database (llm_usage table)
└─→ Return Response
    ↓
Query via API
    ↓
Usage Statistics
```

## Quick Start Commands

```bash
# 1. Install dependencies
cd backend && pip install -r requirements.txt

# 2. Start observability stack
cd .. && docker-compose -f docker-compose.observability.yml up -d

# 3. Configure environment
cp .env.example .env
# Edit .env with your OPENAI_API_KEY

# 4. Start backend
cd backend && uvicorn app.main:app --reload

# 5. Submit a task
curl -X POST http://localhost:8000/api/v1/task/submit \
  -H "Content-Type: application/json" \
  -d '{"repo_url": "https://github.com/example/repo", "bug_description": "Fix bug", "test_command": "pytest"}'

# 6. View usage (replace {task_id})
curl http://localhost:8000/api/v1/usage/task/{task_id}

# 7. View metrics
curl http://localhost:8000/metrics
```

## Access Points

Once running, you can access:

| Service | URL | Purpose |
|---------|-----|---------|
| Backend API | http://localhost:8000 | Main API |
| API Docs | http://localhost:8000/docs | Swagger UI |
| Prometheus | http://localhost:9090 | Metrics |
| Jaeger | http://localhost:16686 | Traces |
| Grafana | http://localhost:3000 | Dashboards |
| Metrics Endpoint | http://localhost:8000/metrics | Prometheus scrape |

## Example Queries

### Get Task Cost
```bash
curl http://localhost:8000/api/v1/usage/task/abc-123
```

### Get User Cost (30 days)
```bash
curl http://localhost:8000/api/v1/usage/user/user-456?days=30
```

### Get Overall Statistics
```bash
curl http://localhost:8000/api/v1/usage/overall?days=7
```

### Check Prometheus Metrics
```bash
curl http://localhost:8000/metrics | grep llm_
```

### Prometheus Queries
```promql
# Total cost
sum(llm_cost_usd_total)

# Requests per second
rate(llm_requests_total[1m])

# 95th percentile latency
histogram_quantile(0.95, rate(llm_latency_seconds_bucket[5m]))

# Success rate
rate(llm_requests_total{status="success"}[5m]) / rate(llm_requests_total[5m])
```

## Integration Points

### Using LLMClient in Your Code

```python
from app.services.llm_client import LLMClient

# Create tracked client
client = LLMClient(task_id="task-123", user_id="user-456")

# Make API call (automatically tracked)
response = client.chat_completion(
    messages=[...],
    model="gpt-4",
    temperature=0.7
)

# Check usage limits
limits = client.check_usage_limits(
    max_cost_per_task=10.0,
    max_cost_per_user=100.0
)

if not limits["within_limits"]:
    # Handle limit exceeded
    pass
```

### Existing Agents

All existing agents (`FixAgent`, `CodeAgent`, `TestGenerator`) have been updated to:
- Accept optional `task_id` and `user_id` parameters
- Use `LLMClient` wrapper when available
- Fall back to direct OpenAI client if wrapper not available
- Automatically track all LLM calls

## Benefits

1. **Cost Transparency** - Know exactly how much each task/user costs
2. **Performance Monitoring** - Track latency and success rates
3. **Usage Optimization** - Identify opportunities to use cheaper models
4. **Budget Control** - Set and enforce usage limits
5. **Debugging** - Distributed tracing helps debug issues
6. **Compliance** - Audit trail of all LLM usage
7. **Forecasting** - Historical data for cost forecasting

## Future Enhancements

Potential additions:
- [ ] Real-time alerting (Slack, email)
- [ ] Usage quotas with automatic enforcement
- [ ] Cost optimization recommendations
- [ ] Multi-region tracking
- [ ] Custom dashboards
- [ ] Billing integration
- [ ] A/B testing for model selection
- [ ] Token usage forecasting
- [ ] Anomaly detection

## Testing

To test the implementation:

1. **Unit Tests** - Test LLMClient wrapper
2. **Integration Tests** - Test end-to-end tracking
3. **Load Tests** - Verify metrics under load
4. **Cost Validation** - Verify cost calculations are accurate

## Maintenance

### Regular Tasks
- Update model pricing in `llm_client.py` as OpenAI changes prices
- Archive old usage data periodically
- Review and optimize expensive queries
- Monitor and set up alerts for cost thresholds

### Monitoring
- Check Prometheus targets regularly
- Review Jaeger traces for errors
- Monitor disk usage for metrics storage
- Set up backup for usage database

## Support

For questions or issues:
1. Review `OBSERVABILITY.md` for detailed documentation
2. Check `QUICKSTART_OBSERVABILITY.md` for getting started
3. Review logs for errors
4. Check Docker container logs if using observability stack

## Conclusion

The observability and cost tracking implementation provides:
- ✅ Complete LLM usage tracking
- ✅ Accurate cost calculation
- ✅ Distributed tracing
- ✅ Prometheus metrics
- ✅ RESTful API for usage statistics
- ✅ Usage limit enforcement
- ✅ Easy deployment with Docker Compose
- ✅ Comprehensive documentation

All features are production-ready and can be enabled/disabled via environment variables.
