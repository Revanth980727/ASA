"""
Enhanced API endpoints for frontend features.

Includes:
- Real-time status updates
- Detailed logs and test results
- PR information
- User feedback collection (RLHF)
"""

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime
import asyncio
import json

from ...database import get_db
from ...models import Task
from ...schemas import TaskDetail, FeedbackSubmit
from ...services.workflow_monitor import WorkflowMonitor

router = APIRouter()


# WebSocket connection manager
class ConnectionManager:
    """Manage WebSocket connections for real-time updates."""

    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, task_id: str):
        """Accept connection and track it."""
        await websocket.accept()
        if task_id not in self.active_connections:
            self.active_connections[task_id] = []
        self.active_connections[task_id].append(websocket)

    def disconnect(self, websocket: WebSocket, task_id: str):
        """Remove connection from tracking."""
        if task_id in self.active_connections:
            self.active_connections[task_id].remove(websocket)
            if not self.active_connections[task_id]:
                del self.active_connections[task_id]

    async def send_update(self, task_id: str, data: dict):
        """Send update to all connections watching this task."""
        if task_id in self.active_connections:
            message = json.dumps(data)
            for connection in self.active_connections[task_id]:
                try:
                    await connection.send_text(message)
                except Exception:
                    pass  # Connection might be closed


manager = ConnectionManager()


@router.websocket("/ws/task/{task_id}")
async def websocket_endpoint(websocket: WebSocket, task_id: str, db: Session = Depends(get_db)):
    """
    WebSocket endpoint for real-time task updates.

    Sends updates when task status, logs, or other fields change.
    """
    await manager.connect(websocket, task_id)

    try:
        # Send initial status
        task = db.query(Task).filter(Task.id == task_id).first()
        if task:
            await websocket.send_json({
                "type": "status",
                "task_id": task_id,
                "status": task.status,
                "updated_at": task.updated_at.isoformat() if task.updated_at else None
            })

        # Keep connection alive and send updates
        last_update = None
        while True:
            # Check for updates every second
            await asyncio.sleep(1)

            task = db.query(Task).filter(Task.id == task_id).first()
            if not task:
                break

            # Send update if task changed
            if task.updated_at != last_update:
                await websocket.send_json({
                    "type": "update",
                    "task_id": task_id,
                    "status": task.status,
                    "logs": task.logs,
                    "branch_name": task.branch_name,
                    "pr_url": task.pr_url,
                    "updated_at": task.updated_at.isoformat() if task.updated_at else None
                })
                last_update = task.updated_at

            # Close if task is in terminal state
            if task.status in ["COMPLETED", "FAILED", "TIMEOUT"]:
                await websocket.send_json({
                    "type": "final",
                    "task_id": task_id,
                    "status": task.status
                })
                break

    except WebSocketDisconnect:
        manager.disconnect(websocket, task_id)
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        manager.disconnect(websocket, task_id)


@router.get("/task/{task_id}/logs")
def get_task_logs(
    task_id: str,
    tail: Optional[int] = None,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get task execution logs.

    Args:
        task_id: Task ID
        tail: Number of lines to return (None = all)

    Returns:
        {
            "task_id": str,
            "logs": str,
            "log_count": int
        }
    """
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    logs = task.logs or ""
    log_lines = logs.split('\n')

    if tail:
        log_lines = log_lines[-tail:]

    return {
        "task_id": task_id,
        "logs": '\n'.join(log_lines),
        "log_count": len(log_lines)
    }


@router.get("/task/{task_id}/status")
def get_task_status(task_id: str, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Get detailed task status.

    Returns:
        {
            "task_id": str,
            "status": str,
            "created_at": str,
            "updated_at": str,
            "duration_seconds": float,
            "progress_percentage": float,
            "current_step": str
        }
    """
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # Calculate duration
    duration = None
    if task.updated_at and task.created_at:
        duration = (task.updated_at - task.created_at).total_seconds()

    # Estimate progress based on status
    progress_map = {
        "QUEUED": 0,
        "INIT": 5,
        "CLONING_REPO": 10,
        "INDEXING_CODE": 20,
        "VERIFYING_BUG_BEHAVIOR": 30,
        "RUNNING_TESTS_BEFORE_FIX": 40,
        "GENERATING_FIX": 60,
        "RUNNING_TESTS_AFTER_FIX": 80,
        "VERIFYING_FIX_BEHAVIOR": 85,
        "CREATING_PR_BRANCH": 95,
        "COMPLETED": 100,
        "FAILED": 0,
    }
    progress = progress_map.get(task.status, 0)

    return {
        "task_id": task_id,
        "status": task.status,
        "created_at": task.created_at.isoformat() if task.created_at else None,
        "updated_at": task.updated_at.isoformat() if task.updated_at else None,
        "duration_seconds": duration,
        "progress_percentage": progress,
        "current_step": task.status
    }


@router.get("/task/{task_id}/pr")
def get_task_pr_info(task_id: str, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Get PR information for a task.

    Returns:
        {
            "task_id": str,
            "pr_url": str | None,
            "branch_name": str | None,
            "has_pr": bool
        }
    """
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    return {
        "task_id": task_id,
        "pr_url": task.pr_url,
        "branch_name": task.branch_name,
        "has_pr": bool(task.pr_url)
    }


@router.post("/task/{task_id}/feedback")
def submit_feedback(
    task_id: str,
    feedback: FeedbackSubmit,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Submit user feedback for a task (RLHF).

    Body:
        {
            "rating": int (1-5),
            "approved": bool,
            "comment": str,
            "issues": List[str]
        }

    Returns:
        {
            "task_id": str,
            "feedback_recorded": bool,
            "message": str
        }
    """
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # Store feedback in logs for now (could be separate table later)
    feedback_entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "rating": feedback.rating,
        "approved": feedback.approved,
        "comment": feedback.comment,
        "issues": feedback.issues
    }

    feedback_log = f"\n[FEEDBACK] {json.dumps(feedback_entry)}"
    task.logs = (task.logs or "") + feedback_log

    db.commit()

    return {
        "task_id": task_id,
        "feedback_recorded": True,
        "message": "Thank you for your feedback!"
    }


@router.get("/dashboard")
def get_dashboard(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Get dashboard data.

    Returns:
        {
            "metrics_24h": {...},
            "metrics_all_time": {...},
            "recent_tasks": [...],
            "active_tasks": [...]
        }
    """
    monitor = WorkflowMonitor(db)
    dashboard = monitor.get_dashboard()

    # Add active tasks
    active_tasks = db.query(Task).filter(
        ~Task.status.in_(["COMPLETED", "FAILED", "TIMEOUT"])
    ).order_by(Task.created_at.desc()).all()

    dashboard["active_tasks"] = [
        {
            "task_id": t.id,
            "status": t.status,
            "created_at": t.created_at.isoformat() if t.created_at else None,
            "bug_description": t.bug_description[:100] + "..."
            if len(t.bug_description) > 100
            else t.bug_description
        }
        for t in active_tasks
    ]

    return dashboard


@router.get("/metrics")
def get_metrics(
    time_window_hours: Optional[int] = 24,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get workflow metrics.

    Query params:
        time_window_hours: Time window (None = all time)

    Returns:
        {
            "total_tasks": int,
            "completed": int,
            "failed": int,
            "in_progress": int,
            "success_rate": float,
            "avg_duration_seconds": float
        }
    """
    monitor = WorkflowMonitor(db)
    metrics = monitor.get_metrics(time_window_hours=time_window_hours)

    return {
        "total_tasks": metrics.total_tasks,
        "completed": metrics.completed,
        "failed": metrics.failed,
        "in_progress": metrics.in_progress,
        "success_rate": metrics.success_rate,
        "avg_duration_seconds": metrics.avg_duration_seconds,
        "state_distribution": metrics.state_distribution
    }
