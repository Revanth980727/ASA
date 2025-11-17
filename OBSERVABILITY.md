# Observability and Cost Tracking

This document describes the observability and cost tracking features implemented in the ASA (Automated Software Agent) system.

## Overview

The system now includes comprehensive monitoring and cost tracking for LLM usage:

1. **Token Usage Tracking** - Automatic tracking of all LLM API calls
2. **Cost Calculation** - Real-time cost calculation based on model pricing
3. **OpenTelemetry Instrumentation** - Distributed tracing across services
4. **Prometheus Metrics** - Metrics export for monitoring dashboards
5. **Usage Limits** - Per-task and per-user usage limits
6. **API Endpoints** - RESTful APIs for querying usage statistics

## Features

### 1. LLM Token Usage and Cost Tracking

All LLM API calls are automatically tracked with the following information:
- Task ID (if available)
- User ID (if available)
- Model name (e.g., "gpt-4", "gpt-4-turbo")
- Token counts (prompt, completion, total)
- Cost in USD
- Latency in milliseconds
- Status (success/error)
- Timestamp

**Database Schema:**
```sql
CREATE TABLE llm_usage (
    id VARCHAR PRIMARY KEY,
    task_id VARCHAR,
    user_id VARCHAR,
    model VARCHAR NOT NULL,
    prompt_tokens INTEGER NOT NULL,
    completion_tokens INTEGER NOT NULL,
    total_tokens INTEGER NOT NULL,
    cost_usd FLOAT NOT NULL,
    latency_ms FLOAT NOT NULL,
    status VARCHAR NOT NULL,
    error_message TEXT,
    timestamp DATETIME NOT NULL
);
```

### 2. OpenTelemetry Instrumentation

The system uses OpenTelemetry for distributed tracing:

**Automatic Instrumentation:**
- FastAPI HTTP requests
- SQLAlchemy database queries
- LLM API calls (custom spans)

**Custom Span Attributes:**
- `llm.model` - Model name
- `llm.prompt_tokens` - Input tokens
- `llm.completion_tokens` - Output tokens
- `llm.total_tokens` - Total tokens
- `llm.cost_usd` - Cost in USD
- `llm.latency_ms` - Request latency
- `llm.task_id` - Task ID
- `llm.user_id` - User ID

### 3. Prometheus Metrics

The following Prometheus metrics are exported at `/metrics`:

**LLM Metrics:**
- `llm_requests_total` - Total number of LLM requests (by model, status, task_id)
- `llm_tokens_total` - Total tokens used (by model, token_type)
- `llm_cost_usd_total` - Total cost in USD (by model)
- `llm_latency_seconds` - LLM request latency histogram (by model)

**Task Metrics:**
- `task_duration_seconds` - Task execution duration histogram (by status)
- `task_success_total` - Total successful/failed tasks (by status)
- `active_tasks` - Number of currently active tasks (by status)

### 4. Usage Limits

Configure usage limits to prevent excessive costs:

```python
from app.services.llm_client import LLMClient

# Create client with usage tracking
client = LLMClient(task_id="task-123", user_id="user-456")

# Check usage limits
limits = client.check_usage_limits(
    max_cost_per_task=10.0,  # $10 per task
    max_cost_per_user=100.0  # $100 per user
)

if not limits["within_limits"]:
    for violation in limits["violations"]:
        print(f"Limit exceeded: {violation}")
```

## Configuration

### Environment Variables

**OpenTelemetry:**
```bash
# Enable/disable OpenTelemetry
ENABLE_OPENTELEMETRY=true

# OTLP endpoint (default: http://localhost:4317)
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
```

**LLM API:**
```bash
# OpenAI API key
OPENAI_API_KEY=sk-...
```

### Model Pricing

Current pricing configuration (in `app/services/llm_client.py`):

```python
MODEL_PRICING = {
    "gpt-4": {
        "input": 30.0,   # $30 per 1M tokens
        "output": 60.0,  # $60 per 1M tokens
    },
    "gpt-4-turbo": {
        "input": 10.0,
        "output": 30.0,
    },
    "gpt-4o": {
        "input": 2.50,
        "output": 10.0,
    },
    "gpt-4o-mini": {
        "input": 0.15,
        "output": 0.60,
    },
    "gpt-3.5-turbo": {
        "input": 0.50,
        "output": 1.50,
    },
}
```

Update these values as OpenAI pricing changes.

## API Endpoints

### Get Task Usage

```bash
GET /api/v1/usage/task/{task_id}
```

**Response:**
```json
{
  "task_id": "task-123",
  "total_requests": 5,
  "total_tokens": 15000,
  "total_cost_usd": 0.75,
  "avg_latency_ms": 1250.5,
  "by_model": {
    "gpt-4": {
      "requests": 3,
      "tokens": 10000,
      "cost_usd": 0.50
    },
    "gpt-4-turbo": {
      "requests": 2,
      "tokens": 5000,
      "cost_usd": 0.25
    }
  },
  "records": [...]
}
```

### Get User Usage

```bash
GET /api/v1/usage/user/{user_id}?days=30
```

**Response:**
```json
{
  "user_id": "user-456",
  "period_days": 30,
  "start_date": "2025-01-01T00:00:00",
  "end_date": "2025-01-31T00:00:00",
  "total_requests": 50,
  "total_tokens": 150000,
  "total_cost_usd": 7.50,
  "avg_latency_ms": 1100.0,
  "by_model": {...}
}
```

### Get Overall Usage

```bash
GET /api/v1/usage/overall?days=7
```

**Response:**
```json
{
  "period_days": 7,
  "total_requests": 200,
  "total_tokens": 500000,
  "total_cost_usd": 25.00,
  "avg_latency_ms": 1200.0,
  "success_rate_percent": 98.5,
  "successful_requests": 197,
  "failed_requests": 3,
  "by_model": {...}
}
```

### Get Task Metrics

```bash
GET /api/v1/usage/metrics/tasks?days=7
```

**Response:**
```json
{
  "period_days": 7,
  "total_tasks": 100,
  "success_rate_percent": 85.0,
  "completed_tasks": 85,
  "failed_tasks": 15,
  "by_status": {
    "COMPLETED": 85,
    "FAILED": 10,
    "RUNNING": 3,
    "QUEUED": 2
  }
}
```

## Setup Instructions

### 1. Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 2. Run Database Migrations

The new tables (`llm_usage`, `task_metrics`) will be created automatically when you start the application.

```bash
# Start the backend
uvicorn app.main:app --reload
```

### 3. Set Up OpenTelemetry Collector (Optional)

If you want to export traces and metrics to an external system:

**Install Jaeger (for tracing):**
```bash
docker run -d --name jaeger \
  -p 16686:16686 \
  -p 4317:4317 \
  jaegertracing/all-in-one:latest
```

**Enable OpenTelemetry:**
```bash
export ENABLE_OPENTELEMETRY=true
export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
```

**Access Jaeger UI:**
Open http://localhost:16686 to view traces.

### 4. Set Up Prometheus (Optional)

**prometheus.yml:**
```yaml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'asa-backend'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/metrics'
```

**Run Prometheus:**
```bash
docker run -d --name prometheus \
  -p 9090:9090 \
  -v $(pwd)/prometheus.yml:/etc/prometheus/prometheus.yml \
  prom/prometheus
```

**Access Prometheus UI:**
Open http://localhost:9090

### 5. Set Up Grafana (Optional)

For visualization of metrics:

```bash
docker run -d --name grafana \
  -p 3000:3000 \
  grafana/grafana
```

**Access Grafana UI:**
Open http://localhost:3000 (default credentials: admin/admin)

**Add Prometheus as Data Source:**
1. Go to Configuration > Data Sources
2. Add Prometheus with URL: http://localhost:9090
3. Create dashboards with the metrics

## Usage Examples

### 1. Track LLM Usage in Custom Code

```python
from app.services.llm_client import LLMClient

# Create tracked client
client = LLMClient(task_id="my-task-123", user_id="user-456")

# Make API call (automatically tracked)
response = client.chat_completion(
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello!"}
    ],
    model="gpt-4",
    temperature=0.7,
    max_tokens=100
)

# Get usage stats
stats = client.get_task_usage()
print(f"Total cost: ${stats['total_cost_usd']:.2f}")
print(f"Total tokens: {stats['total_tokens']}")
```

### 2. Check Usage Limits

```python
# Check if within limits
limits = client.check_usage_limits(
    max_cost_per_task=5.0,
    max_cost_per_user=50.0
)

if not limits["within_limits"]:
    print("Usage limit exceeded!")
    for violation in limits["violations"]:
        print(f"  {violation['type']}: ${violation['current_cost']:.2f} / ${violation['limit']:.2f}")
```

### 3. Query Usage via API

```python
import requests

# Get task usage
response = requests.get("http://localhost:8000/api/v1/usage/task/task-123")
usage = response.json()
print(f"Task cost: ${usage['total_cost_usd']:.2f}")

# Get user usage (last 30 days)
response = requests.get("http://localhost:8000/api/v1/usage/user/user-456?days=30")
usage = response.json()
print(f"User cost (30d): ${usage['total_cost_usd']:.2f}")

# Get overall usage (last 7 days)
response = requests.get("http://localhost:8000/api/v1/usage/overall?days=7")
usage = response.json()
print(f"Overall cost (7d): ${usage['total_cost_usd']:.2f}")
print(f"Success rate: {usage['success_rate_percent']:.1f}%")
```

## Monitoring Dashboards

### Recommended Grafana Dashboards

**LLM Usage Dashboard:**
- Total cost per day (time series)
- Token usage by model (pie chart)
- Request latency histogram
- Success/error rate
- Cost breakdown by task

**Task Execution Dashboard:**
- Task success rate (gauge)
- Task duration by status (histogram)
- Active tasks (gauge)
- Task completion rate (time series)

**Cost Analysis Dashboard:**
- Daily cost trend
- Cost per model
- Most expensive tasks
- Cost per user

## Troubleshooting

### OpenTelemetry Not Working

1. Check environment variable:
   ```bash
   echo $ENABLE_OPENTELEMETRY
   ```

2. Verify OTLP endpoint is reachable:
   ```bash
   curl http://localhost:4317
   ```

3. Check logs for errors:
   ```bash
   # Look for "OpenTelemetry" in logs
   ```

### Usage Not Being Tracked

1. Verify database tables exist:
   ```sql
   SELECT * FROM llm_usage LIMIT 1;
   ```

2. Check that agents are using LLMClient:
   ```python
   # In agent code, look for:
   from app.services.llm_client import LLMClient
   ```

3. Verify task_id is being passed:
   ```python
   # Should see:
   agent = CodeAgent(task_id=task_id)
   ```

### Metrics Not Appearing

1. Check `/metrics` endpoint:
   ```bash
   curl http://localhost:8000/metrics
   ```

2. Verify Prometheus is scraping:
   - Open Prometheus UI
   - Go to Status > Targets
   - Check if `asa-backend` is up

## Best Practices

1. **Set Usage Limits** - Always configure cost limits to prevent runaway costs
2. **Monitor Regularly** - Set up alerts for cost thresholds
3. **Review Metrics** - Regularly review success rates and latency
4. **Optimize Models** - Use cheaper models (e.g., gpt-4o-mini) when possible
5. **Track by User** - Implement user tracking for multi-tenant scenarios
6. **Archive Old Data** - Periodically archive old usage records to keep DB performant

## Future Enhancements

- [ ] Real-time cost alerts (email/Slack)
- [ ] Usage quotas with automatic enforcement
- [ ] Cost optimization suggestions
- [ ] Multi-region deployment tracking
- [ ] Custom metrics and dashboards
- [ ] Integration with billing systems
- [ ] Cost forecasting
- [ ] A/B testing framework for model selection
