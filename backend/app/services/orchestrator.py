import time
import sys
from pathlib import Path

from datetime import datetime

from typing import Optional

from sqlalchemy.orm import Session

from app.database import SessionLocal

from app.models import Task

# Add project root to path to import from src/core
# File is at: backend/app/services/orchestrator.py
# Need to go up 3 levels to reach project root (ASA/)
_orchestrator_file = Path(__file__).resolve()
project_root = _orchestrator_file.parent.parent.parent.parent
if project_root.exists() and (project_root / "src" / "core" / "repo_manager.py").exists():
    sys.path.insert(0, str(project_root))

class TaskOrchestrator:

    """

    Very simple fake orchestrator that simulates state changes

    for a single Task.

    It uses its own DB session so it can run safely in a background

    task, outside the request scope.

    """

    def __init__(self, db: Session):

        self.db = db

    @staticmethod

    def start_task(task_id: str) -> None:

        """

        Entry point used by FastAPI BackgroundTasks.

        Example usage:

            background_tasks.add_task(TaskOrchestrator.start_task, task.id)

        """

        db = SessionLocal()

        try:

            orchestrator = TaskOrchestrator(db=db)

            orchestrator._run(task_id)

        finally:

            db.close()

    def _run(self, task_id: str) -> None:

        """

        Pipeline:

        - CLONING_REPO (creates workspace, clones repo)

        - INDEXING_CODE

        - COMPLETED

        """

        # Step 1 - CLONING_REPO

        if not self._set_status(task_id, "CLONING_REPO"):

            # Task not found, nothing else to do

            return

        # Load task to get repo_url
        task = self.db.query(Task).filter(Task.id == task_id).first()
        if not task:
            return

        try:
            # Import here to avoid circular imports
            from src.core.repo_manager import create_workspace, clone_repo

            # Create workspace for this task
            workspace_path = create_workspace(task_id)
            
            # Store workspace_path on Task
            task.workspace_path = workspace_path
            self.db.add(task)
            self.db.commit()
            
            # Clone the repo into the workspace
            clone_repo(task.repo_url, workspace_path)
            
            # Log success
            self._add_log(task_id, f"Successfully cloned {task.repo_url} to {workspace_path}")
            
            # Move to INDEXING_CODE on success
            if not self._set_status(task_id, "INDEXING_CODE"):
                return

        except Exception as e:
            # Log error and move to FAILED
            error_msg = f"Failed to clone repository: {str(e)}"
            self._add_log(task_id, error_msg)
            self._set_status(task_id, "FAILED")
            return

        # Step 2 - INDEXING_CODE (simulated for now)
        time.sleep(2)  # simulate work

        # Step 3 - COMPLETED

        self._set_status(task_id, "COMPLETED")

    def _set_status(self, task_id: str, new_status: str) -> bool:

        """

        Load the task fresh, update status and logs, commit.

        Returns:

            True if the task was found and updated.

            False if the task does not exist.

        """

        task: Optional[Task] = (

            self.db.query(Task)

            .filter(Task.id == task_id)

            .first()

        )

        if task is None:

            # In a real app you might want structured logging here

            print(f"[TaskOrchestrator] Task {task_id} not found. Stopping.")

            return False

        timestamp = datetime.utcnow().isoformat()

        log_line = f"[{timestamp}] Moved to {new_status}"

        # Append to logs. Ensure logs is a string.

        existing_logs = task.logs or ""

        if existing_logs:

            task.logs = existing_logs + "\n" + log_line

        else:

            task.logs = log_line

        task.status = new_status

        task.updated_at = datetime.utcnow()

        self.db.add(task)

        self.db.commit()

        # Optional: refresh to make sure we have the latest state

        self.db.refresh(task)

        return True

    def _add_log(self, task_id: str, message: str) -> None:
        """
        Add a log message to the task's logs field.
        """
        task: Optional[Task] = (
            self.db.query(Task)
            .filter(Task.id == task_id)
            .first()
        )
        
        if task is None:
            return

        timestamp = datetime.utcnow().isoformat()
        log_line = f"[{timestamp}] {message}"

        existing_logs = task.logs or ""
        if existing_logs:
            task.logs = existing_logs + "\n" + log_line
        else:
            task.logs = log_line

        task.updated_at = datetime.utcnow()
        self.db.add(task)
        self.db.commit()
        self.db.refresh(task)
