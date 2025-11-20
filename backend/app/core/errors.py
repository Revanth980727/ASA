"""
Error Taxonomy and Retry Policies.

Defines structured error types and retry behavior for the ASA system.
Each error type has:
- Classification (transient, permanent, policy, user)
- Retry policy (should_retry, max_attempts, backoff)
- User-facing message
"""

from enum import Enum
from typing import Optional, Dict, Any
from dataclasses import dataclass


class ErrorCategory(str, Enum):
    """High-level error categories."""
    TRANSIENT = "transient"  # Temporary failures, safe to retry
    PERMANENT = "permanent"  # Cannot be fixed by retry
    POLICY = "policy"  # Policy/security violation
    USER = "user"  # User input error
    RESOURCE = "resource"  # Resource limits exceeded


class ErrorType(str, Enum):
    """Specific error types with retry policies."""

    # Transient errors (retry with backoff)
    NETWORK_TIMEOUT = "network_timeout"
    NETWORK_CONNECTION = "network_connection"
    LLM_RATE_LIMIT = "llm_rate_limit"
    LLM_TIMEOUT = "llm_timeout"
    SANDBOX_TIMEOUT = "sandbox_timeout"
    DATABASE_LOCK = "database_lock"
    GITHUB_API_RATE_LIMIT = "github_api_rate_limit"

    # Permanent errors (do not retry)
    LLM_INVALID_RESPONSE = "llm_invalid_response"
    PARSE_ERROR = "parse_error"
    FILE_NOT_FOUND = "file_not_found"
    GIT_AUTHENTICATION_FAILED = "git_authentication_failed"
    GITHUB_REPO_NOT_FOUND = "github_repo_not_found"
    SANDBOX_FAILED = "sandbox_failed"
    TEST_COMPILATION_FAILED = "test_compilation_failed"

    # Policy violations (do not retry, require human review)
    GUARDIAN_REJECTED = "guardian_rejected"
    SECRET_EXPOSED = "secret_exposed"
    UNSAFE_CODE = "unsafe_code"
    BUDGET_EXCEEDED = "budget_exceeded"

    # User errors (do not retry, need user fix)
    INVALID_INPUT = "invalid_input"
    MISSING_REQUIRED_FIELD = "missing_required_field"
    INVALID_REPO_URL = "invalid_repo_url"

    # Resource limits
    TOKEN_BUDGET_EXCEEDED = "token_budget_exceeded"
    COST_BUDGET_EXCEEDED = "cost_budget_exceeded"
    TIME_BUDGET_EXCEEDED = "time_budget_exceeded"
    QUEUE_FULL = "queue_full"


@dataclass
class RetryPolicy:
    """Retry policy for an error type."""

    should_retry: bool
    max_attempts: int
    backoff_seconds: float  # Initial backoff
    backoff_multiplier: float  # Exponential backoff multiplier
    max_backoff_seconds: float  # Cap on backoff


@dataclass
class ErrorInfo:
    """Complete information about an error type."""

    error_type: ErrorType
    category: ErrorCategory
    retry_policy: RetryPolicy
    user_message_template: str
    internal_log_message: str


# Error taxonomy with retry policies
ERROR_TAXONOMY: Dict[ErrorType, ErrorInfo] = {
    # Transient network errors - retry with exponential backoff
    ErrorType.NETWORK_TIMEOUT: ErrorInfo(
        error_type=ErrorType.NETWORK_TIMEOUT,
        category=ErrorCategory.TRANSIENT,
        retry_policy=RetryPolicy(
            should_retry=True,
            max_attempts=3,
            backoff_seconds=2.0,
            backoff_multiplier=2.0,
            max_backoff_seconds=30.0
        ),
        user_message_template="Network timeout occurred. Retrying... (attempt {attempt}/{max_attempts})",
        internal_log_message="Network timeout during operation"
    ),

    ErrorType.NETWORK_CONNECTION: ErrorInfo(
        error_type=ErrorType.NETWORK_CONNECTION,
        category=ErrorCategory.TRANSIENT,
        retry_policy=RetryPolicy(
            should_retry=True,
            max_attempts=3,
            backoff_seconds=1.0,
            backoff_multiplier=2.0,
            max_backoff_seconds=10.0
        ),
        user_message_template="Network connection error. Retrying... (attempt {attempt}/{max_attempts})",
        internal_log_message="Network connection failed"
    ),

    # LLM errors
    ErrorType.LLM_RATE_LIMIT: ErrorInfo(
        error_type=ErrorType.LLM_RATE_LIMIT,
        category=ErrorCategory.TRANSIENT,
        retry_policy=RetryPolicy(
            should_retry=True,
            max_attempts=5,
            backoff_seconds=10.0,
            backoff_multiplier=2.0,
            max_backoff_seconds=120.0
        ),
        user_message_template="LLM rate limit hit. Waiting before retry... (attempt {attempt}/{max_attempts})",
        internal_log_message="OpenAI API rate limit exceeded"
    ),

    ErrorType.LLM_TIMEOUT: ErrorInfo(
        error_type=ErrorType.LLM_TIMEOUT,
        category=ErrorCategory.TRANSIENT,
        retry_policy=RetryPolicy(
            should_retry=True,
            max_attempts=2,
            backoff_seconds=5.0,
            backoff_multiplier=1.5,
            max_backoff_seconds=15.0
        ),
        user_message_template="LLM request timed out. Retrying with shorter context...",
        internal_log_message="LLM API timeout"
    ),

    ErrorType.LLM_INVALID_RESPONSE: ErrorInfo(
        error_type=ErrorType.LLM_INVALID_RESPONSE,
        category=ErrorCategory.PERMANENT,
        retry_policy=RetryPolicy(
            should_retry=False,
            max_attempts=0,
            backoff_seconds=0,
            backoff_multiplier=1.0,
            max_backoff_seconds=0
        ),
        user_message_template="LLM generated invalid response. Task failed.",
        internal_log_message="LLM response failed schema validation"
    ),

    # Sandbox errors
    ErrorType.SANDBOX_TIMEOUT: ErrorInfo(
        error_type=ErrorType.SANDBOX_TIMEOUT,
        category=ErrorCategory.TRANSIENT,
        retry_policy=RetryPolicy(
            should_retry=True,
            max_attempts=2,
            backoff_seconds=3.0,
            backoff_multiplier=1.0,
            max_backoff_seconds=3.0
        ),
        user_message_template="Test execution timed out. Retrying...",
        internal_log_message="Sandbox execution timeout"
    ),

    ErrorType.SANDBOX_FAILED: ErrorInfo(
        error_type=ErrorType.SANDBOX_FAILED,
        category=ErrorCategory.PERMANENT,
        retry_policy=RetryPolicy(
            should_retry=False,
            max_attempts=0,
            backoff_seconds=0,
            backoff_multiplier=1.0,
            max_backoff_seconds=0
        ),
        user_message_template="Sandbox execution failed. Cannot complete task.",
        internal_log_message="Docker sandbox failed to start or execute"
    ),

    # Git/GitHub errors
    ErrorType.GIT_AUTHENTICATION_FAILED: ErrorInfo(
        error_type=ErrorType.GIT_AUTHENTICATION_FAILED,
        category=ErrorCategory.USER,
        retry_policy=RetryPolicy(
            should_retry=False,
            max_attempts=0,
            backoff_seconds=0,
            backoff_multiplier=1.0,
            max_backoff_seconds=0
        ),
        user_message_template="Git authentication failed. Please check your GitHub token.",
        internal_log_message="Git authentication error"
    ),

    ErrorType.GITHUB_API_RATE_LIMIT: ErrorInfo(
        error_type=ErrorType.GITHUB_API_RATE_LIMIT,
        category=ErrorCategory.TRANSIENT,
        retry_policy=RetryPolicy(
            should_retry=True,
            max_attempts=3,
            backoff_seconds=60.0,
            backoff_multiplier=1.0,
            max_backoff_seconds=60.0
        ),
        user_message_template="GitHub API rate limit hit. Waiting 60 seconds...",
        internal_log_message="GitHub API rate limit exceeded"
    ),

    # Policy violations - never retry
    ErrorType.GUARDIAN_REJECTED: ErrorInfo(
        error_type=ErrorType.GUARDIAN_REJECTED,
        category=ErrorCategory.POLICY,
        retry_policy=RetryPolicy(
            should_retry=False,
            max_attempts=0,
            backoff_seconds=0,
            backoff_multiplier=1.0,
            max_backoff_seconds=0
        ),
        user_message_template="Fix rejected by security guardian. Human review required.",
        internal_log_message="Guardian policy violation"
    ),

    ErrorType.SECRET_EXPOSED: ErrorInfo(
        error_type=ErrorType.SECRET_EXPOSED,
        category=ErrorCategory.POLICY,
        retry_policy=RetryPolicy(
            should_retry=False,
            max_attempts=0,
            backoff_seconds=0,
            backoff_multiplier=1.0,
            max_backoff_seconds=0
        ),
        user_message_template="Potential secret exposure detected. Task aborted.",
        internal_log_message="Secret exposure in code changes"
    ),

    # Budget errors
    ErrorType.TOKEN_BUDGET_EXCEEDED: ErrorInfo(
        error_type=ErrorType.TOKEN_BUDGET_EXCEEDED,
        category=ErrorCategory.RESOURCE,
        retry_policy=RetryPolicy(
            should_retry=False,
            max_attempts=0,
            backoff_seconds=0,
            backoff_multiplier=1.0,
            max_backoff_seconds=0
        ),
        user_message_template="Token budget exceeded. Task stopped.",
        internal_log_message="LLM token budget limit reached"
    ),

    ErrorType.COST_BUDGET_EXCEEDED: ErrorInfo(
        error_type=ErrorType.COST_BUDGET_EXCEEDED,
        category=ErrorCategory.RESOURCE,
        retry_policy=RetryPolicy(
            should_retry=False,
            max_attempts=0,
            backoff_seconds=0,
            backoff_multiplier=1.0,
            max_backoff_seconds=0
        ),
        user_message_template="Cost budget exceeded. Task stopped.",
        internal_log_message="LLM cost budget limit reached"
    ),

    # User errors
    ErrorType.INVALID_INPUT: ErrorInfo(
        error_type=ErrorType.INVALID_INPUT,
        category=ErrorCategory.USER,
        retry_policy=RetryPolicy(
            should_retry=False,
            max_attempts=0,
            backoff_seconds=0,
            backoff_multiplier=1.0,
            max_backoff_seconds=0
        ),
        user_message_template="Invalid input provided: {details}",
        internal_log_message="User input validation failed"
    ),

    ErrorType.FILE_NOT_FOUND: ErrorInfo(
        error_type=ErrorType.FILE_NOT_FOUND,
        category=ErrorCategory.PERMANENT,
        retry_policy=RetryPolicy(
            should_retry=False,
            max_attempts=0,
            backoff_seconds=0,
            backoff_multiplier=1.0,
            max_backoff_seconds=0
        ),
        user_message_template="Required file not found: {file_path}",
        internal_log_message="File not found error"
    ),
}


class ASAError(Exception):
    """Base exception for all ASA errors."""

    def __init__(
        self,
        error_type: ErrorType,
        message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        original_exception: Optional[Exception] = None
    ):
        """
        Initialize ASA error.

        Args:
            error_type: Type of error from ErrorType enum
            message: Optional custom message
            details: Optional additional details
            original_exception: Original exception if wrapping
        """
        self.error_type = error_type
        self.error_info = ERROR_TAXONOMY.get(error_type)
        self.details = details or {}
        self.original_exception = original_exception

        # Use custom message or default from taxonomy
        if message:
            self.message = message
        elif self.error_info:
            self.message = self.error_info.user_message_template.format(**self.details)
        else:
            self.message = f"Unknown error: {error_type}"

        super().__init__(self.message)

    @property
    def category(self) -> Optional[ErrorCategory]:
        """Get error category."""
        return self.error_info.category if self.error_info else None

    @property
    def retry_policy(self) -> Optional[RetryPolicy]:
        """Get retry policy."""
        return self.error_info.retry_policy if self.error_info else None

    @property
    def should_retry(self) -> bool:
        """Check if error should be retried."""
        return self.retry_policy.should_retry if self.retry_policy else False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging/API."""
        return {
            "error_type": self.error_type.value,
            "category": self.category.value if self.category else None,
            "message": self.message,
            "details": self.details,
            "should_retry": self.should_retry,
            "max_attempts": self.retry_policy.max_attempts if self.retry_policy else 0
        }


def get_retry_policy(error_type: ErrorType) -> Optional[RetryPolicy]:
    """
    Get retry policy for an error type.

    Args:
        error_type: Error type

    Returns:
        RetryPolicy or None
    """
    error_info = ERROR_TAXONOMY.get(error_type)
    return error_info.retry_policy if error_info else None


def classify_exception(exception: Exception) -> ErrorType:
    """
    Classify a raw exception into an ErrorType.

    Args:
        exception: Exception to classify

    Returns:
        ErrorType classification
    """
    exception_str = str(exception).lower()
    exception_type = type(exception).__name__

    # Network errors
    if "timeout" in exception_str or "TimeoutError" in exception_type:
        return ErrorType.NETWORK_TIMEOUT
    if "connection" in exception_str or "ConnectionError" in exception_type:
        return ErrorType.NETWORK_CONNECTION

    # LLM errors
    if "rate limit" in exception_str or "429" in exception_str:
        return ErrorType.LLM_RATE_LIMIT
    if "json" in exception_str or "JSONDecodeError" in exception_type:
        return ErrorType.LLM_INVALID_RESPONSE

    # File errors
    if "FileNotFoundError" in exception_type or "no such file" in exception_str:
        return ErrorType.FILE_NOT_FOUND

    # Git errors
    if "authentication" in exception_str or "401" in exception_str:
        return ErrorType.GIT_AUTHENTICATION_FAILED

    # Default to permanent error
    return ErrorType.SANDBOX_FAILED
