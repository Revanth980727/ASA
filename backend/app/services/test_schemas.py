"""
Test Result Schemas - Structured data for test execution results.

Used by CIT Agent for behavioral verification.
"""

from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


class TestStatus(Enum):
    """Test execution status."""
    PASSED = "passed"
    FAILED = "failed"
    ERROR = "error"
    SKIPPED = "skipped"
    TIMEOUT = "timeout"


@dataclass
class TestFailure:
    """Details about a test failure."""
    message: str
    stack_trace: Optional[str] = None
    line_number: Optional[int] = None
    screenshot_path: Optional[str] = None


@dataclass
class TestResult:
    """Result of a single test execution."""
    test_name: str
    status: TestStatus
    duration_ms: float
    failure: Optional[TestFailure] = None
    stdout: str = ""
    stderr: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result = {
            "test_name": self.test_name,
            "status": self.status.value,
            "duration_ms": self.duration_ms,
            "stdout": self.stdout,
            "stderr": self.stderr
        }

        if self.failure:
            result["failure"] = {
                "message": self.failure.message,
                "stack_trace": self.failure.stack_trace,
                "line_number": self.failure.line_number,
                "screenshot_path": self.failure.screenshot_path
            }

        return result


@dataclass
class TestSuiteResult:
    """Result of a complete test suite execution."""
    total: int
    passed: int
    failed: int
    errors: int
    skipped: int
    duration_ms: float
    test_results: List[TestResult]
    timestamp: datetime

    @property
    def success(self) -> bool:
        """Whether all tests passed."""
        return self.failed == 0 and self.errors == 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "total": self.total,
            "passed": self.passed,
            "failed": self.failed,
            "errors": self.errors,
            "skipped": self.skipped,
            "duration_ms": self.duration_ms,
            "success": self.success,
            "timestamp": self.timestamp.isoformat(),
            "test_results": [t.to_dict() for t in self.test_results]
        }

    def get_summary(self) -> str:
        """Get human-readable summary."""
        return (
            f"Tests: {self.total} total, {self.passed} passed, "
            f"{self.failed} failed, {self.errors} errors, {self.skipped} skipped "
            f"({self.duration_ms:.0f}ms)"
        )

    def get_failure_details(self) -> str:
        """Get detailed failure information."""
        if self.success:
            return "All tests passed"

        failures = []
        for test in self.test_results:
            if test.status in (TestStatus.FAILED, TestStatus.ERROR):
                failure_info = [f"\n❌ {test.test_name}:"]
                if test.failure:
                    failure_info.append(f"   Message: {test.failure.message}")
                    if test.failure.stack_trace:
                        # Truncate stack trace for readability
                        stack = test.failure.stack_trace[:500]
                        failure_info.append(f"   Stack: {stack}...")
                failures.append("\n".join(failure_info))

        return "\n".join(failures)
