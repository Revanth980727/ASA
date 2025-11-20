"""
Autonomous Orchestrator - State machine-driven workflow execution.

Features:
- State machine orchestration
- Retry logic
- Failure handling
- State persistence
- Comprehensive logging
"""

import os
import sys
import time
from pathlib import Path
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import Task
from app.services.state_machine import StateMachine, TaskState, TransitionCondition

# Add project root to path
_orchestrator_file = Path(__file__).resolve()
project_root = _orchestrator_file.parent.parent.parent.parent
if project_root.exists():
    sys.path.insert(0, str(project_root))


class AutonomousOrchestrator:
    """
    Enhanced orchestrator with state machine and autonomous workflow.

    Handles:
    - State transitions
    - Retry logic
    - Failure recovery
    - Conditional branching
    - State persistence
    """

    def __init__(self, db: Session = None, enable_cit: bool = None, cancellation_callback=None):
        """
        Initialize orchestrator.

        Args:
            db: Database session (optional, will create one if not provided)
            enable_cit: Enable CIT Agent (overrides env var if provided)
            cancellation_callback: Optional callback function to check if task should be cancelled
        """
        self.db = db if db is not None else SessionLocal()
        self._owns_db = db is None  # Track if we created the session

        # Check CIT enablement
        if enable_cit is None:
            enable_cit = os.getenv("ENABLE_CIT_AGENT", "false").lower() == "true"

        self.enable_cit = enable_cit
        self.cancellation_callback = cancellation_callback

    @staticmethod
    def start_task(task_id: str) -> None:
        """
        Entry point for background task execution.

        Args:
            task_id: ID of task to process
        """
        db = SessionLocal()
        try:
            orchestrator = AutonomousOrchestrator(db=db)
            orchestrator.run(task_id)
        finally:
            db.close()

    def run(self, task_id: str) -> None:
        """
        Execute autonomous workflow for a task.

        Args:
            task_id: Task ID to process
        """
        # Load task
        task = self.db.query(Task).filter(Task.id == task_id).first()
        if not task:
            print(f"Task {task_id} not found")
            return

        # Initialize state machine
        state_machine = StateMachine(enable_cit=self.enable_cit)

        # Transition from QUEUED to INIT
        self._log(task_id, "Starting autonomous workflow")
        state_machine.transition("success")

        # Main workflow loop
        while not state_machine.is_terminal():
            current_state = state_machine.get_current_state()

            try:
                # Execute state handler
                result = self._execute_state(task_id, current_state, state_machine)

                # Transition to next state
                next_state = state_machine.transition(result)

                self._log(task_id, f"Transitioned: {current_state.value} → {next_state.value}")

            except Exception as e:
                error_msg = f"Error in {current_state.value}: {str(e)}"
                self._log(task_id, error_msg)

                # Try to transition to failure state
                try:
                    state_machine.transition("failure", error=str(e))
                except ValueError:
                    # No valid failure transition, force FAILED state
                    task.status = TaskState.FAILED.value
                    self.db.commit()
                    break

        # Workflow complete
        final_state = state_machine.get_current_state()
        self._log(task_id, f"Workflow complete: {final_state.value}")

        # Update task status
        task.status = final_state.value
        self.db.commit()

        # Log summary
        summary = state_machine.get_summary()
        self._log(task_id, f"Total duration: {summary['total_duration_seconds']:.2f}s")
        self._log(task_id, f"States visited: {summary['total_states']}")

        # Visualize workflow
        visualization = state_machine.visualize()
        self._log(task_id, f"\n{visualization}")

    def _execute_state(self, task_id: str, state: TaskState, state_machine: StateMachine) -> str:
        """
        Execute logic for a specific state.

        Args:
            task_id: Task ID
            state: Current state
            state_machine: State machine instance

        Returns:
            Result condition (success, failure, etc.)
        """
        # Update task status in DB
        task = self.db.query(Task).filter(Task.id == task_id).first()
        if task:
            task.status = state.value
            task.updated_at = datetime.utcnow()
            self.db.commit()

        # Execute state-specific logic
        if state == TaskState.INIT:
            return self._state_init(task_id)

        elif state == TaskState.CLONING_REPO:
            return self._state_clone_repo(task_id)

        elif state == TaskState.INDEXING_CODE:
            return self._state_index_code(task_id)

        elif state == TaskState.VERIFYING_BUG_BEHAVIOR:
            return self._state_verify_bug_behavior(task_id)

        elif state == TaskState.RUNNING_TESTS_BEFORE_FIX:
            return self._state_run_tests_before(task_id)

        elif state == TaskState.GENERATING_FIX:
            return self._state_generate_fix(task_id)

        elif state == TaskState.RUNNING_TESTS_AFTER_FIX:
            return self._state_run_tests_after(task_id)

        elif state == TaskState.VERIFYING_FIX_BEHAVIOR:
            return self._state_verify_fix_behavior(task_id)

        elif state == TaskState.CREATING_PR_BRANCH:
            return self._state_create_pr_branch(task_id)

        elif state == TaskState.RETRY:
            return self._state_retry(task_id)

        else:
            raise ValueError(f"Unknown state: {state}")

    # State handlers

    def _state_init(self, task_id: str) -> str:
        """Initialize task."""
        self._log(task_id, "Initializing task")
        return "success"

    def _state_clone_repo(self, task_id: str) -> str:
        """Clone repository."""
        task = self.db.query(Task).filter(Task.id == task_id).first()

        try:
            from app.services.repo_manager import create_workspace, clone_repo

            workspace_path = create_workspace(task_id)
            task.workspace_path = workspace_path
            self.db.commit()

            clone_repo(task.repo_url, workspace_path)
            self._log(task_id, f"Cloned {task.repo_url} to {workspace_path}")

            return "success"

        except Exception as e:
            self._log(task_id, f"Clone failed: {e}")
            return "failure"

    def _state_index_code(self, task_id: str) -> str:
        """Index codebase."""
        task = self.db.query(Task).filter(Task.id == task_id).first()

        try:
            # Try semantic indexing first
            try:
                self._log(task_id, "Attempting semantic indexing...")
                from app.services.semantic_index import SemanticCodeIndex

                self._log(task_id, f"Creating semantic index for {task.workspace_path}")
                index = SemanticCodeIndex(task.workspace_path)

                self._log(task_id, "Building index...")
                index.build_index()

                stats = index.get_stats()
                self._log(task_id, f"Semantic index: {stats['total_nodes']} nodes")

            except ImportError as ie:
                # Fall back to simple index
                self._log(task_id, f"Semantic indexing not available ({ie}), using simple index...")
                from app.services.code_index import CodeIndex

                self._log(task_id, f"Creating simple index for {task.workspace_path}")
                index = CodeIndex(task.workspace_path)

                self._log(task_id, "Building index...")
                index.build_index()

                self._log(task_id, f"Simple index: {len(index.file_contents)} files")

            return "success"

        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            self._log(task_id, f"Indexing failed: {e}\n{error_details}")
            return "failure"

    def _state_verify_bug_behavior(self, task_id: str) -> str:
        """Verify bug with CIT Agent E2E test."""
        task = self.db.query(Task).filter(Task.id == task_id).first()

        try:
            from app.services.cit_agent import CITAgent

            cit_agent = CITAgent(use_docker=True)

            bug_exists, test_result, test_file = cit_agent.verify_bug(
                bug_description=task.bug_description,
                workspace_path=task.workspace_path
            )

            self._log(task_id, f"E2E test: {test_result.get_summary()}")

            task.e2e_test_path = test_file
            self.db.commit()

            return "bug_confirmed" if bug_exists else "bug_not_found"

        except Exception as e:
            self._log(task_id, f"CIT verification failed (non-fatal): {e}")
            return "bug_not_found"  # Continue with unit tests

    def _state_run_tests_before(self, task_id: str) -> str:
        """Run tests to verify bug exists."""
        task = self.db.query(Task).filter(Task.id == task_id).first()

        try:
            from app.services.test_runner import run_tests

            tests_passed, test_output = run_tests(task.workspace_path, task.test_command)

            # Truncate output
            truncated = test_output[-5000:] if len(test_output) > 5000 else test_output

            task.test_output_before = truncated
            self.db.commit()

            if tests_passed:
                self._log(task_id, "Tests pass - no bug found")
                return "tests_pass"
            else:
                self._log(task_id, "Tests fail - bug confirmed")
                return "tests_fail"

        except Exception as e:
            self._log(task_id, f"Test execution failed: {e}")
            return "failure"

    def _state_generate_fix(self, task_id: str) -> str:
        """Generate and apply fix."""
        task = self.db.query(Task).filter(Task.id == task_id).first()

        try:
            # Try enhanced CodeAgent first
            try:
                from app.services.code_agent import CodeAgent
                from app.services.patch_applicator import PatchApplicator

                # Build index and get context
                try:
                    from app.services.semantic_index import SemanticCodeIndex
                    index = SemanticCodeIndex(task.workspace_path)
                    index.build_index()
                    # Increased from 5 to 10 for better coverage
                    code_context = index.get_context(task.bug_description, max_results=10)

                    # If no results found, add a warning
                    if "No relevant code found" in code_context:
                        self._log(task_id, "Warning: Semantic search found no results, adding file list")
                        code_context += self._get_file_list_context(task.workspace_path)

                except ImportError:
                    from app.services.code_index import CodeIndex
                    index = CodeIndex(task.workspace_path)
                    index.build_index()
                    # Increased from 5 to 10 for better coverage
                    snippets = index.search(task.bug_description, max_results=10)

                    if not snippets:
                        self._log(task_id, "Warning: No code snippets found, adding file list")
                        context_parts = [self._get_file_list_context(task.workspace_path)]
                    else:
                        context_parts = [
                            f"### {s.file_path} (lines {s.start_line}-{s.end_line})\n```python\n{s.snippet}\n```"
                            for s in snippets
                        ]
                    code_context = "\n\n".join(context_parts)

                # Generate fix
                agent = CodeAgent()
                patch_set = agent.generate_fix(
                    bug_description=task.bug_description,
                    test_failure_log=task.test_output_before or "",
                    code_context=code_context
                )

                self._log(task_id, f"Generated {len(patch_set.patches)} patches (confidence: {patch_set.confidence:.2f})")

                # Apply patches
                applicator = PatchApplicator(task.workspace_path, create_backups=True)
                results = applicator.apply_patch_set(patch_set)

                if results["success"]:
                    self._log(task_id, f"Applied {results['applied']} patches")
                    return "success"
                else:
                    self._log(task_id, f"Patch application failed: {results['errors']}")
                    return "failure"

            except ImportError:
                # Fall back to legacy FixAgent
                from app.services.fix_agent import FixAgent, apply_patches
                from app.services.code_index import CodeIndex

                index = CodeIndex(task.workspace_path)
                index.build_index()

                agent = FixAgent()
                patches = agent.generate_patch(task=task, failing_output=task.test_output_before or "", code_index=index)

                apply_patches(patches, workspace_path=task.workspace_path)
                self._log(task_id, f"Applied {len(patches)} legacy patches")
                return "success"

        except Exception as e:
            self._log(task_id, f"Fix generation failed: {e}")
            return "failure"

    def _state_run_tests_after(self, task_id: str) -> str:
        """Run tests after applying fix."""
        task = self.db.query(Task).filter(Task.id == task_id).first()

        try:
            from app.services.test_runner import run_tests

            tests_passed, test_output = run_tests(task.workspace_path, task.test_command)

            truncated = test_output[-5000:] if len(test_output) > 5000 else test_output
            self._log(task_id, f"Test result: {'PASS' if tests_passed else 'FAIL'}")

            if tests_passed:
                return "tests_pass"
            else:
                return "tests_fail"

        except Exception as e:
            self._log(task_id, f"Test execution failed: {e}")
            return "failure"

    def _state_verify_fix_behavior(self, task_id: str) -> str:
        """Verify fix with CIT Agent E2E test."""
        task = self.db.query(Task).filter(Task.id == task_id).first()

        if not hasattr(task, 'e2e_test_path') or not task.e2e_test_path:
            self._log(task_id, "No E2E test to verify")
            return "fix_invalid"  # Continue anyway

        try:
            from app.services.cit_agent import CITAgent

            cit_agent = CITAgent(use_docker=True)
            fix_works, test_result = cit_agent.verify_fix(
                test_file_path=task.e2e_test_path,
                workspace_path=task.workspace_path
            )

            self._log(task_id, f"E2E verification: {test_result.get_summary()}")

            return "fix_validated" if fix_works else "fix_invalid"

        except Exception as e:
            self._log(task_id, f"CIT verification failed (non-fatal): {e}")
            return "fix_invalid"  # Continue anyway

    def _state_create_pr_branch(self, task_id: str) -> str:
        """Create PR branch."""
        task = self.db.query(Task).filter(Task.id == task_id).first()

        try:
            from app.services.repo_manager import create_pr_branch_local

            branch_name = create_pr_branch_local(
                workspace_path=task.workspace_path,
                task_id=task_id,
                push_to_remote=False
            )

            task.branch_name = branch_name
            self.db.commit()

            self._log(task_id, f"Created branch: {branch_name}")
            return "success"

        except Exception as e:
            self._log(task_id, f"PR branch creation failed (non-fatal): {e}")
            return "failure"  # Still mark as success overall

    def _state_retry(self, task_id: str) -> str:
        """
        Handle retry state.

        The state machine handles the retry logic automatically,
        so this method just returns success to trigger the transition.
        """
        self._log(task_id, "Retrying previous operation...")
        return "success"

    # Utility methods

    def _get_file_list_context(self, workspace_path: str) -> str:
        """Get a list of all Python files as fallback context."""
        from pathlib import Path

        workspace = Path(workspace_path)
        python_files = []
        skip_dirs = {'.git', 'venv', 'node_modules', '__pycache__', '.venv', 'dist', 'build'}

        for py_file in workspace.rglob('*.py'):
            # Skip certain directories
            if any(part in skip_dirs for part in py_file.parts):
                continue

            rel_path = py_file.relative_to(workspace)
            python_files.append(str(rel_path))

            if len(python_files) >= 20:  # Limit to first 20 files
                break

        return f"\n### File List (first {len(python_files)} Python files)\n" + "\n".join(f"- {f}" for f in python_files)

    def _log(self, task_id: str, message: str) -> None:
        """Add log message to task."""
        task = self.db.query(Task).filter(Task.id == task_id).first()
        if not task:
            return

        timestamp = datetime.utcnow().isoformat()
        log_line = f"[{timestamp}] {message}"

        existing_logs = task.logs or ""
        task.logs = existing_logs + "\n" + log_line if existing_logs else log_line

        task.updated_at = datetime.utcnow()
        self.db.commit()

        print(log_line)
