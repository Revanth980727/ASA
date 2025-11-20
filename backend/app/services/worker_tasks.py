"""
Worker task functions that execute in RQ background jobs.

These functions are the actual work that gets executed by RQ workers.
They wrap the autonomous orchestrator with proper error handling and cancellation checks.
"""

import logging
from typing import Optional
from rq import get_current_job
from sqlalchemy import func

from app.database import SessionLocal
from app.services.autonomous_orchestrator import AutonomousOrchestrator
from app.services.queue import get_task_queue
from app.models import Task

logger = logging.getLogger(__name__)


def run_task_job(task_id: str) -> dict:
    """
    Execute a task in the background using the autonomous orchestrator.

    This function is called by RQ workers. It:
    1. Fetches the task from the database
    2. Runs the autonomous orchestrator
    3. Checks for cancellation signals periodically
    4. Updates task status on completion

    Args:
        task_id: The ID of the task to execute

    Returns:
        dict with execution results
    """
    job = get_current_job()
    job_id = job.id if job else "unknown"

    logger.info(f"Starting task {task_id} in job {job_id}")

    db = SessionLocal()
    try:
        # Fetch task
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            logger.error(f"Task {task_id} not found")
            return {"success": False, "error": "Task not found"}

        # Check if already cancelled before starting
        if job:
            queue = get_task_queue()
            if queue.is_job_cancelled(job_id):
                logger.info(f"Task {task_id} was cancelled before starting")
                task.status = "CANCELLED"
                task.logs = (task.logs or "") + "\n[Worker] Task cancelled before execution"
                db.commit()
                return {"success": False, "error": "Task cancelled"}

        # Create orchestrator with cancellation callback
        def check_cancellation():
            """Callback to check if job was cancelled."""
            if job:
                queue = get_task_queue()
                if queue.is_job_cancelled(job_id):
                    logger.info(f"Cancellation detected for task {task_id}")
                    return True
            return False

        orchestrator = AutonomousOrchestrator(
            db=db,
            cancellation_callback=check_cancellation
        )

        # Run the task
        try:
            result = orchestrator.run(task_id)

            # Handle None result (orchestrator.run() doesn't always return a dict)
            if result is None:
                result = {"status": "COMPLETED"}

            status = result.get("status", "UNKNOWN") if isinstance(result, dict) else "COMPLETED"
            logger.info(f"Task {task_id} completed with status: {status}")

            return {
                "success": True,
                "task_id": task_id,
                "status": status,
                "result": result
            }

        except Exception as e:
            logger.error(f"Error executing task {task_id}: {e}", exc_info=True)

            # Update task status to failed
            task = db.query(Task).filter(Task.id == task_id).first()
            if task:
                task.status = "FAILED"
                task.logs = (task.logs or "") + f"\n[Worker] Execution error: {str(e)}"
                db.commit()

            return {
                "success": False,
                "task_id": task_id,
                "error": str(e)
            }

    finally:
        db.close()


def run_evaluation_job(evaluation_case_id: str) -> dict:
    """
    Run a single evaluation case.

    Args:
        evaluation_case_id: The evaluation case to run

    Returns:
        dict with evaluation results
    """
    from app.models import EvaluationCase, EvaluationResult, Task
    import time

    logger.info(f"Starting evaluation for case {evaluation_case_id}")

    db = SessionLocal()
    try:
        # Fetch evaluation case
        eval_case = db.query(EvaluationCase).filter(
            EvaluationCase.id == evaluation_case_id
        ).first()

        if not eval_case:
            logger.error(f"Evaluation case {evaluation_case_id} not found")
            return {"success": False, "error": "Evaluation case not found"}

        # Create a task from the evaluation case
        task = Task(
            repo_url=eval_case.repo_url,
            bug_description=eval_case.bug_description,
            test_command=eval_case.test_command,
            status="QUEUED"
        )
        db.add(task)
        db.commit()
        db.refresh(task)

        start_time = time.time()

        # Run the task
        orchestrator = AutonomousOrchestrator()
        result = orchestrator.start_task(task.id)

        execution_time = time.time() - start_time

        # Evaluate the result
        passed = result.get("status") == "COMPLETED" and task.pr_url is not None

        # Get total cost from LLM usage
        from app.models import LLMUsage
        total_cost = db.query(func.sum(LLMUsage.cost_usd)).filter(
            LLMUsage.task_id == task.id
        ).scalar() or 0.0

        # Create evaluation result
        eval_result = EvaluationResult(
            evaluation_case_id=evaluation_case_id,
            task_id=task.id,
            passed=passed,
            execution_time_seconds=execution_time,
            cost_usd=total_cost,
            metrics={"status": result.get("status")}
        )
        db.add(eval_result)
        db.commit()

        logger.info(f"Evaluation case {evaluation_case_id} completed: {'PASSED' if passed else 'FAILED'}")

        return {
            "success": True,
            "evaluation_case_id": evaluation_case_id,
            "task_id": task.id,
            "passed": passed,
            "execution_time": execution_time,
            "cost_usd": total_cost
        }

    except Exception as e:
        logger.error(f"Error running evaluation {evaluation_case_id}: {e}", exc_info=True)
        return {"success": False, "error": str(e)}

    finally:
        db.close()
