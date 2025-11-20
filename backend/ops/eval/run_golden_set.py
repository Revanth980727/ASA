"""
Evaluation framework for running golden test set.

This script:
1. Loads the golden set of 25 test cases
2. Runs ASA on each case
3. Records results (pass/fail, time, cost)
4. Generates aggregate metrics
5. Compares against success criteria

Usage:
    python ops/eval/run_golden_set.py
    python ops/eval/run_golden_set.py --load-only  # Just load cases to DB
    python ops/eval/run_golden_set.py --case-name python_simple_syntax_error  # Run single case
"""

import sys
import json
import time
import argparse
from pathlib import Path
from datetime import datetime

# Add backend to path
backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

from app.database import SessionLocal, engine
from app.models import Base, EvaluationCase, EvaluationResult, Task, LLMUsage
from app.services.autonomous_orchestrator import AutonomousOrchestrator
from sqlalchemy import func
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)


def load_golden_set(db_session) -> list:
    """Load golden set from JSON file into database."""
    golden_set_path = backend_dir / "ops" / "golden_set.json"

    if not golden_set_path.exists():
        logger.error(f"Golden set file not found: {golden_set_path}")
        return []

    with open(golden_set_path, "r") as f:
        cases = json.load(f)

    loaded = []
    for case_data in cases:
        # Check if case already exists
        existing = db_session.query(EvaluationCase).filter(
            EvaluationCase.name == case_data["name"]
        ).first()

        if existing:
            logger.info(f"Case already exists: {case_data['name']}")
            loaded.append(existing)
            continue

        # Create new case
        case = EvaluationCase(
            name=case_data["name"],
            repo_url=case_data["repo_url"],
            bug_description=case_data["bug_description"],
            test_command=case_data.get("test_command"),
            expected_behavior=case_data["expected_behavior"],
            difficulty=case_data.get("difficulty", "medium"),
            category=case_data.get("category"),
            metadata=json.dumps(case_data.get("metadata", {}))
        )
        db_session.add(case)
        loaded.append(case)
        logger.info(f"Loaded case: {case_data['name']}")

    db_session.commit()
    return loaded


def run_evaluation_case(case: EvaluationCase, db_session) -> dict:
    """Run a single evaluation case."""
    logger.info(f"Running evaluation: {case.name}")

    # Create task from evaluation case
    task = Task(
        repo_url=case.repo_url,
        bug_description=case.bug_description,
        test_command=case.test_command,
        status="QUEUED"
    )
    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)

    start_time = time.time()

    try:
        # Run orchestrator
        orchestrator = AutonomousOrchestrator()
        result = orchestrator.start_task(task.id)

        execution_time = time.time() - start_time

        # Refresh task to get latest data
        db_session.refresh(task)

        # Determine if passed
        passed = (
            result.get("status") == "COMPLETED" and
            task.pr_url is not None and
            task.status == "COMPLETED"
        )

        # Calculate total cost
        total_cost = db_session.query(func.sum(LLMUsage.cost_usd)).filter(
            LLMUsage.task_id == task.id
        ).scalar() or 0.0

        # Create evaluation result
        eval_result = EvaluationResult(
            evaluation_case_id=case.id,
            task_id=task.id,
            passed=passed,
            execution_time_seconds=execution_time,
            cost_usd=total_cost,
            metrics=json.dumps({
                "status": result.get("status"),
                "has_pr": task.pr_url is not None,
                "final_task_status": task.status
            })
        )
        db_session.add(eval_result)
        db_session.commit()

        logger.info(
            f"Case {case.name}: {'PASSED' if passed else 'FAILED'} "
            f"in {execution_time:.2f}s, cost ${total_cost:.4f}"
        )

        return {
            "case_name": case.name,
            "passed": passed,
            "execution_time": execution_time,
            "cost_usd": total_cost,
            "task_id": task.id
        }

    except Exception as e:
        logger.error(f"Error running case {case.name}: {e}", exc_info=True)

        execution_time = time.time() - start_time

        # Record failure
        eval_result = EvaluationResult(
            evaluation_case_id=case.id,
            task_id=task.id,
            passed=False,
            execution_time_seconds=execution_time,
            reviewer_notes=f"Execution error: {str(e)}"
        )
        db_session.add(eval_result)
        db_session.commit()

        return {
            "case_name": case.name,
            "passed": False,
            "execution_time": execution_time,
            "error": str(e),
            "task_id": task.id
        }


def generate_report(results: list) -> dict:
    """Generate aggregate metrics and report."""
    total = len(results)
    passed = sum(1 for r in results if r["passed"])
    failed = total - passed

    success_rate = (passed / total * 100) if total > 0 else 0

    total_time = sum(r["execution_time"] for r in results)
    avg_time = total_time / total if total > 0 else 0

    total_cost = sum(r.get("cost_usd", 0) for r in results)
    avg_cost = total_cost / total if total > 0 else 0

    report = {
        "timestamp": datetime.utcnow().isoformat(),
        "total_cases": total,
        "passed": passed,
        "failed": failed,
        "success_rate_percent": round(success_rate, 2),
        "total_execution_time_seconds": round(total_time, 2),
        "avg_execution_time_seconds": round(avg_time, 2),
        "total_cost_usd": round(total_cost, 4),
        "avg_cost_per_case_usd": round(avg_cost, 4),
        "results": results
    }

    # Check against success criteria (from FROZEN spec)
    # Success criteria: 80% success rate on golden set
    meets_criteria = success_rate >= 80.0

    report["meets_success_criteria"] = meets_criteria
    report["success_criteria"] = {
        "required_success_rate": 80.0,
        "actual_success_rate": round(success_rate, 2),
        "status": "PASS" if meets_criteria else "FAIL"
    }

    return report


def print_report(report: dict):
    """Print evaluation report in a readable format."""
    print("\n" + "=" * 70)
    print("ASA GOLDEN SET EVALUATION REPORT")
    print("=" * 70)
    print(f"\nTimestamp: {report['timestamp']}")
    print(f"\nTotal Cases: {report['total_cases']}")
    print(f"Passed: {report['passed']}")
    print(f"Failed: {report['failed']}")
    print(f"Success Rate: {report['success_rate_percent']}%")
    print(f"\nTotal Execution Time: {report['total_execution_time_seconds']:.2f}s")
    print(f"Average Time per Case: {report['avg_execution_time_seconds']:.2f}s")
    print(f"\nTotal Cost: ${report['total_cost_usd']:.4f}")
    print(f"Average Cost per Case: ${report['avg_cost_per_case_usd']:.4f}")

    print("\n" + "-" * 70)
    print("SUCCESS CRITERIA")
    print("-" * 70)
    criteria = report["success_criteria"]
    print(f"Required Success Rate: {criteria['required_success_rate']}%")
    print(f"Actual Success Rate: {criteria['actual_success_rate']}%")
    print(f"Status: {criteria['status']}")

    print("\n" + "-" * 70)
    print("INDIVIDUAL RESULTS")
    print("-" * 70)
    for result in report["results"]:
        status = "✓ PASS" if result["passed"] else "✗ FAIL"
        print(
            f"{status} | {result['case_name']:<40} | "
            f"{result['execution_time']:>6.2f}s | "
            f"${result.get('cost_usd', 0):>7.4f}"
        )

    print("=" * 70 + "\n")


def main():
    parser = argparse.ArgumentParser(description="Run ASA Golden Set Evaluation")
    parser.add_argument(
        "--load-only",
        action="store_true",
        help="Only load cases to database, don't run evaluation"
    )
    parser.add_argument(
        "--case-name",
        type=str,
        help="Run only a specific case by name"
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Save report to JSON file"
    )

    args = parser.parse_args()

    # Create tables if needed
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()

    try:
        # Load golden set
        logger.info("Loading golden set...")
        cases = load_golden_set(db)
        logger.info(f"Loaded {len(cases)} evaluation cases")

        if args.load_only:
            logger.info("Load-only mode, exiting")
            return

        # Filter to specific case if requested
        if args.case_name:
            cases = [c for c in cases if c.name == args.case_name]
            if not cases:
                logger.error(f"Case not found: {args.case_name}")
                return
            logger.info(f"Running single case: {args.case_name}")

        # Run evaluation
        results = []
        for case in cases:
            result = run_evaluation_case(case, db)
            results.append(result)

        # Generate report
        report = generate_report(results)

        # Print report
        print_report(report)

        # Save to file if requested
        if args.output:
            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w") as f:
                json.dump(report, f, indent=2)
            logger.info(f"Report saved to: {output_path}")

    except Exception as e:
        logger.error(f"Error running evaluation: {e}", exc_info=True)
    finally:
        db.close()


if __name__ == "__main__":
    main()
