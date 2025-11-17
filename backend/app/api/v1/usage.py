"""
Usage and Cost Tracking API Endpoints.

Provides endpoints for:
- Viewing LLM usage statistics per task
- Viewing LLM usage statistics per user
- Viewing overall usage and cost metrics
- Setting and checking usage limits
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional, List
from datetime import datetime, timedelta

from ...database import get_db
from ...models import LLMUsage, Task, TaskMetrics


router = APIRouter()


@router.get("/task/{task_id}")
def get_task_usage(task_id: str, db: Session = Depends(get_db)):
    """
    Get LLM usage statistics for a specific task.

    Returns:
        - Total requests
        - Total tokens used
        - Total cost (USD)
        - Average latency
        - Breakdown by model
    """
    # Check if task exists
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    # Get usage records
    usage_records = db.query(LLMUsage).filter(LLMUsage.task_id == task_id).all()

    if not usage_records:
        return {
            "task_id": task_id,
            "total_requests": 0,
            "total_tokens": 0,
            "total_cost_usd": 0.0,
            "avg_latency_ms": 0.0,
            "by_model": {},
            "timeline": []
        }

    # Aggregate overall stats
    result = db.query(
        func.count(LLMUsage.id).label("request_count"),
        func.sum(LLMUsage.total_tokens).label("total_tokens"),
        func.sum(LLMUsage.cost_usd).label("total_cost_usd"),
        func.avg(LLMUsage.latency_ms).label("avg_latency_ms"),
    ).filter(LLMUsage.task_id == task_id).first()

    # Aggregate by model
    by_model_results = db.query(
        LLMUsage.model,
        func.count(LLMUsage.id).label("request_count"),
        func.sum(LLMUsage.total_tokens).label("total_tokens"),
        func.sum(LLMUsage.cost_usd).label("total_cost_usd"),
    ).filter(LLMUsage.task_id == task_id).group_by(LLMUsage.model).all()

    by_model = {}
    for row in by_model_results:
        by_model[row.model] = {
            "requests": row.request_count,
            "tokens": row.total_tokens,
            "cost_usd": float(row.total_cost_usd)
        }

    return {
        "task_id": task_id,
        "total_requests": result.request_count or 0,
        "total_tokens": result.total_tokens or 0,
        "total_cost_usd": float(result.total_cost_usd or 0.0),
        "avg_latency_ms": float(result.avg_latency_ms or 0.0),
        "by_model": by_model,
        "records": [
            {
                "model": r.model,
                "tokens": r.total_tokens,
                "cost_usd": r.cost_usd,
                "latency_ms": r.latency_ms,
                "status": r.status,
                "timestamp": r.timestamp.isoformat() if r.timestamp else None
            }
            for r in usage_records
        ]
    }


@router.get("/user/{user_id}")
def get_user_usage(
    user_id: str,
    days: int = Query(30, description="Number of days to look back"),
    db: Session = Depends(get_db)
):
    """
    Get LLM usage statistics for a specific user.

    Args:
        user_id: User ID
        days: Number of days to look back (default: 30)

    Returns:
        - Total requests
        - Total tokens used
        - Total cost (USD)
        - Average latency
        - Breakdown by model
        - Daily usage trend
    """
    # Calculate date range
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)

    # Get usage records
    usage_records = db.query(LLMUsage).filter(
        LLMUsage.user_id == user_id,
        LLMUsage.timestamp >= start_date
    ).all()

    if not usage_records:
        return {
            "user_id": user_id,
            "period_days": days,
            "total_requests": 0,
            "total_tokens": 0,
            "total_cost_usd": 0.0,
            "avg_latency_ms": 0.0,
            "by_model": {}
        }

    # Aggregate overall stats
    result = db.query(
        func.count(LLMUsage.id).label("request_count"),
        func.sum(LLMUsage.total_tokens).label("total_tokens"),
        func.sum(LLMUsage.cost_usd).label("total_cost_usd"),
        func.avg(LLMUsage.latency_ms).label("avg_latency_ms"),
    ).filter(
        LLMUsage.user_id == user_id,
        LLMUsage.timestamp >= start_date
    ).first()

    # Aggregate by model
    by_model_results = db.query(
        LLMUsage.model,
        func.count(LLMUsage.id).label("request_count"),
        func.sum(LLMUsage.total_tokens).label("total_tokens"),
        func.sum(LLMUsage.cost_usd).label("total_cost_usd"),
    ).filter(
        LLMUsage.user_id == user_id,
        LLMUsage.timestamp >= start_date
    ).group_by(LLMUsage.model).all()

    by_model = {}
    for row in by_model_results:
        by_model[row.model] = {
            "requests": row.request_count,
            "tokens": row.total_tokens,
            "cost_usd": float(row.total_cost_usd)
        }

    return {
        "user_id": user_id,
        "period_days": days,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "total_requests": result.request_count or 0,
        "total_tokens": result.total_tokens or 0,
        "total_cost_usd": float(result.total_cost_usd or 0.0),
        "avg_latency_ms": float(result.avg_latency_ms or 0.0),
        "by_model": by_model
    }


@router.get("/overall")
def get_overall_usage(
    days: int = Query(7, description="Number of days to look back"),
    db: Session = Depends(get_db)
):
    """
    Get overall LLM usage statistics across all tasks and users.

    Args:
        days: Number of days to look back (default: 7)

    Returns:
        - Total requests
        - Total tokens used
        - Total cost (USD)
        - Breakdown by model
        - Success rate
    """
    # Calculate date range
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)

    # Get overall stats
    result = db.query(
        func.count(LLMUsage.id).label("request_count"),
        func.sum(LLMUsage.total_tokens).label("total_tokens"),
        func.sum(LLMUsage.cost_usd).label("total_cost_usd"),
        func.avg(LLMUsage.latency_ms).label("avg_latency_ms"),
    ).filter(LLMUsage.timestamp >= start_date).first()

    # Count successes and failures
    success_count = db.query(func.count(LLMUsage.id)).filter(
        LLMUsage.timestamp >= start_date,
        LLMUsage.status == "success"
    ).scalar()

    error_count = db.query(func.count(LLMUsage.id)).filter(
        LLMUsage.timestamp >= start_date,
        LLMUsage.status == "error"
    ).scalar()

    total_count = success_count + error_count
    success_rate = (success_count / total_count * 100) if total_count > 0 else 0

    # Aggregate by model
    by_model_results = db.query(
        LLMUsage.model,
        func.count(LLMUsage.id).label("request_count"),
        func.sum(LLMUsage.total_tokens).label("total_tokens"),
        func.sum(LLMUsage.cost_usd).label("total_cost_usd"),
    ).filter(LLMUsage.timestamp >= start_date).group_by(LLMUsage.model).all()

    by_model = {}
    for row in by_model_results:
        by_model[row.model] = {
            "requests": row.request_count,
            "tokens": row.total_tokens,
            "cost_usd": float(row.total_cost_usd)
        }

    return {
        "period_days": days,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "total_requests": result.request_count or 0,
        "total_tokens": result.total_tokens or 0,
        "total_cost_usd": float(result.total_cost_usd or 0.0),
        "avg_latency_ms": float(result.avg_latency_ms or 0.0),
        "success_rate_percent": round(success_rate, 2),
        "successful_requests": success_count,
        "failed_requests": error_count,
        "by_model": by_model
    }


@router.get("/metrics/tasks")
def get_task_metrics(
    days: int = Query(7, description="Number of days to look back"),
    db: Session = Depends(get_db)
):
    """
    Get task execution metrics.

    Returns:
        - Total tasks
        - Success rate
        - Average duration
        - Status breakdown
    """
    # Calculate date range
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)

    # Get tasks in time range
    tasks = db.query(Task).filter(Task.created_at >= start_date).all()

    if not tasks:
        return {
            "period_days": days,
            "total_tasks": 0,
            "success_rate_percent": 0,
            "by_status": {}
        }

    # Count by status
    status_counts = db.query(
        Task.status,
        func.count(Task.id).label("count")
    ).filter(Task.created_at >= start_date).group_by(Task.status).all()

    by_status = {row.status: row.count for row in status_counts}

    # Calculate success rate
    completed = by_status.get("COMPLETED", 0)
    failed = by_status.get("FAILED", 0)
    total = len(tasks)
    success_rate = (completed / total * 100) if total > 0 else 0

    return {
        "period_days": days,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "total_tasks": total,
        "success_rate_percent": round(success_rate, 2),
        "completed_tasks": completed,
        "failed_tasks": failed,
        "by_status": by_status
    }
