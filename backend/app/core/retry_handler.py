"""
Retry Handler - Implements retry logic based on error taxonomy.

Provides decorators and utilities for automatic retry with:
- Exponential backoff
- Error classification
- Attempt tracking
- Logging
"""

import time
import logging
from typing import Callable, Any, Optional, Type
from functools import wraps

from app.core.errors import (
    ASAError, ErrorType, ErrorCategory, classify_exception, get_retry_policy
)

logger = logging.getLogger(__name__)


class RetryExhausted(Exception):
    """Raised when all retry attempts are exhausted."""

    def __init__(self, original_error: Exception, attempts: int):
        self.original_error = original_error
        self.attempts = attempts
        super().__init__(
            f"Retry exhausted after {attempts} attempts. Original error: {original_error}"
        )


def with_retry(
    error_types: Optional[list[ErrorType]] = None,
    on_retry: Optional[Callable] = None
):
    """
    Decorator to automatically retry function calls based on error taxonomy.

    Args:
        error_types: Optional list of specific error types to handle
                    (if None, handles all ASAErrors based on their policy)
        on_retry: Optional callback called before each retry attempt
                 Signature: on_retry(attempt, error, wait_time)

    Example:
        @with_retry(error_types=[ErrorType.NETWORK_TIMEOUT])
        def call_api():
            ...

        @with_retry()  # Retry all ASAErrors based on policy
        def process_task():
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            attempt = 0
            last_error: Optional[Exception] = None

            while True:
                try:
                    attempt += 1
                    result = func(*args, **kwargs)
                    return result

                except ASAError as e:
                    last_error = e

                    # Check if we should retry this error type
                    if error_types and e.error_type not in error_types:
                        # Not in our retry list, re-raise
                        raise

                    if not e.should_retry:
                        # Error policy says don't retry
                        logger.warning(
                            f"Error is not retryable: {e.error_type.value}. "
                            f"Category: {e.category.value if e.category else 'unknown'}"
                        )
                        raise

                    retry_policy = e.retry_policy
                    if not retry_policy:
                        raise

                    if attempt >= retry_policy.max_attempts:
                        # Exhausted retries
                        logger.error(
                            f"Retry exhausted for {e.error_type.value} "
                            f"after {attempt} attempts"
                        )
                        raise RetryExhausted(e, attempt)

                    # Calculate backoff
                    wait_time = min(
                        retry_policy.backoff_seconds * (
                            retry_policy.backoff_multiplier ** (attempt - 1)
                        ),
                        retry_policy.max_backoff_seconds
                    )

                    logger.info(
                        f"Retrying {func.__name__} after {e.error_type.value}. "
                        f"Attempt {attempt}/{retry_policy.max_attempts}. "
                        f"Waiting {wait_time:.1f}s..."
                    )

                    # Call retry callback if provided
                    if on_retry:
                        on_retry(attempt, e, wait_time)

                    # Wait before retry
                    time.sleep(wait_time)

                except Exception as e:
                    # Classify unknown exception
                    last_error = e
                    error_type = classify_exception(e)

                    logger.info(
                        f"Classified exception {type(e).__name__} as {error_type.value}"
                    )

                    # Wrap in ASAError and retry
                    asa_error = ASAError(
                        error_type=error_type,
                        details={"exception_type": type(e).__name__},
                        original_exception=e
                    )

                    if not asa_error.should_retry:
                        # Don't retry, re-raise original
                        raise

                    retry_policy = asa_error.retry_policy
                    if not retry_policy or attempt >= retry_policy.max_attempts:
                        # Can't retry or exhausted
                        raise RetryExhausted(e, attempt)

                    # Calculate backoff and retry
                    wait_time = min(
                        retry_policy.backoff_seconds * (
                            retry_policy.backoff_multiplier ** (attempt - 1)
                        ),
                        retry_policy.max_backoff_seconds
                    )

                    logger.info(
                        f"Retrying {func.__name__} after {error_type.value}. "
                        f"Attempt {attempt}/{retry_policy.max_attempts}. "
                        f"Waiting {wait_time:.1f}s..."
                    )

                    if on_retry:
                        on_retry(attempt, asa_error, wait_time)

                    time.sleep(wait_time)

        return wrapper
    return decorator


def retry_operation(
    operation: Callable,
    error_type: ErrorType,
    max_attempts: Optional[int] = None,
    on_retry: Optional[Callable] = None
) -> Any:
    """
    Retry an operation based on error taxonomy.

    Args:
        operation: Function to retry
        error_type: Expected error type for retry policy
        max_attempts: Optional override for max attempts
        on_retry: Optional callback on retry

    Returns:
        Result of operation

    Raises:
        RetryExhausted: If retries exhausted
        ASAError: If error is not retryable
    """
    retry_policy = get_retry_policy(error_type)

    if not retry_policy or not retry_policy.should_retry:
        # No retry policy or not retryable
        return operation()

    max_attempts = max_attempts or retry_policy.max_attempts
    attempt = 0
    last_error: Optional[Exception] = None

    while attempt < max_attempts:
        try:
            attempt += 1
            return operation()

        except Exception as e:
            last_error = e

            if attempt >= max_attempts:
                raise RetryExhausted(e, attempt)

            # Calculate backoff
            wait_time = min(
                retry_policy.backoff_seconds * (
                    retry_policy.backoff_multiplier ** (attempt - 1)
                ),
                retry_policy.max_backoff_seconds
            )

            logger.info(
                f"Retrying operation after error. "
                f"Attempt {attempt}/{max_attempts}. "
                f"Waiting {wait_time:.1f}s..."
            )

            if on_retry:
                on_retry(attempt, e, wait_time)

            time.sleep(wait_time)

    # Should never reach here, but just in case
    if last_error:
        raise RetryExhausted(last_error, attempt)

    raise RuntimeError("Retry logic error: no attempts made")


class RetryContext:
    """Context manager for retry operations."""

    def __init__(
        self,
        error_type: ErrorType,
        max_attempts: Optional[int] = None
    ):
        """
        Initialize retry context.

        Args:
            error_type: Error type for retry policy
            max_attempts: Optional override for max attempts
        """
        self.error_type = error_type
        self.retry_policy = get_retry_policy(error_type)
        self.max_attempts = max_attempts or (
            self.retry_policy.max_attempts if self.retry_policy else 1
        )
        self.attempt = 0
        self.last_error: Optional[Exception] = None

    def __enter__(self):
        """Enter context."""
        self.attempt += 1
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context with retry logic."""
        if exc_val is None:
            # Success, no exception
            return True

        self.last_error = exc_val

        # Check if should retry
        if not self.retry_policy or not self.retry_policy.should_retry:
            return False  # Don't suppress exception

        if self.attempt >= self.max_attempts:
            # Exhausted retries
            logger.error(
                f"Retry exhausted for {self.error_type.value} "
                f"after {self.attempt} attempts"
            )
            return False

        # Calculate backoff
        wait_time = min(
            self.retry_policy.backoff_seconds * (
                self.retry_policy.backoff_multiplier ** (self.attempt - 1)
            ),
            self.retry_policy.max_backoff_seconds
        )

        logger.info(
            f"Retrying after {self.error_type.value}. "
            f"Attempt {self.attempt}/{self.max_attempts}. "
            f"Waiting {wait_time:.1f}s..."
        )

        time.sleep(wait_time)

        # Suppress exception to retry
        return True
