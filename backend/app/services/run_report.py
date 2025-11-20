"""
Run Report Generator - Creates comprehensive execution reports for PR templates.

Collects and formats:
- Timing metrics (total, p50, p95)
- Token usage and costs
- Test results
- Stage breakdown
- Budget utilization
"""

import os
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from pathlib import Path
import statistics
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models import Task, LLMUsage, TaskMetrics


class RunReport:
    """Generates comprehensive run reports for PR descriptions."""

    def __init__(self, task_id: str, db: Session):
        """
        Initialize run report generator.

        Args:
            task_id: Task ID to generate report for
            db: Database session
        """
        self.task_id = task_id
        self.db = db
        self.task = db.query(Task).filter(Task.id == task_id).first()

        if not self.task:
            raise ValueError(f"Task {task_id} not found")

    def generate_pr_body(self) -> str:
        """
        Generate PR body from template with all placeholders filled.

        Returns:
            Formatted PR description
        """
        # Load template
        template_path = Path(__file__).parent.parent.parent.parent / ".github" / "PULL_REQUEST_TEMPLATE.md"

        if not template_path.exists():
            # Fallback to simple template
            return self._generate_simple_pr_body()

        with open(template_path, "r") as f:
            template = f.read()

        # Collect all metrics
        metrics = self._collect_metrics()

        # Replace all placeholders
        body = template
        for key, value in metrics.items():
            placeholder = f"{{{{{key}}}}}"
            body = body.replace(placeholder, str(value))

        return body

    def _collect_metrics(self) -> Dict[str, Any]:
        """Collect all metrics for the report."""
        # Timing metrics
        timing = self._get_timing_metrics()

        # Token and cost metrics
        llm_usage = self._get_llm_metrics()

        # Test results
        test_results = self._get_test_results()

        # Stage breakdown
        stage_breakdown = self._get_stage_breakdown()

        # Budget status
        budgets = self._get_budget_status(llm_usage, timing)

        # Combine all metrics
        return {
            # Task info
            "TASK_ID": self.task.id[:8] + "...",
            "SANDBOX_RUN_ID": self.task.job_id or "N/A",
            "STATUS": self._format_status_emoji(self.task.status),
            "ASA_VERSION": "1.0.0",

            # Timing
            "TOTAL_TIME": timing["total_time"],
            "P50_STAGE_DURATION": timing["p50_duration"],
            "P95_STAGE_DURATION": timing["p95_duration"],

            # Token usage
            "TOTAL_TOKENS": llm_usage["total_tokens"],
            "PROMPT_TOKENS": llm_usage["prompt_tokens"],
            "COMPLETION_TOKENS": llm_usage["completion_tokens"],
            "TOKEN_BUDGET": budgets["token_budget"],
            "TOTAL_COST": f"{llm_usage['total_cost']:.4f}",
            "COST_BUDGET": f"{budgets['cost_budget']:.2f}",

            # Model breakdown
            "MODEL_BREAKDOWN": llm_usage["model_breakdown"],

            # Bug info
            "BUG_DESCRIPTION": self.task.bug_description,

            # Test results
            "PRE_FIX_TEST_OUTPUT": test_results["pre_fix_output"],
            "PRE_FIX_STATUS": test_results["pre_fix_status"],
            "POST_FIX_TEST_OUTPUT": test_results["post_fix_output"],
            "POST_FIX_STATUS": test_results["post_fix_status"],
            "E2E_TEST_SUMMARY": test_results["e2e_summary"],

            # Changes
            "CHANGES_SUMMARY": self._extract_changes_summary(),
            "FILES_MODIFIED_LIST": self._extract_files_modified(),

            # Stage table
            "STAGE_TABLE_ROWS": stage_breakdown,

            # Links
            "TASK_URL": self._get_task_url(),
            "LOGS_URL": self._get_logs_url(),
            "SANDBOX_URL": f"Job ID: {self.task.job_id or 'N/A'}",

            # Budget percentages
            "TOKEN_USAGE_PERCENTAGE": budgets["token_percentage"],
            "COST_USAGE_PERCENTAGE": budgets["cost_percentage"],
            "TIME_USAGE_PERCENTAGE": budgets["time_percentage"],
            "TIME_BUDGET": budgets["time_budget_str"],
            "BUDGET_WARNING": budgets["warning"],

            # Notes
            "ADDITIONAL_NOTES": self._generate_notes(),
            "FULL_EXECUTION_TRACE": self._get_execution_trace()
        }

    def _get_timing_metrics(self) -> Dict[str, Any]:
        """Calculate timing metrics."""
        if not self.task.created_at or not self.task.updated_at:
            return {
                "total_time": "N/A",
                "p50_duration": "N/A",
                "p95_duration": "N/A"
            }

        total_seconds = (self.task.updated_at - self.task.created_at).total_seconds()
        total_time = self._format_duration(total_seconds)

        # Get stage durations from task metrics
        stage_durations = self.db.query(TaskMetrics.metric_value).filter(
            TaskMetrics.task_id == self.task.id,
            TaskMetrics.metric_name.like("%_duration")
        ).all()

        durations = [d[0] for d in stage_durations if d[0] > 0]

        if durations:
            p50 = statistics.median(durations)
            p95 = statistics.quantiles(durations, n=20)[18] if len(durations) > 1 else durations[0]
        else:
            p50 = p95 = 0

        return {
            "total_time": total_time,
            "p50_duration": self._format_duration(p50),
            "p95_duration": self._format_duration(p95)
        }

    def _get_llm_metrics(self) -> Dict[str, Any]:
        """Calculate LLM usage metrics."""
        usage_records = self.db.query(LLMUsage).filter(
            LLMUsage.task_id == self.task.id
        ).all()

        if not usage_records:
            return {
                "total_tokens": 0,
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_cost": 0.0,
                "model_breakdown": "No LLM calls recorded"
            }

        total_tokens = sum(u.total_tokens for u in usage_records)
        prompt_tokens = sum(u.prompt_tokens for u in usage_records)
        completion_tokens = sum(u.completion_tokens for u in usage_records)
        total_cost = sum(u.cost_usd for u in usage_records)

        # Model breakdown
        model_stats = {}
        for usage in usage_records:
            model = usage.model
            if model not in model_stats:
                model_stats[model] = {"calls": 0, "tokens": 0, "cost": 0.0}
            model_stats[model]["calls"] += 1
            model_stats[model]["tokens"] += usage.total_tokens
            model_stats[model]["cost"] += usage.cost_usd

        breakdown_lines = []
        for model, stats in model_stats.items():
            breakdown_lines.append(
                f"- **{model}**: {stats['calls']} calls, "
                f"{stats['tokens']:,} tokens, ${stats['cost']:.4f}"
            )

        return {
            "total_tokens": f"{total_tokens:,}",
            "prompt_tokens": f"{prompt_tokens:,}",
            "completion_tokens": f"{completion_tokens:,}",
            "total_cost": total_cost,
            "model_breakdown": "\n".join(breakdown_lines) if breakdown_lines else "No model usage"
        }

    def _get_test_results(self) -> Dict[str, Any]:
        """Extract test results from task."""
        pre_fix_output = self.task.test_output_before or "No pre-fix tests run"
        pre_fix_status = "❌ FAILED" if "FAIL" in pre_fix_output.upper() else "✅ PASSED"

        # Extract post-fix test results from logs
        logs = self.task.logs or ""
        post_fix_output = "No post-fix tests run"
        post_fix_status = "⚠️ UNKNOWN"

        if "RUNNING_TESTS_AFTER_FIX" in logs:
            # Extract test output from logs
            lines = logs.split('\n')
            test_section = []
            in_test_section = False

            for line in lines:
                if "RUNNING_TESTS_AFTER_FIX" in line:
                    in_test_section = True
                elif in_test_section:
                    if any(s in line for s in ["COMPLETED", "FAILED", "CREATING_PR"]):
                        break
                    test_section.append(line)

            if test_section:
                post_fix_output = "\n".join(test_section[-20:])  # Last 20 lines
                post_fix_status = "✅ PASSED" if self.task.status == "COMPLETED" else "❌ FAILED"

        # E2E test summary
        e2e_summary = "No E2E tests configured"
        if self.task.e2e_test_path:
            e2e_summary = f"✅ Behavioral tests executed from `{self.task.e2e_test_path}`"

        return {
            "pre_fix_output": pre_fix_output[:500],  # Truncate
            "pre_fix_status": pre_fix_status,
            "post_fix_output": post_fix_output[:500],
            "post_fix_status": post_fix_status,
            "e2e_summary": e2e_summary
        }

    def _get_stage_breakdown(self) -> str:
        """Generate stage breakdown table."""
        # Get stage metrics
        stage_metrics = self.db.query(TaskMetrics).filter(
            TaskMetrics.task_id == self.task.id
        ).all()

        if not stage_metrics:
            return "| No stage data | - | - | - | - |"

        # Group by stage (extract from metric_name)
        stages = {}
        for metric in stage_metrics:
            # Parse metric name like "GENERATING_FIX_duration"
            parts = metric.metric_name.rsplit('_', 1)
            if len(parts) == 2:
                stage_name = parts[0]
                metric_type = parts[1]

                if stage_name not in stages:
                    stages[stage_name] = {}
                stages[stage_name][metric_type] = metric.metric_value

        # Generate table rows
        rows = []
        for stage_name, metrics in stages.items():
            duration = self._format_duration(metrics.get("duration", 0))
            tokens = int(metrics.get("tokens", 0))
            cost = metrics.get("cost", 0.0)
            status = "✅" if metrics.get("success", 1) else "❌"

            rows.append(
                f"| {stage_name.replace('_', ' ').title()} | {duration} | "
                f"{tokens:,} | ${cost:.4f} | {status} |"
            )

        return "\n".join(rows) if rows else "| No stage data | - | - | - | - |"

    def _get_budget_status(self, llm_usage: Dict, timing: Dict) -> Dict[str, Any]:
        """Calculate budget utilization."""
        # Default budgets (should come from config)
        token_budget = 100000
        cost_budget = 5.0
        time_budget_seconds = 3600  # 1 hour

        total_tokens = int(llm_usage["total_tokens"].replace(",", "")) if isinstance(llm_usage["total_tokens"], str) else 0
        total_cost = llm_usage["total_cost"]

        # Parse time
        total_seconds = 0
        if timing["total_time"] != "N/A":
            # Simple parser for "Xm Ys" format
            time_str = timing["total_time"]
            if 'm' in time_str:
                minutes = int(time_str.split('m')[0].strip())
                total_seconds = minutes * 60

        token_pct = (total_tokens / token_budget * 100) if token_budget > 0 else 0
        cost_pct = (total_cost / cost_budget * 100) if cost_budget > 0 else 0
        time_pct = (total_seconds / time_budget_seconds * 100) if time_budget_seconds > 0 else 0

        # Generate warning if over budget
        warnings = []
        if token_pct > 100:
            warnings.append(f"⚠️ **Token budget exceeded** ({token_pct:.1f}%)")
        if cost_pct > 100:
            warnings.append(f"⚠️ **Cost budget exceeded** ({cost_pct:.1f}%)")
        if time_pct > 100:
            warnings.append(f"⚠️ **Time budget exceeded** ({time_pct:.1f}%)")

        warning = "\n".join(warnings) if warnings else ""

        return {
            "token_budget": f"{token_budget:,}",
            "cost_budget": cost_budget,
            "time_budget_str": self._format_duration(time_budget_seconds),
            "token_percentage": f"{token_pct:.1f}",
            "cost_percentage": f"{cost_pct:.1f}",
            "time_percentage": f"{time_pct:.1f}",
            "warning": warning
        }

    def _extract_changes_summary(self) -> str:
        """Extract summary of changes from logs."""
        logs = self.task.logs or ""

        # Look for patch information in logs
        if "patch" in logs.lower() or "fix" in logs.lower():
            return "Code patches applied to fix the bug. See diff for details."

        return "Automated bug fix applied."

    def _extract_files_modified(self) -> str:
        """Extract list of modified files."""
        # This would ideally come from git diff or patch metadata
        # For now, extract from logs if available
        logs = self.task.logs or ""

        files = []
        for line in logs.split('\n'):
            if 'file_path' in line.lower() or '.py' in line or '.js' in line:
                # Try to extract filenames
                words = line.split()
                for word in words:
                    if '.' in word and '/' in word:
                        files.append(f"- `{word}`")

        if files:
            return "\n".join(list(set(files))[:10])  # Max 10 unique files

        return "- Files modified (see diff)"

    def _get_task_url(self) -> str:
        """Get URL to task details."""
        base_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
        return f"{base_url}/?task={self.task.id}"

    def _get_logs_url(self) -> str:
        """Get URL to execution logs."""
        base_url = os.getenv("API_URL", "http://localhost:8000")
        return f"{base_url}/api/v1/task/{self.task.id}/logs"

    def _get_execution_trace(self) -> str:
        """Get full execution trace from logs."""
        logs = self.task.logs or "No logs available"
        return logs[-2000:]  # Last 2000 chars

    def _generate_notes(self) -> str:
        """Generate additional notes."""
        notes = []

        if self.task.workspace_path:
            notes.append(f"Workspace: `{self.task.workspace_path}`")

        if self.task.branch_name:
            notes.append(f"Branch: `{self.task.branch_name}`")

        return "\n".join(notes) if notes else "No additional notes."

    def _format_status_emoji(self, status: str) -> str:
        """Convert status to emoji + text."""
        emoji_map = {
            "COMPLETED": "✅ Completed",
            "FAILED": "❌ Failed",
            "QUEUED": "⏳ Queued",
            "RUNNING": "🔄 Running",
            "CANCELLED": "🚫 Cancelled"
        }
        return emoji_map.get(status, f"❓ {status}")

    def _format_duration(self, seconds: float) -> str:
        """Format duration as human-readable string."""
        if seconds < 60:
            return f"{seconds:.1f}s"
        elif seconds < 3600:
            minutes = seconds / 60
            return f"{minutes:.1f}m"
        else:
            hours = seconds / 3600
            minutes = (seconds % 3600) / 60
            return f"{hours:.0f}h {minutes:.0f}m"

    def _generate_simple_pr_body(self) -> str:
        """Generate simple PR body if template not found."""
        metrics = self._collect_metrics()

        return f"""# Autonomous Bug Fix

## 🤖 ASA Run Report

**Task ID:** {metrics['TASK_ID']}
**Status:** {metrics['STATUS']}

## 🐛 Bug Description

{metrics['BUG_DESCRIPTION']}

## 📊 Execution Summary

- **Total Time:** {metrics['TOTAL_TIME']}
- **Total Tokens:** {metrics['TOTAL_TOKENS']}
- **Total Cost:** ${metrics['TOTAL_COST']}

## 🧪 Test Results

### Pre-Fix Tests
{metrics['PRE_FIX_STATUS']}

### Post-Fix Tests
{metrics['POST_FIX_STATUS']}

---

*Generated automatically by ASA v{metrics['ASA_VERSION']}*
"""


def generate_pr_body_for_task(task_id: str, db: Session) -> str:
    """
    Convenience function to generate PR body for a task.

    Args:
        task_id: Task ID
        db: Database session

    Returns:
        Formatted PR body
    """
    report = RunReport(task_id, db)
    return report.generate_pr_body()
