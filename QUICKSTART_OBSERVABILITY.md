# Quick Start: Observability & Cost Tracking

This guide will help you get started with the observability and cost tracking features in 5 minutes.

## Prerequisites

- Docker and Docker Compose installed
- Python 3.8+ installed
- OpenAI API key

## Step 1: Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

## Step 2: Configure Environment

```bash
# Copy example environment file
cp ../.env.example ../.env

# Edit .env and add your OpenAI API key
# OPENAI_API_KEY=sk-your-api-key-here
# ENABLE_OPENTELEMETRY=true
```

## Step 3: Start Observability Stack (Optional)

This step is optional but recommended for full observability features.

```bash
# Start Jaeger, Prometheus, and Grafana
cd ..
docker-compose -f docker-compose.observability.yml up -d

# Check status
docker-compose -f docker-compose.observability.yml ps
```

**Services will be available at:**
- Jaeger UI: http://localhost:16686 (distributed tracing)
- Prometheus UI: http://localhost:9090 (metrics)
- Grafana UI: http://localhost:3000 (dashboards - admin/admin)

## Step 4: Start Backend

```bash
cd backend
uvicorn app.main:app --reload
```

The API will be available at: http://localhost:8000

## Step 5: Test LLM Usage Tracking

### Submit a Test Task

```bash
curl -X POST http://localhost:8000/api/v1/task/submit \
  -H "Content-Type: application/json" \
  -d '{
    "repo_url": "https://github.com/example/repo",
    "bug_description": "Fix the authentication bug",
    "test_command": "pytest tests/"
  }'
```

Save the returned `task_id`.

### View LLM Usage for the Task

```bash
# Replace {task_id} with actual task ID
curl http://localhost:8000/api/v1/usage/task/{task_id}
```

**Example Response:**
```json
{
  "task_id": "abc-123",
  "total_requests": 2,
  "total_tokens": 5000,
  "total_cost_usd": 0.25,
  "avg_latency_ms": 1200.0,
  "by_model": {
    "gpt-4": {
      "requests": 2,
      "tokens": 5000,
      "cost_usd": 0.25
    }
  }
}
```

## Step 6: View Metrics

### Prometheus Metrics

```bash
# View raw Prometheus metrics
curl http://localhost:8000/metrics
```

### API Metrics Endpoints

```bash
# Overall usage (last 7 days)
curl http://localhost:8000/api/v1/usage/overall?days=7

# Task execution metrics
curl http://localhost:8000/api/v1/usage/metrics/tasks?days=7
```

### Jaeger Traces

1. Open http://localhost:16686
2. Select service: `asa-backend`
3. Click "Find Traces"
4. View distributed traces for LLM calls, DB queries, etc.

### Prometheus Queries

1. Open http://localhost:9090
2. Try these queries:
   ```promql
   # Total LLM cost
   sum(llm_cost_usd_total)

   # Request rate by model
   rate(llm_requests_total[5m])

   # Average latency
   histogram_quantile(0.95, rate(llm_latency_seconds_bucket[5m]))

   # Task success rate
   rate(task_success_total{status="success"}[5m])
   ```

## Step 7: Create Grafana Dashboard

1. Open http://localhost:3000 (admin/admin)
2. Add Prometheus data source:
   - Go to Configuration > Data Sources
   - Click "Add data source"
   - Select Prometheus
   - URL: `http://prometheus:9090`
   - Click "Save & Test"

3. Create dashboard:
   - Click "+" > Dashboard
   - Add panels with queries like:
     ```promql
     # LLM Cost Over Time
     sum(rate(llm_cost_usd_total[1h]))

     # Token Usage by Model
     sum by (model) (llm_tokens_total)

     # Request Latency
     histogram_quantile(0.95, rate(llm_latency_seconds_bucket[5m]))
     ```

## Common Use Cases

### 1. Monitor Daily Costs

```python
import requests
from datetime import datetime, timedelta

# Get usage for last 24 hours
response = requests.get("http://localhost:8000/api/v1/usage/overall?days=1")
data = response.json()

print(f"Last 24h Cost: ${data['total_cost_usd']:.2f}")
print(f"Total Tokens: {data['total_tokens']:,}")
print(f"Success Rate: {data['success_rate_percent']:.1f}%")
```

### 2. Set Up Cost Alerts

```python
from app.services.llm_client import LLMClient

client = LLMClient(task_id="task-123")

# Check if within budget
limits = client.check_usage_limits(max_cost_per_task=5.0)

if not limits["within_limits"]:
    # Send alert (email, Slack, etc.)
    print("ALERT: Task exceeded cost limit!")
```

### 3. Analyze Model Performance

```bash
# Compare costs by model
curl http://localhost:8000/api/v1/usage/overall?days=30 | \
  jq '.by_model | to_entries | sort_by(.value.cost_usd) | reverse'
```

### 4. Track User Usage

```bash
# Get usage for specific user
curl http://localhost:8000/api/v1/usage/user/user-123?days=30
```

## Troubleshooting

### Issue: No data in Prometheus

**Solution:**
1. Check if backend is running: `curl http://localhost:8000/health`
2. Check if metrics endpoint works: `curl http://localhost:8000/metrics`
3. On Windows, update `prometheus.yml`:
   ```yaml
   - targets: ['host.docker.internal:8000']
   ```

### Issue: OpenTelemetry not working

**Solution:**
1. Check environment variable: `echo $ENABLE_OPENTELEMETRY`
2. Ensure Jaeger is running: `docker ps | grep jaeger`
3. Check logs for errors in backend

### Issue: Usage not being tracked

**Solution:**
1. Verify `LLMUsage` table exists:
   ```bash
   sqlite3 backend/asa.db "SELECT * FROM llm_usage LIMIT 1;"
   ```
2. Check that agents are initialized with `task_id`
3. Review backend logs for errors

## Next Steps

1. **Set Up Alerts** - Configure Prometheus AlertManager for cost alerts
2. **Create Dashboards** - Build Grafana dashboards for your team
3. **Implement Quotas** - Add usage quotas to prevent overspending
4. **Export Data** - Set up regular exports of usage data for billing
5. **Optimize Costs** - Use insights to switch to cheaper models where possible

## Resources

- Full Documentation: See `OBSERVABILITY.md`
- API Reference: http://localhost:8000/docs
- Jaeger Docs: https://www.jaegertracing.io/docs/
- Prometheus Docs: https://prometheus.io/docs/
- Grafana Docs: https://grafana.com/docs/

## Support

For questions or issues:
1. Check the full documentation in `OBSERVABILITY.md`
2. Review logs in the backend console
3. Check Docker logs: `docker-compose -f docker-compose.observability.yml logs`
