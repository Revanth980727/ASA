import time

from datetime import datetime

from typing import Optional

from sqlalchemy.orm import Session

from app.database import SessionLocal

from app.models import Task

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

        Fake pipeline:

        - CLONING_REPO

        - INDEXING_CODE

        - COMPLETED

        """

        # Step 1 - CLONING_REPO

        if not self._set_status(task_id, "CLONING_REPO"):

            # Task not found, nothing else to do

            return

        time.sleep(2)  # simulate work

        # Step 2 - INDEXING_CODE

        if not self._set_status(task_id, "INDEXING_CODE"):

            return

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

        # TODO: later, add real actions for each state:

        # if new_status == "CLONING_REPO":

        #     repo_manager.clone_repo(task)

        # elif new_status == "INDEXING_CODE":

        #     code_index.build_index(task)

        # etc.

        return True
