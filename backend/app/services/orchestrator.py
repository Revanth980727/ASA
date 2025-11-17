import time
import sys
import os
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
                # Use SemanticCodeIndex for better context (falls back to CodeIndex if unavailable)
                try:
                    from app.services.semantic_index import SemanticCodeIndex

                    index = SemanticCodeIndex(task.workspace_path)
                    index.build_index()
                    stats = index.get_stats()
                    self._add_log(task_id, f"Semantic index built: {stats['total_nodes']} nodes "
                                          f"({stats['functions']} functions, {stats['classes']} classes, "
                                          f"{stats['methods']} methods)")
                except ImportError as e:
                    # Fall back to simple CodeIndex
                    self._add_log(task_id, "Semantic indexing not available, using simple index")
                    from app.services.code_index import CodeIndex

                    index = CodeIndex(task.workspace_path)
                    index.build_index()
                    self._add_log(task_id, f"Indexed {len(index.file_contents)} Python files")
            except Exception as e:
                error_msg = f"Failed to index code: {str(e)}"
                self._add_log(task_id, error_msg)
                self._set_status(task_id, "FAILED")
                return

        # Step 2.5 - VERIFYING_BUG_BEHAVIOR (optional CIT Agent step)
        enable_cit = os.getenv("ENABLE_CIT_AGENT", "false").lower() == "true"

        if enable_cit:
            if not self._set_status(task_id, "VERIFYING_BUG_BEHAVIOR"):
                return

            task = self.db.query(Task).filter(Task.id == task_id).first()
            if not task or not task.workspace_path:
                self._add_log(task_id, "No workspace_path, skipping behavioral verification")
            else:
                try:
                    from app.services.cit_agent import CITAgent

                    self._add_log(task_id, "Generating E2E test to verify bug behavior...")

                    cit_agent = CITAgent(use_docker=True)

                    # Verify bug exists using behavioral test
                    bug_exists, test_result, test_file = cit_agent.verify_bug(
                        bug_description=task.bug_description,
                        workspace_path=task.workspace_path,
                        app_context=""  # Could be enhanced with repo context
                    )

                    # Log results
                    self._add_log(task_id, f"Behavioral test result: {test_result.get_summary()}")

                    if bug_exists:
                        self._add_log(task_id, "✓ Bug confirmed by behavioral test (test failed as expected)")
                        self._add_log(task_id, f"Test file: {test_file}")

                        # Store test file path for later verification
                        task.e2e_test_path = test_file
                        self.db.add(task)
                        self.db.commit()
                    else:
                        self._add_log(task_id, "⚠ Behavioral test passed - bug may not be reproducible via E2E test")
                        self._add_log(task_id, "Continuing with unit test verification...")

                except Exception as e:
                    # Don't fail the whole pipeline if CIT fails
                    error_msg = f"CIT Agent error (non-fatal): {str(e)}"
                    self._add_log(task_id, error_msg)
                    self._add_log(task_id, "Continuing with unit test verification...")

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
            # Try enhanced CodeAgent first, fall back to legacy FixAgent
            use_enhanced = True
            try:
                from app.services.code_agent import CodeAgent
                from app.services.patch_applicator import PatchApplicator
            except ImportError:
                use_enhanced = False
                from app.services.fix_agent import FixAgent, apply_patches

            # Rebuild code index with semantic search
            try:
                from app.services.semantic_index import SemanticCodeIndex

                index = SemanticCodeIndex(task.workspace_path)
                index.build_index()
                self._add_log(task_id, "Using semantic search for context")
            except ImportError:
                # Fall back to simple CodeIndex
                from app.services.code_index import CodeIndex

                index = CodeIndex(task.workspace_path)
                index.build_index()
                self._add_log(task_id, "Using simple search for context")

            if use_enhanced:
                # Use enhanced Code Agent with structured patches
                self._add_log(task_id, "Using enhanced Code Agent (line-accurate patches)")

                agent = CodeAgent()

                # Get code context
                if hasattr(index, 'get_context'):
                    code_context = index.get_context(task.bug_description, max_results=5)
                else:
                    snippets = index.search(task.bug_description, max_results=5)
                    context_parts = []
                    for i, snippet in enumerate(snippets, 1):
                        context_parts.append(
                            f"### File {i}: {snippet.file_path} (lines {snippet.start_line}-{snippet.end_line})\n"
                            f"```python\n{snippet.snippet}\n```"
                        )
                    code_context = "\n\n".join(context_parts)

                # Generate patches
                self._add_log(task_id, "Generating structured patches...")
                patch_set = agent.generate_fix(
                    bug_description=task.bug_description,
                    test_failure_log=task.test_output_before or "",
                    code_context=code_context
                )

                self._add_log(task_id,
                             f"Generated {len(patch_set.patches)} patch(es) "
                             f"(confidence: {patch_set.confidence:.2f})")
                self._add_log(task_id, f"Rationale: {patch_set.rationale}")

                # Apply patches
                applicator = PatchApplicator(task.workspace_path, create_backups=True)
                results = applicator.apply_patch_set(patch_set, dry_run=False, fail_fast=False)

                if results["success"]:
                    self._add_log(task_id,
                                 f"Applied {results['applied']} patch(es) successfully")
                else:
                    self._add_log(task_id,
                                 f"Patch application completed with {results['failed']} error(s)")
                    for error in results["errors"]:
                        self._add_log(task_id, f"  - {error}")

            else:
                # Fall back to legacy FixAgent
                self._add_log(task_id, "Using legacy FixAgent")

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
                # Continue to behavioral verification if enabled
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

        # Step 5.5 - VERIFYING_FIX_BEHAVIOR (optional CIT Agent verification)
        enable_cit = os.getenv("ENABLE_CIT_AGENT", "false").lower() == "true"

        if enable_cit:
            task = self.db.query(Task).filter(Task.id == task_id).first()

            # Check if we have a behavioral test to re-run
            if task and hasattr(task, 'e2e_test_path') and task.e2e_test_path:
                if not self._set_status(task_id, "VERIFYING_FIX_BEHAVIOR"):
                    return

                try:
                    from app.services.cit_agent import CITAgent

                    self._add_log(task_id, "Re-running E2E test to verify fix...")

                    cit_agent = CITAgent(use_docker=True)

                    # Verify fix works
                    fix_works, test_result = cit_agent.verify_fix(
                        test_file_path=task.e2e_test_path,
                        workspace_path=task.workspace_path
                    )

                    self._add_log(task_id, f"Behavioral verification: {test_result.get_summary()}")

                    if fix_works:
                        self._add_log(task_id, "✓ Fix confirmed by behavioral test (E2E test now passes)")
                    else:
                        self._add_log(task_id, "⚠ E2E test still failing, but unit tests pass")
                        self._add_log(task_id, test_result.get_failure_details())
                        # Don't fail - unit tests passed, E2E might need different fix

                except Exception as e:
                    error_msg = f"CIT verification error (non-fatal): {str(e)}"
                    self._add_log(task_id, error_msg)

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
