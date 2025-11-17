from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from ...database import get_db
from ...models import Task
from ...schemas import TaskSubmit, TaskResponse, TaskDetail, TaskListItem

router = APIRouter()

@router.post("/submit", response_model=TaskResponse)
def submit_task(task: TaskSubmit, db: Session = Depends(get_db)):
    """Submit a new bug fix task"""
    try:
        db_task = Task(
            repo_url=task.repo_url,
            bug_description=task.bug_description,
            test_command=task.test_command,
            status="QUEUED"
        )
        db.add(db_task)
        db.commit()
        db.refresh(db_task)
        return TaskResponse(task_id=db_task.id, status=db_task.status)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create task: {str(e)}")

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

