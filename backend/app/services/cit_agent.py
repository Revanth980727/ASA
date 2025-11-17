"""
CIT Agent - Behavioral Verification Agent.

Generates and executes Playwright E2E tests to verify bugs and fixes.
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Optional, Tuple

from app.services.test_generator import TestGenerator
from app.services.docker_sandbox import DockerSandbox
from app.services.test_schemas import (
    TestResult, TestSuiteResult, TestStatus, TestFailure
)


class CITAgent:
    """
    CIT (Continuous Integration Testing) Agent for behavioral verification.

    Orchestrates:
    1. Test generation from bug descriptions
    2. Isolated test execution in Docker
    3. Result parsing and validation
    """

    def __init__(self, use_docker: bool = True):
        """
        Initialize CIT Agent.

        Args:
            use_docker: Whether to use Docker sandbox (recommended for safety)
        """
        self.test_generator = TestGenerator()
        self.use_docker = use_docker

        if use_docker:
            self.sandbox = DockerSandbox()
        else:
            self.sandbox = None

    def verify_bug(
        self,
        bug_description: str,
        workspace_path: str,
        app_context: str = ""
    ) -> Tuple[bool, TestSuiteResult, str]:
        """
        Verify that a bug exists by generating and running a test.

        Args:
            bug_description: Description of the bug to verify
            workspace_path: Path to the workspace
            app_context: Optional context about the application

        Returns:
            Tuple of (bug_exists, test_result, test_file_path)
            - bug_exists: True if test fails (bug confirmed)
            - test_result: TestSuiteResult with details
            - test_file_path: Path to generated test file
        """
        print(f"CIT Agent: Verifying bug exists...")

        # Step 1: Generate test
        test_file = self._generate_test_file(
            bug_description,
            workspace_path,
            app_context
        )

        # Step 2: Setup Playwright if needed
        if self.use_docker:
            self._setup_test_environment(workspace_path)

        # Step 3: Run test
        result = self._execute_test(test_file, workspace_path)

        # Step 4: Interpret results
        # Bug exists if test FAILS
        bug_exists = not result.success

        return bug_exists, result, test_file

    def verify_fix(
        self,
        test_file_path: str,
        workspace_path: str
    ) -> Tuple[bool, TestSuiteResult]:
        """
        Verify that a fix works by re-running the test.

        Args:
            test_file_path: Path to the test file
            workspace_path: Path to the workspace

        Returns:
            Tuple of (fix_works, test_result)
            - fix_works: True if test passes (fix confirmed)
            - test_result: TestSuiteResult with details
        """
        print(f"CIT Agent: Verifying fix works...")

        # Run the same test again
        result = self._execute_test(test_file_path, workspace_path)

        # Fix works if test PASSES
        fix_works = result.success

        return fix_works, result

    def _generate_test_file(
        self,
        bug_description: str,
        workspace_path: str,
        app_context: str
    ) -> str:
        """Generate a Playwright test file."""
        workspace = Path(workspace_path)

        # Create tests directory
        tests_dir = workspace / "tests"
        tests_dir.mkdir(exist_ok=True)

        # Generate test
        test_file = tests_dir / "bug_verification.spec.js"

        print(f"Generating test for bug: {bug_description[:50]}...")
        self.test_generator.generate_and_save(
            bug_description=bug_description,
            output_path=str(test_file),
            app_context=app_context
        )

        return str(test_file)

    def _setup_test_environment(self, workspace_path: str):
        """Setup Playwright test environment."""
        if self.use_docker and self.sandbox:
            print("Setting up Playwright environment in Docker...")
            self.sandbox.setup_playwright_project(workspace_path)

    def _execute_test(
        self,
        test_file_path: str,
        workspace_path: str
    ) -> TestSuiteResult:
        """Execute test and parse results."""
        print(f"Executing test: {test_file_path}")

        if self.use_docker and self.sandbox:
            return self._execute_test_docker(test_file_path, workspace_path)
        else:
            return self._execute_test_local(test_file_path, workspace_path)

    def _execute_test_docker(
        self,
        test_file_path: str,
        workspace_path: str
    ) -> TestSuiteResult:
        """Execute test in Docker sandbox."""
        exit_code, stdout, stderr = self.sandbox.run_test(
            test_file_path=test_file_path,
            workspace_path=workspace_path,
            timeout=60
        )

        return self._parse_test_results(exit_code, stdout, stderr)

    def _execute_test_local(
        self,
        test_file_path: str,
        workspace_path: str
    ) -> TestSuiteResult:
        """Execute test locally (not recommended for production)."""
        import subprocess

        # This is a fallback - Docker is preferred
        print("Warning: Running test locally without Docker isolation")

        try:
            result = subprocess.run(
                ['npx', 'playwright', 'test', test_file_path, '--reporter=json'],
                cwd=workspace_path,
                capture_output=True,
                text=True,
                timeout=60
            )

            return self._parse_test_results(
                result.returncode,
                result.stdout,
                result.stderr
            )
        except Exception as e:
            # Return error result
            return self._create_error_result(str(e))

    def _parse_test_results(
        self,
        exit_code: int,
        stdout: str,
        stderr: str
    ) -> TestSuiteResult:
        """Parse Playwright test results."""
        test_results = []
        total = 0
        passed = 0
        failed = 0
        errors = 0
        skipped = 0
        duration_ms = 0.0

        # Try to parse JSON output from Playwright
        try:
            # Playwright JSON reporter outputs to stdout
            if stdout:
                # Look for JSON output
                lines = stdout.split('\n')
                for line in lines:
                    if line.strip().startswith('{'):
                        try:
                            data = json.loads(line)
                            # Parse Playwright JSON format
                            if 'suites' in data:
                                # Parse suite results
                                result = self._parse_playwright_json(data)
                                if result:
                                    return result
                        except json.JSONDecodeError:
                            continue

            # Fallback: parse text output
            return self._parse_text_output(exit_code, stdout, stderr)

        except Exception as e:
            print(f"Error parsing test results: {e}")
            return self._create_error_result(str(e))

    def _parse_playwright_json(self, data: dict) -> Optional[TestSuiteResult]:
        """Parse Playwright JSON reporter output."""
        test_results = []
        total = 0
        passed = 0
        failed = 0
        errors = 0
        duration_ms = 0.0

        # Playwright JSON structure varies, handle common formats
        if 'stats' in data:
            stats = data['stats']
            total = stats.get('total', 0)
            passed = stats.get('expected', 0)
            failed = stats.get('unexpected', 0)
            errors = stats.get('flaky', 0)
            duration_ms = stats.get('duration', 0)

        # Parse individual test results
        if 'suites' in data:
            for suite in data['suites']:
                if 'specs' in suite:
                    for spec in suite['specs']:
                        test_results.append(self._parse_spec(spec))

        return TestSuiteResult(
            total=total,
            passed=passed,
            failed=failed,
            errors=errors,
            skipped=0,
            duration_ms=duration_ms,
            test_results=test_results,
            timestamp=datetime.now()
        )

    def _parse_spec(self, spec: dict) -> TestResult:
        """Parse a single test spec from Playwright JSON."""
        title = spec.get('title', 'Unknown test')
        tests = spec.get('tests', [])

        if not tests:
            return TestResult(
                test_name=title,
                status=TestStatus.SKIPPED,
                duration_ms=0.0
            )

        # Get first test result
        test = tests[0]
        results = test.get('results', [])

        if not results:
            return TestResult(
                test_name=title,
                status=TestStatus.SKIPPED,
                duration_ms=0.0
            )

        result = results[0]
        status_str = result.get('status', 'unknown')
        duration = result.get('duration', 0)

        # Map Playwright status to our TestStatus
        status_map = {
            'passed': TestStatus.PASSED,
            'failed': TestStatus.FAILED,
            'skipped': TestStatus.SKIPPED,
            'timedOut': TestStatus.TIMEOUT
        }
        status = status_map.get(status_str, TestStatus.ERROR)

        # Extract failure details
        failure = None
        if status in (TestStatus.FAILED, TestStatus.ERROR):
            error = result.get('error', {})
            failure = TestFailure(
                message=error.get('message', 'Test failed'),
                stack_trace=error.get('stack', None)
            )

        return TestResult(
            test_name=title,
            status=status,
            duration_ms=duration,
            failure=failure,
            stdout=result.get('stdout', ''),
            stderr=result.get('stderr', '')
        )

    def _parse_text_output(
        self,
        exit_code: int,
        stdout: str,
        stderr: str
    ) -> TestSuiteResult:
        """Fallback: parse text output when JSON not available."""
        # Simple heuristic: exit code 0 = pass, non-zero = fail
        if exit_code == 0:
            return TestSuiteResult(
                total=1,
                passed=1,
                failed=0,
                errors=0,
                skipped=0,
                duration_ms=0.0,
                test_results=[
                    TestResult(
                        test_name="Bug verification test",
                        status=TestStatus.PASSED,
                        duration_ms=0.0,
                        stdout=stdout,
                        stderr=stderr
                    )
                ],
                timestamp=datetime.now()
            )
        else:
            return TestSuiteResult(
                total=1,
                passed=0,
                failed=1,
                errors=0,
                skipped=0,
                duration_ms=0.0,
                test_results=[
                    TestResult(
                        test_name="Bug verification test",
                        status=TestStatus.FAILED,
                        duration_ms=0.0,
                        failure=TestFailure(
                            message="Test failed",
                            stack_trace=stderr
                        ),
                        stdout=stdout,
                        stderr=stderr
                    )
                ],
                timestamp=datetime.now()
            )

    def _create_error_result(self, error_message: str) -> TestSuiteResult:
        """Create an error result."""
        return TestSuiteResult(
            total=1,
            passed=0,
            failed=0,
            errors=1,
            skipped=0,
            duration_ms=0.0,
            test_results=[
                TestResult(
                    test_name="Bug verification test",
                    status=TestStatus.ERROR,
                    duration_ms=0.0,
                    failure=TestFailure(message=error_message),
                    stderr=error_message
                )
            ],
            timestamp=datetime.now()
        )
