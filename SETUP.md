# ASA Setup Guide

Complete setup instructions for the Autonomous Software Agent (ASA) system with background workers, evaluation framework, and feedback loop.

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [System Architecture](#system-architecture)
3. [Installation](#installation)
4. [Running the System](#running-the-system)
5. [Using the API](#using-the-api)
6. [Evaluation Framework](#evaluation-framework)
7. [Troubleshooting](#troubleshooting)

---

## Prerequisites

Before you begin, ensure you have the following installed:

- **Python 3.10+**
- **Node.js 16+** (for frontend)
- **Redis Server** (for RQ task queue)
- **Git**
- **Docker** (optional, for sandboxed execution)

### Installing Redis

#### Windows:
Download and install Redis from [Redis for Windows](https://github.com/microsoftarchive/redis/releases) or use WSL2.

#### macOS:
```bash
brew install redis
```

#### Linux:
```bash
sudo apt-get update
sudo apt-get install redis-server
```

---

## System Architecture

```
┌──────────────┐
│   Frontend   │ (React)
│  (Port 3000) │
└──────┬───────┘
       │ HTTP API
       ▼
┌──────────────┐      ┌──────────────┐
│   FastAPI    │◄────►│    Redis     │
│  (Port 8000) │      │  (Port 6379) │
└──────┬───────┘      └──────┬───────┘
       │                     │
       │ Enqueue Jobs        │ Pull Jobs
       │                     │
       ▼                     ▼
┌──────────────┐      ┌──────────────┐
│   Database   │◄─────│  RQ Workers  │
│   (SQLite)   │      │ (Background) │
└──────────────┘      └──────────────┘
```

**Components:**
1. **Frontend**: React app for task submission and monitoring
2. **FastAPI Backend**: REST API with queue management
3. **Redis**: Message broker for RQ task queue
4. **RQ Workers**: Background processes executing bug-fix tasks
5. **SQLite Database**: Persistent storage for tasks, feedback, evaluations

---

## Installation

### 1. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Set environment variables
# Create .env file:
echo "OPENAI_API_KEY=your_api_key_here" > .env
echo "GITHUB_TOKEN=your_github_token_here" >> .env
```

### 2. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install
```

### 3. Database Initialization

The database will be created automatically on first run. To manually create tables:

```bash
cd backend
python -c "from app.database import engine; from app.models import Base; Base.metadata.create_all(bind=engine)"
```

---

## Running the System

You need **4 terminal windows** to run the complete system:

### Terminal 1: Redis Server
```bash
# Start Redis
redis-server

# Verify Redis is running:
redis-cli ping
# Should return: PONG
```

### Terminal 2: Backend API
```bash
cd backend
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Run FastAPI server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at: `http://localhost:8000`
API docs at: `http://localhost:8000/docs`

### Terminal 3: RQ Worker
```bash
cd backend
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Start a worker
python worker.py

# For multiple workers (increase concurrency):
python worker.py --name worker-1
# In another terminal:
python worker.py --name worker-2
```

### Terminal 4: Frontend
```bash
cd frontend

# Start React dev server
npm start
```

The frontend will be available at: `http://localhost:3000`

---

## Using the API

### Submit a Task

**Via Frontend:**
1. Open `http://localhost:3000`
2. Enter repository URL and bug description
3. Click "Submit Bug Fix Task"

**Via API:**
```bash
curl -X POST "http://localhost:8000/api/v1/task/submit" \
  -H "Content-Type: application/json" \
  -d '{
    "repo_url": "https://github.com/user/repo.git",
    "bug_description": "Function has syntax error on line 42",
    "test_command": "pytest tests/"
  }'
```

### Check Queue Status

```bash
curl http://localhost:8000/api/v1/task/queue/stats
```

Response:
```json
{
  "queue_size": 3,
  "high_priority_queue_size": 0,
  "active_jobs": 2,
  "total_workers": 1,
  "limits": {
    "max_queue_size": 100,
    "max_concurrent_jobs": 5,
    "max_per_user_concurrent": 2
  }
}
```

### Cancel a Task

```bash
curl -X POST "http://localhost:8000/api/v1/task/{task_id}/cancel"
```

### Submit Feedback

**Via Frontend:**
1. Click "Give Feedback" button on completed task
2. Rate 1-5 stars
3. Check "I approve this fix" if satisfied
4. Add optional comment
5. Submit

**Via API:**
```bash
curl -X POST "http://localhost:8000/api/v1/task/{task_id}/feedback" \
  -H "Content-Type: application/json" \
  -d '{
    "rating": 5,
    "approved": true,
    "comment": "Great fix!",
    "issues": []
  }'
```

### View Aggregate Feedback

```bash
curl http://localhost:8000/api/v1/feedback/aggregate
```

---

## Evaluation Framework

The evaluation framework runs ASA against a golden set of 25 test cases to measure performance.

### Load Golden Set to Database

```bash
cd backend
python ops/eval/run_golden_set.py --load-only
```

### Run Full Evaluation

```bash
# Run all 25 cases (this will take time!)
python ops/eval/run_golden_set.py --output results/eval_$(date +%Y%m%d).json
```

### Run Single Test Case

```bash
python ops/eval/run_golden_set.py --case-name python_simple_syntax_error
```

### Evaluation Report

The script generates a comprehensive report:

```
====================================================================
ASA GOLDEN SET EVALUATION REPORT
====================================================================

Timestamp: 2025-01-15T10:30:00.000000

Total Cases: 25
Passed: 21
Failed: 4
Success Rate: 84.0%

Total Execution Time: 1250.45s
Average Time per Case: 50.02s

Total Cost: $12.5600
Average Cost per Case: $0.5024

--------------------------------------------------------------------
SUCCESS CRITERIA
--------------------------------------------------------------------
Required Success Rate: 80.0%
Actual Success Rate: 84.0%
Status: PASS

--------------------------------------------------------------------
INDIVIDUAL RESULTS
--------------------------------------------------------------------
✓ PASS | python_simple_syntax_error           |  45.32s | $ 0.4521
✓ PASS | python_undefined_variable            |  52.11s | $ 0.5102
✗ FAIL | python_type_error_string_int         |  61.45s | $ 0.6234
...
====================================================================
```

### Success Criteria

Based on the FROZEN spec:
- **Required Success Rate**: 80% on golden set
- **Maximum Cost per Case**: $2.00
- **Maximum Time per Case**: 5 minutes

---

## Configuration

### Queue Limits (backend/app/services/queue.py)

```python
class QueueConfig:
    MAX_QUEUE_SIZE = 100          # Maximum tasks in queue
    MAX_CONCURRENT_JOBS = 5       # Maximum concurrent workers
    MAX_PER_USER_CONCURRENT = 2   # Maximum per-user tasks
    JOB_TIMEOUT = 3600            # 1 hour per task
```

### Redis Connection

Set via environment variables:
```bash
export REDIS_HOST=localhost
export REDIS_PORT=6379
export REDIS_DB=0
```

---

## Monitoring

### View Worker Status

```bash
# Check running workers
rq info --url redis://localhost:6379

# View job details
rq info --url redis://localhost:6379 <job_id>
```

### View Task Logs

```bash
curl http://localhost:8000/api/v1/task/{task_id}/logs
```

### Prometheus Metrics

Available at: `http://localhost:8000/metrics`

Metrics include:
- `llm_requests_total`
- `llm_tokens_total`
- `llm_cost_usd_total`
- `task_duration_seconds`
- `task_success_rate`

---

## Troubleshooting

### Redis Connection Error

**Error:** `Error 61 connecting to localhost:6379. Connection refused.`

**Solution:**
```bash
# Start Redis server
redis-server

# Or as background service:
# macOS:
brew services start redis
# Linux:
sudo systemctl start redis
```

### Worker Not Processing Jobs

**Check:**
1. Is Redis running? `redis-cli ping`
2. Is worker running? Check terminal output
3. Are there jobs in queue? Check queue stats API

**Solution:**
```bash
# Restart worker
python worker.py --burst  # Run once and exit
```

### Database Migration Needed

If you've updated models, recreate the database:

```bash
cd backend
rm asa.db  # CAUTION: Deletes all data!
python -c "from app.database import engine; from app.models import Base; Base.metadata.create_all(bind=engine)"
```

### Frontend Can't Connect to Backend

**Check:**
1. Backend running on port 8000?
2. CORS enabled in `main.py`?

**Solution:**
Update `frontend/src/App.js` API URL if needed:
```javascript
const API_BASE_URL = 'http://localhost:8000';
```

---

## Production Deployment Checklist

- [ ] Use PostgreSQL instead of SQLite
- [ ] Set up Redis in production mode (persistence enabled)
- [ ] Use environment variables for all secrets
- [ ] Set up reverse proxy (nginx) for API
- [ ] Enable HTTPS
- [ ] Set up monitoring (Prometheus + Grafana)
- [ ] Configure log aggregation
- [ ] Set up backup strategy for database
- [ ] Use process manager (systemd/supervisor) for workers
- [ ] Implement rate limiting
- [ ] Set up health checks
- [ ] Configure queue retention policies

---

## Additional Resources

- **RQ Documentation**: https://python-rq.org/
- **FastAPI Documentation**: https://fastapi.tiangolo.com/
- **Redis Documentation**: https://redis.io/documentation

---

## Support

For issues or questions:
1. Check the troubleshooting section
2. Review API documentation at `/docs`
3. Check worker logs in `worker.log`
4. Review task logs via API
