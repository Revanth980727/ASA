"""
Workflow Monitor - Track and visualize workflow execution.

Provides metrics, status tracking, and visualization for ASA workflows.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
from sqlalchemy.orm import Session

from app.models import Task
from app.services.state_machine import TaskState


@dataclass
class WorkflowMetrics:
    """Metrics for workflow execution."""
    total_tasks: int
    completed: int
    failed: int
    in_progress: int
    avg_duration_seconds: float
    success_rate: float
    state_distribution: Dict[str, int]
    retry_stats: Dict[str, int]


class WorkflowMonitor:
    """Monitor and analyze workflow executions."""

    def __init__(self, db: Session):
        """
        Initialize monitor.

        Args:
            db: Database session
        """
        self.db = db

    def get_metrics(self, time_window_hours: Optional[int] = 24) -> WorkflowMetrics:
        """
        Get workflow metrics.

        Args:
            time_window_hours: Time window for metrics (None = all time)

        Returns:
            WorkflowMetrics object
        """
        query = self.db.query(Task)

        if time_window_hours:
            cutoff = datetime.utcnow() - timedelta(hours=time_window_hours)
            query = query.filter(Task.created_at >= cutoff)

        tasks = query.all()

        if not tasks:
            return WorkflowMetrics(
                total_tasks=0,
                completed=0,
                failed=0,
                in_progress=0,
                avg_duration_seconds=0.0,
                success_rate=0.0,
                state_distribution={},
                retry_stats={}
            )

        # Count by status
        state_counts: Dict[str, int] = {}
        for task in tasks:
            state_counts[task.status] = state_counts.get(task.status, 0) + 1

        completed = state_counts.get(TaskState.COMPLETED.value, 0)
        failed = state_counts.get(TaskState.FAILED.value, 0)
        in_progress = len(tasks) - completed - failed

        # Calculate duration
        durations = []
        for task in tasks:
            if task.updated_at and task.created_at:
                duration = (task.updated_at - task.created_at).total_seconds()
                durations.append(duration)

        avg_duration = sum(durations) / len(durations) if durations else 0.0

        # Success rate
        terminal_count = completed + failed
        success_rate = (completed / terminal_count * 100) if terminal_count > 0 else 0.0

        return WorkflowMetrics(
            total_tasks=len(tasks),
            completed=completed,
            failed=failed,
            in_progress=in_progress,
            avg_duration_seconds=avg_duration,
            success_rate=success_rate,
            state_distribution=state_counts,
            retry_stats={}  # TODO: Extract from logs
        )

    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed status for a task.

        Args:
            task_id: Task ID

        Returns:
            Status dictionary or None
        """
        task = self.db.query(Task).filter(Task.id == task_id).first()
        if not task:
            return None

        duration = None
        if task.updated_at and task.created_at:
            duration = (task.updated_at - task.created_at).total_seconds()

        return {
            "task_id": task.id,
            "status": task.status,
            "created_at": task.created_at.isoformat() if task.created_at else None,
            "updated_at": task.updated_at.isoformat() if task.updated_at else None,
            "duration_seconds": duration,
            "repo_url": task.repo_url,
            "bug_description": task.bug_description[:100] + "..." if len(task.bug_description) > 100 else task.bug_description,
            "branch_name": task.branch_name,
            "logs": task.logs
        }

    def get_recent_tasks(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent tasks.

        Args:
            limit: Maximum number of tasks to return

        Returns:
            List of task dictionaries
        """
        tasks = (
            self.db.query(Task)
            .order_by(Task.created_at.desc())
            .limit(limit)
            .all()
        )

        return [
            {
                "task_id": task.id,
                "status": task.status,
                "created_at": task.created_at.isoformat() if task.created_at else None,
                "bug_description": task.bug_description[:100] + "..."
                if len(task.bug_description) > 100
                else task.bug_description,
            }
            for task in tasks
        ]

    def get_dashboard(self) -> Dict[str, Any]:
        """
        Get complete dashboard data.

        Returns:
            Dashboard dictionary with metrics and recent tasks
        """
        metrics_24h = self.get_metrics(time_window_hours=24)
        metrics_all = self.get_metrics(time_window_hours=None)
        recent_tasks = self.get_recent_tasks(limit=10)

        return {
            "metrics_24h": {
                "total_tasks": metrics_24h.total_tasks,
                "completed": metrics_24h.completed,
                "failed": metrics_24h.failed,
                "in_progress": metrics_24h.in_progress,
                "success_rate": f"{metrics_24h.success_rate:.1f}%",
                "avg_duration": f"{metrics_24h.avg_duration_seconds:.1f}s",
            },
            "metrics_all_time": {
                "total_tasks": metrics_all.total_tasks,
                "completed": metrics_all.completed,
                "failed": metrics_all.failed,
                "success_rate": f"{metrics_all.success_rate:.1f}%",
            },
            "state_distribution": metrics_24h.state_distribution,
            "recent_tasks": recent_tasks,
        }

    def visualize_metrics(self, metrics: WorkflowMetrics) -> str:
        """
        Create text visualization of metrics.

        Args:
            metrics: WorkflowMetrics object

        Returns:
            ASCII visualization
        """
        lines = [
            "ASA Workflow Metrics",
            "=" * 60,
            "",
            f"Total Tasks:     {metrics.total_tasks}",
            f"Completed:       {metrics.completed} ({metrics.success_rate:.1f}% success rate)",
            f"Failed:          {metrics.failed}",
            f"In Progress:     {metrics.in_progress}",
            f"Avg Duration:    {metrics.avg_duration_seconds:.1f}s",
            "",
            "State Distribution:",
            "-" * 60,
        ]

        # Show distribution
        for state, count in sorted(metrics.state_distribution.items(), key=lambda x: -x[1]):
            bar_length = int((count / metrics.total_tasks) * 40) if metrics.total_tasks > 0 else 0
            bar = "█" * bar_length
            lines.append(f"{state:25s} {count:3d} {bar}")

        lines.append("=" * 60)

        return "\n".join(lines)
