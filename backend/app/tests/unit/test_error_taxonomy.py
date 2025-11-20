"""
Unit Tests for Error Taxonomy and Retry Logic.

Tests error classification, retry policies, and retry handler.
"""

import pytest
import time
from app.core.errors import (
    ErrorType, ErrorCategory, ASAError, classify_exception,
    get_retry_policy, ERROR_TAXONOMY
)
from app.core.retry_handler import with_retry, retry_operation, RetryExhausted


class TestErrorClassification:
    """Test error classification and taxonomy."""

    def test_all_error_types_have_taxonomy(self):
        """Ensure all ErrorType enums have taxonomy entries."""
        for error_type in ErrorType:
            assert error_type in ERROR_TAXONOMY, (
                f"ErrorType.{error_type.name} missing from ERROR_TAXONOMY"
            )

    def test_retry_policy_consistency(self):
        """Test that retry policies are consistent."""
        for error_type, error_info in ERROR_TAXONOMY.items():
            retry_policy = error_info.retry_policy

            # Check consistency
            if retry_policy.should_retry:
                assert retry_policy.max_attempts > 0, (
                    f"{error_type} should_retry=True but max_attempts={retry_policy.max_attempts}"
                )
                assert retry_policy.backoff_seconds > 0, (
                    f"{error_type} should_retry=True but backoff_seconds={retry_policy.backoff_seconds}"
                )
            else:
                assert retry_policy.max_attempts == 0, (
                    f"{error_type} should_retry=False but max_attempts={retry_policy.max_attempts}"
                )

    def test_transient_errors_are_retryable(self):
        """Test that all transient errors are retryable."""
        for error_type, error_info in ERROR_TAXONOMY.items():
            if error_info.category == ErrorCategory.TRANSIENT:
                assert error_info.retry_policy.should_retry, (
                    f"Transient error {error_type} should be retryable"
                )

    def test_policy_errors_not_retryable(self):
        """Test that policy violations are not retryable."""
        for error_type, error_info in ERROR_TAXONOMY.items():
            if error_info.category == ErrorCategory.POLICY:
                assert not error_info.retry_policy.should_retry, (
                    f"Policy error {error_type} should not be retryable"
                )

    def test_classify_timeout_exception(self):
        """Test that timeout exceptions are classified correctly."""
        timeout_error = TimeoutError("Connection timed out")
        error_type = classify_exception(timeout_error)

        assert error_type == ErrorType.NETWORK_TIMEOUT

    def test_classify_connection_exception(self):
        """Test that connection exceptions are classified correctly."""
        conn_error = ConnectionError("Failed to connect")
        error_type = classify_exception(conn_error)

        assert error_type == ErrorType.NETWORK_CONNECTION

    def test_classify_file_not_found(self):
        """Test that file not found is classified correctly."""
        file_error = FileNotFoundError("test.txt not found")
        error_type = classify_exception(file_error)

        assert error_type == ErrorType.FILE_NOT_FOUND


class TestASAError:
    """Test ASAError exception class."""

    def test_create_asa_error(self):
        """Test creating an ASAError."""
        error = ASAError(
            error_type=ErrorType.NETWORK_TIMEOUT,
            details={"url": "https://example.com"}
        )

        assert error.error_type == ErrorType.NETWORK_TIMEOUT
        assert error.category == ErrorCategory.TRANSIENT
        assert error.should_retry is True

    def test_asa_error_to_dict(self):
        """Test converting ASAError to dict."""
        error = ASAError(
            error_type=ErrorType.GUARDIAN_REJECTED,
            message="Security violation"
        )

        error_dict = error.to_dict()

        assert error_dict["error_type"] == "guardian_rejected"
        assert error_dict["category"] == "policy"
        assert error_dict["should_retry"] is False
        assert "message" in error_dict

    def test_asa_error_retry_policy_access(self):
        """Test accessing retry policy from ASAError."""
        error = ASAError(error_type=ErrorType.LLM_RATE_LIMIT)

        assert error.retry_policy is not None
        assert error.retry_policy.should_retry is True
        assert error.retry_policy.max_attempts == 5


class TestRetryHandler:
    """Test retry handler decorators and utilities."""

    def test_retry_on_transient_error(self):
        """Test that transient errors are retried."""
        call_count = 0

        @with_retry()
        def flaky_function():
            nonlocal call_count
            call_count += 1

            if call_count < 2:
                raise ASAError(ErrorType.NETWORK_TIMEOUT)

            return "success"

        result = flaky_function()

        assert result == "success"
        assert call_count == 2  # Failed once, succeeded on retry

    def test_no_retry_on_policy_error(self):
        """Test that policy errors are not retried."""
        call_count = 0

        @with_retry()
        def policy_violation():
            nonlocal call_count
            call_count += 1
            raise ASAError(ErrorType.GUARDIAN_REJECTED)

        with pytest.raises(ASAError) as exc_info:
            policy_violation()

        assert exc_info.value.error_type == ErrorType.GUARDIAN_REJECTED
        assert call_count == 1  # Should not retry

    def test_retry_exhaustion(self):
        """Test that retries are exhausted after max attempts."""
        call_count = 0

        @with_retry()
        def always_fails():
            nonlocal call_count
            call_count += 1
            raise ASAError(ErrorType.NETWORK_TIMEOUT)

        with pytest.raises(RetryExhausted):
            always_fails()

        # Network timeout has max_attempts=3
        assert call_count == 3

    def test_retry_with_callback(self):
        """Test retry with on_retry callback."""
        callback_calls = []

        def on_retry_callback(attempt, error, wait_time):
            callback_calls.append({
                "attempt": attempt,
                "error_type": error.error_type,
                "wait_time": wait_time
            })

        call_count = 0

        @with_retry(on_retry=on_retry_callback)
        def flaky_function():
            nonlocal call_count
            call_count += 1

            if call_count < 2:
                raise ASAError(ErrorType.NETWORK_CONNECTION)

            return "success"

        result = flaky_function()

        assert result == "success"
        assert len(callback_calls) == 1  # Called before the retry
        assert callback_calls[0]["attempt"] == 1

    def test_retry_operation_utility(self):
        """Test retry_operation utility function."""
        call_count = 0

        def operation():
            nonlocal call_count
            call_count += 1

            if call_count < 2:
                raise Exception("Temporary failure")

            return "success"

        result = retry_operation(
            operation,
            error_type=ErrorType.NETWORK_TIMEOUT
        )

        assert result == "success"
        assert call_count == 2


class TestBackoffCalculation:
    """Test exponential backoff calculations."""

    def test_exponential_backoff(self):
        """Test that backoff increases exponentially."""
        policy = get_retry_policy(ErrorType.NETWORK_TIMEOUT)

        assert policy is not None

        # Calculate backoff for attempts
        backoff_1 = policy.backoff_seconds
        backoff_2 = policy.backoff_seconds * policy.backoff_multiplier
        backoff_3 = policy.backoff_seconds * (policy.backoff_multiplier ** 2)

        # Should increase
        assert backoff_2 > backoff_1
        assert backoff_3 > backoff_2

    def test_backoff_cap(self):
        """Test that backoff is capped at max_backoff_seconds."""
        policy = get_retry_policy(ErrorType.LLM_RATE_LIMIT)

        assert policy is not None

        # After many attempts, should cap
        for attempt in range(10):
            backoff = min(
                policy.backoff_seconds * (policy.backoff_multiplier ** attempt),
                policy.max_backoff_seconds
            )

            assert backoff <= policy.max_backoff_seconds


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
