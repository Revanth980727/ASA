from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.orm import Session
from typing import List, Optional
from ...database import get_db
from ...models import Task
from ...schemas import TaskSubmit, TaskResponse, TaskDetail, TaskListItem
from ...services.queue import get_task_queue
from ...services.worker_tasks import run_task_job

router = APIRouter()

@router.post("/submit", response_model=TaskDetail, status_code=status.HTTP_201_CREATED)
def submit_task(
    task: TaskSubmit,
    db: Session = Depends(get_db),
    x_user_id: Optional[str] = Header(None)
):
    """
    Submit a new bug fix task to the queue.

    This endpoint creates a task and enqueues it for processing by RQ workers.
    Backpressure is applied based on queue size and per-user limits.
    """
    try:
        queue = get_task_queue()

        # Check if we can enqueue (backpressure)
        can_enqueue, reason = queue.can_enqueue(user_id=x_user_id)
        if not can_enqueue:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Cannot accept task: {reason}"
            )

        # Create task in database
        db_task = Task(
            repo_url=task.repo_url,
            bug_description=task.bug_description,
            test_command=task.test_command,
            user_id=x_user_id,
            status="QUEUED",
            workspace_path=None,
            branch_name=None,
            pr_url=None,
            logs=""
        )
        db.add(db_task)
        db.commit()
        db.refresh(db_task)

        # Enqueue the task
        job = queue.enqueue_task(
            run_task_job,
            task_id=db_task.id,
            user_id=x_user_id
        )

        if not job:
            # Failed to enqueue (shouldn't happen after can_enqueue check)
            db_task.status = "FAILED"
            db_task.logs = "Failed to enqueue task"
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to enqueue task"
            )

        # Store job ID for tracking
        db_task.job_id = job.id
        db.commit()
        db.refresh(db_task)

        return db_task
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create task: {str(e)}"
        )

@router.get("/{task_id}", response_model=TaskDetail)
def get_task(task_id: str, db: Session = Depends(get_db)):
    """Get task details by ID"""
    try:
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            raise HTTPException(status_code=404, detail=f"Task with ID '{task_id}' not found")
        return task
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve task: {str(e)}")

@router.get("", response_model=List[TaskListItem])
def list_tasks(db: Session = Depends(get_db)):
    """Get list of all tasks"""
    try:
        tasks = db.query(Task).order_by(Task.created_at.desc()).all()
        return tasks
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list tasks: {str(e)}")


@router.post("/{task_id}/cancel")
def cancel_task(task_id: str, db: Session = Depends(get_db)):
    """
    Cancel and delete a task completely.

    This will:
    1. Cancel the job in the queue (if queued/running)
    2. Delete the task from the database
    3. Remove all job history from Redis
    """
    try:
        # Get task
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            raise HTTPException(status_code=404, detail=f"Task with ID '{task_id}' not found")

        # Cancel the job in queue (if exists)
        if task.job_id:
            try:
                queue = get_task_queue()
                queue.cancel_job(task.job_id)

                # Also try to delete the job completely from Redis
                job = queue.get_job(task.job_id)
                if job:
                    job.delete()
            except Exception as e:
                # Log but continue - we still want to delete from DB even if Redis cleanup fails
                print(f"Warning: Failed to cancel/delete job {task.job_id}: {e}")

        # Delete task from database
        db.delete(task)
        db.commit()

        return {
            "success": True,
            "task_id": task_id,
            "message": "Task cancelled and deleted successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to cancel task: {str(e)}"
        )


@router.get("/{task_id}/job-status")
def get_job_status(task_id: str, db: Session = Depends(get_db)):
    """
    Get detailed job status from the queue.

    Returns queue-level job information including:
    - Job status (queued, started, finished, failed)
    - Timing information
    - Queue position
    """
    try:
        # Get task
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            raise HTTPException(status_code=404, detail=f"Task with ID '{task_id}' not found")

        if not task.job_id:
            return {
                "task_id": task_id,
                "job_id": None,
                "message": "Task not yet queued or job ID not available"
            }

        # Get job status from queue
        queue = get_task_queue()
        job_status = queue.get_job_status(task.job_id)

        if not job_status:
            return {
                "task_id": task_id,
                "job_id": task.job_id,
                "message": "Job not found in queue (may have expired)"
            }

        return {
            "task_id": task_id,
            "job_id": task.job_id,
            "job_status": job_status
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get job status: {str(e)}"
        )


@router.get("/queue/stats")
def get_queue_stats():
    """Get current queue statistics and limits."""
    try:
        queue = get_task_queue()
        stats = queue.get_queue_stats()
        return stats
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get queue stats: {str(e)}"
        )
