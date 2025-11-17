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

        - RUNNING_TESTS_BEFORE_FIX

        - [later: GENERATING_FIX, APPLYING_FIX]

        - RUNNING_TESTS_AFTER_FIX

        - COMPLETED/FAILED

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

        # Step 2 - INDEXING_CODE
        # Load task to get workspace_path
        task = self.db.query(Task).filter(Task.id == task_id).first()
        if not task or not task.workspace_path:
            self._add_log(task_id, "No workspace_path, skipping indexing")
            self._set_status(task_id, "FAILED")
            return
        else:
            try:
                from app.services.code_index import CodeIndex
                
                index = CodeIndex(task.workspace_path)
                index.build_index()
                self._add_log(task_id, f"Indexed {len(index.file_contents)} Python files")
            except Exception as e:
                error_msg = f"Failed to index code: {str(e)}"
                self._add_log(task_id, error_msg)
                self._set_status(task_id, "FAILED")
                return

        # Step 3 - RUNNING_TESTS_BEFORE_FIX
        if not self._set_status(task_id, "RUNNING_TESTS_BEFORE_FIX"):
            return

        # Load task again to get latest state
        task = self.db.query(Task).filter(Task.id == task_id).first()
        if not task or not task.workspace_path:
            self._add_log(task_id, "No workspace_path, cannot run tests")
            self._set_status(task_id, "FAILED")
            return

        try:
            from app.services.test_runner import run_tests

            tests_passed, test_output = run_tests(task.workspace_path, task.test_command)

            # Truncate test output to avoid DB bloat (keep last 5000 chars)
            truncated_output = test_output
            if len(test_output) > 5000:
                truncated_output = "... [truncated] ...\n" + test_output[-5000:]

            if tests_passed:
                # Tests pass - no bug to fix
                self._add_log(task_id, f"Tests passed. Output:\n{truncated_output}")
                self._add_log(task_id, "No failing tests found, nothing to fix")
                self._set_status(task_id, "FAILED")
                return
            else:
                # Tests fail - we've reproduced the bug
                self._add_log(task_id, f"Tests failed (bug reproduced). Output:\n{truncated_output}")
                # Store the failing output for use in fix generation
                task.test_output_before = truncated_output
                self.db.add(task)
                self.db.commit()

        except Exception as e:
            error_msg = f"Failed to run tests: {str(e)}"
            self._add_log(task_id, error_msg)
            self._set_status(task_id, "FAILED")
            return

        # Step 4 - GENERATING_FIX
        if not self._set_status(task_id, "GENERATING_FIX"):
            return

        # Load task again to get latest state
        task = self.db.query(Task).filter(Task.id == task_id).first()
        if not task or not task.workspace_path:
            self._add_log(task_id, "No workspace_path, cannot generate fix")
            self._set_status(task_id, "FAILED")
            return

        try:
            from app.services.fix_agent import FixAgent, apply_patches
            from app.services.code_index import CodeIndex

            # Rebuild code index
            index = CodeIndex(task.workspace_path)
            index.build_index()

            # Initialize FixAgent
            fix_agent = FixAgent()

            # Generate patches
            self._add_log(task_id, "Calling LLM to generate fix...")
            patches = fix_agent.generate_patch(
                task=task,
                failing_output=task.test_output_before or "",
                code_index=index
            )

            self._add_log(task_id, f"Generated {len(patches)} patch(es)")

            # Apply patches
            apply_patches(patches, workspace_path=task.workspace_path)
            self._add_log(task_id, "Applied patches to source files")

        except Exception as e:
            error_msg = f"Failed to generate or apply fix: {str(e)}"
            self._add_log(task_id, error_msg)
            self._set_status(task_id, "FAILED")
            return

        # Step 5 - RUNNING_TESTS_AFTER_FIX
        if not self._set_status(task_id, "RUNNING_TESTS_AFTER_FIX"):
            return

        # Load task again
        task = self.db.query(Task).filter(Task.id == task_id).first()
        if not task or not task.workspace_path:
            self._add_log(task_id, "No workspace_path, cannot run tests")
            self._set_status(task_id, "FAILED")
            return

        try:
            from app.services.test_runner import run_tests

            tests_passed, test_output = run_tests(task.workspace_path, task.test_command)

            # Truncate test output
            truncated_output = test_output
            if len(test_output) > 5000:
                truncated_output = "... [truncated] ...\n" + test_output[-5000:]

            if tests_passed:
                # Success! Fix worked
                self._add_log(task_id, f"Tests passed after fix! Output:\n{truncated_output}")
                # Continue to PR creation
            else:
                # Fix didn't work
                self._add_log(task_id, f"Tests still failing after fix. Output:\n{truncated_output}")
                self._set_status(task_id, "FAILED")
                return

        except Exception as e:
            error_msg = f"Failed to run tests after fix: {str(e)}"
            self._add_log(task_id, error_msg)
            self._set_status(task_id, "FAILED")
            return

        # Step 6 - CREATING_PR_BRANCH
        if not self._set_status(task_id, "CREATING_PR_BRANCH"):
            return

        # Load task again
        task = self.db.query(Task).filter(Task.id == task_id).first()
        if not task or not task.workspace_path:
            self._add_log(task_id, "No workspace_path, cannot create PR branch")
            self._set_status(task_id, "FAILED")
            return

        try:
            from app.services.repo_manager import create_pr_branch_local

            # Create branch and commit changes
            # For v0.1: don't push to remote (set to False)
            # Later: can set to True to enable push
            push_to_remote = False

            branch_name = create_pr_branch_local(
                workspace_path=task.workspace_path,
                task_id=task_id,
                push_to_remote=push_to_remote
            )

            # Store branch name in task
            task.branch_name = branch_name
            self.db.add(task)
            self.db.commit()

            self._add_log(task_id, f"Created branch: {branch_name}")

            if push_to_remote:
                self._add_log(task_id, f"Branch pushed to remote: {branch_name}")
            else:
                self._add_log(task_id, f"Branch created locally (not pushed to remote)")

            # Mark as completed
            self._set_status(task_id, "COMPLETED")
            return

        except Exception as e:
            error_msg = f"Failed to create PR branch: {str(e)}"
            self._add_log(task_id, error_msg)
            # Still mark as completed since the fix worked, just PR creation failed
            self._add_log(task_id, "Fix was successful, but PR branch creation failed")
            self._set_status(task_id, "COMPLETED")
            return

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
