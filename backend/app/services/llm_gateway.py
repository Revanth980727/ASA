"""
LLM Gateway - Centralized LLM API abstraction with model pinning and budgets.

This is the ONLY module allowed to make external LLM API calls.
All agents must use this gateway for consistency and budget enforcement.

Features:
- Model pinning per purpose
- Token budget enforcement
- Cost tracking
- Usage logging
- Timeout handling
- Rate limiting
- Error taxonomy integration
- Prompt versioning with schema validation
"""

import os
import time
import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from openai import OpenAI, APIError, RateLimitError, APITimeoutError
from sqlalchemy.orm import Session

from app.core.limits import (
    LLMPurpose,
    ModelConfig,
    BudgetLimits,
    TimeoutConfig,
    get_model_config,
    calculate_cost
)
from app.core.errors import ASAError, ErrorType, classify_exception
from app.core.retry_handler import with_retry
from app.core.prompt_loader import load_prompt, PromptVersion
from app.models import LLMUsage, Task
from app.database import SessionLocal

logger = logging.getLogger(__name__)


class LLMGateway:
    """
    Centralized gateway for all LLM API calls.

    This class enforces:
    - Model pinning per purpose
    - Token budgets
    - Cost limits
    - Usage tracking
    """

    def __init__(
        self,
        task_id: Optional[str] = None,
        user_id: Optional[str] = None,
        db: Optional[Session] = None
    ):
        """
        Initialize LLM gateway.

        Args:
            task_id: Task ID for tracking
            user_id: User ID for quota enforcement
            db: Database session (will create if not provided)
        """
        self.task_id = task_id
        self.user_id = user_id
        self.db = db or SessionLocal()
        self._owns_db = db is None

        # Initialize OpenAI client
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable required")

        self.client = OpenAI(api_key=api_key)

        # Track calls for this instance
        self._call_counts: Dict[LLMPurpose, int] = {}
        self._total_tokens = 0
        self._total_cost = 0.0

    def __del__(self):
        """Clean up database session if we own it."""
        if self._owns_db and self.db:
            self.db.close()

    @with_retry(
        error_types=[
            ErrorType.LLM_RATE_LIMIT,
            ErrorType.LLM_TIMEOUT,
            ErrorType.NETWORK_TIMEOUT,
            ErrorType.NETWORK_CONNECTION
        ]
    )
    def chat_completion(
        self,
        purpose: LLMPurpose,
        messages: List[Dict[str, str]],
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
        schema_version: Optional[str] = None
    ) -> str:
        """
        Make a chat completion call with budget enforcement and retry logic.

        Args:
            purpose: Purpose of this LLM call (determines model)
            messages: Chat messages in OpenAI format
            max_tokens: Optional override for max tokens
            temperature: Optional override for temperature
            metadata: Optional metadata to log with usage
            schema_version: Optional schema version for tracking

        Returns:
            Generated text response

        Raises:
            ASAError: If budget limits exceeded or API errors occur
        """
        # Get model config for this purpose
        config = get_model_config(purpose)

        # Check budget before making call
        self._check_budgets(purpose, config)

        # Use config defaults or overrides
        max_tokens = max_tokens or config.max_tokens_per_call
        temperature = temperature if temperature is not None else config.temperature

        # Prepare model name with version
        model = f"{config.model}"

        # Add schema version to metadata if provided
        enhanced_metadata = metadata or {}
        if schema_version:
            enhanced_metadata["schema_version"] = schema_version

        logger.info(
            f"[LLMGateway] Calling {model} for {purpose.value} "
            f"(task: {self.task_id}, max_tokens: {max_tokens}, "
            f"schema_version: {schema_version or 'none'})"
        )

        # Make API call with timeout
        start_time = time.time()

        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                timeout=TimeoutConfig.LLM_CALL_TIMEOUT_SECONDS
            )

            latency_ms = (time.time() - start_time) * 1000

            # Extract usage
            usage = response.usage
            prompt_tokens = usage.prompt_tokens
            completion_tokens = usage.completion_tokens
            total_tokens = usage.total_tokens

            # Calculate cost
            cost = calculate_cost(model, prompt_tokens, completion_tokens)

            # Update tracking
            self._call_counts[purpose] = self._call_counts.get(purpose, 0) + 1
            self._total_tokens += total_tokens
            self._total_cost += cost

            # Log usage to database
            self._log_usage(
                purpose=purpose,
                model=model,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                cost=cost,
                latency_ms=latency_ms,
                status="success",
                metadata=enhanced_metadata
            )

            # Extract response text
            response_text = response.choices[0].message.content

            logger.info(
                f"[LLMGateway] Success: {total_tokens} tokens, "
                f"${cost:.4f}, {latency_ms:.0f}ms"
            )

            return response_text

        except RateLimitError as e:
            latency_ms = (time.time() - start_time) * 1000
            self._log_usage(
                purpose=purpose, model=model, prompt_tokens=0,
                completion_tokens=0, total_tokens=0, cost=0.0,
                latency_ms=latency_ms, status="error",
                error_message=str(e), metadata=enhanced_metadata
            )
            logger.warning(f"[LLMGateway] Rate limit hit: {e}")
            raise ASAError(ErrorType.LLM_RATE_LIMIT, original_exception=e)

        except APITimeoutError as e:
            latency_ms = (time.time() - start_time) * 1000
            self._log_usage(
                purpose=purpose, model=model, prompt_tokens=0,
                completion_tokens=0, total_tokens=0, cost=0.0,
                latency_ms=latency_ms, status="error",
                error_message=str(e), metadata=enhanced_metadata
            )
            logger.warning(f"[LLMGateway] Timeout: {e}")
            raise ASAError(ErrorType.LLM_TIMEOUT, original_exception=e)

        except APIError as e:
            latency_ms = (time.time() - start_time) * 1000
            self._log_usage(
                purpose=purpose, model=model, prompt_tokens=0,
                completion_tokens=0, total_tokens=0, cost=0.0,
                latency_ms=latency_ms, status="error",
                error_message=str(e), metadata=enhanced_metadata
            )
            logger.error(f"[LLMGateway] API error: {e}")
            # Classify and wrap the error
            error_type = classify_exception(e)
            raise ASAError(error_type, original_exception=e)

        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            self._log_usage(
                purpose=purpose, model=model, prompt_tokens=0,
                completion_tokens=0, total_tokens=0, cost=0.0,
                latency_ms=latency_ms, status="error",
                error_message=str(e), metadata=enhanced_metadata
            )
            logger.error(f"[LLMGateway] Unexpected error: {e}")
            raise

    def chat_completion_with_prompt(
        self,
        purpose: LLMPurpose,
        version: str = "v1",
        **prompt_variables
    ) -> Dict[str, Any]:
        """
        Make an LLM call using a versioned prompt with schema validation.

        Args:
            purpose: Purpose of this LLM call
            version: Schema version to use (default: "v1")
            **prompt_variables: Variables to substitute in the prompt template

        Returns:
            Parsed and validated JSON response

        Raises:
            ASAError: If budget exceeded, API errors, or schema validation fails
        """
        # Load the versioned prompt
        prompt = load_prompt(purpose, version)

        logger.info(
            f"[LLMGateway] Using versioned prompt: {prompt.purpose} "
            f"v{prompt.schema_version} (checksum: {prompt.checksum})"
        )

        # Get messages from prompt
        messages = prompt.get_messages(**prompt_variables)

        # Get model config from prompt if available
        max_tokens = prompt.model_config.get("max_tokens")
        temperature = prompt.model_config.get("temperature")

        # Make LLM call with schema version tracking
        response_text = self.chat_completion(
            purpose=purpose,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            metadata=prompt.to_metadata(),
            schema_version=prompt.schema_version
        )

        # Parse JSON response
        try:
            response_json = json.loads(response_text)
        except json.JSONDecodeError as e:
            logger.error(f"[LLMGateway] Failed to parse JSON response: {e}")
            raise ASAError(
                ErrorType.LLM_INVALID_RESPONSE,
                message="LLM response is not valid JSON",
                details={"response": response_text[:200]},
                original_exception=e
            )

        # Validate response against schema
        try:
            prompt.validate_response(response_json)
        except ValueError as e:
            logger.error(f"[LLMGateway] Schema validation failed: {e}")
            raise ASAError(
                ErrorType.LLM_INVALID_RESPONSE,
                message="LLM response failed schema validation",
                details={
                    "schema_version": prompt.schema_version,
                    "validation_error": str(e)
                },
                original_exception=e
            )

        logger.info(
            f"[LLMGateway] Response validated against schema {prompt.schema_version}"
        )

        return response_json

    def _check_budgets(self, purpose: LLMPurpose, config: ModelConfig):
        """
        Check if budget limits would be exceeded.

        Raises:
            ASAError: If any budget limit would be exceeded
        """
        # Check call count for this purpose
        call_count = self._call_counts.get(purpose, 0)
        if call_count >= config.max_calls_per_task:
            raise ASAError(
                ErrorType.COST_BUDGET_EXCEEDED,
                message=f"Max calls for {purpose.value} exceeded "
                        f"({call_count}/{config.max_calls_per_task})",
                details={"purpose": purpose.value, "count": call_count, "limit": config.max_calls_per_task}
            )

        # Check total token budget for task
        if self.task_id:
            task_usage = self._get_task_usage()

            if task_usage["total_tokens"] >= BudgetLimits.MAX_TOKENS_PER_TASK:
                raise ASAError(
                    ErrorType.TOKEN_BUDGET_EXCEEDED,
                    details={
                        "task_id": self.task_id,
                        "tokens_used": task_usage["total_tokens"],
                        "limit": BudgetLimits.MAX_TOKENS_PER_TASK
                    }
                )

            if task_usage["total_cost"] >= BudgetLimits.MAX_COST_PER_TASK_USD:
                raise ASAError(
                    ErrorType.COST_BUDGET_EXCEEDED,
                    details={
                        "task_id": self.task_id,
                        "cost_usd": task_usage["total_cost"],
                        "limit": BudgetLimits.MAX_COST_PER_TASK_USD
                    }
                )

        # Check user daily limits
        if self.user_id:
            user_usage = self._get_user_daily_usage()

            if user_usage["total_cost"] >= BudgetLimits.MAX_COST_PER_USER_PER_DAY_USD:
                raise ASAError(
                    ErrorType.COST_BUDGET_EXCEEDED,
                    details={
                        "user_id": self.user_id,
                        "cost_usd": user_usage["total_cost"],
                        "limit": BudgetLimits.MAX_COST_PER_USER_PER_DAY_USD,
                        "period": "daily"
                    }
                )

    def _get_task_usage(self) -> Dict[str, Any]:
        """Get current usage for this task."""
        if not self.task_id:
            return {"total_tokens": 0, "total_cost": 0.0}

        from sqlalchemy import func

        result = self.db.query(
            func.sum(LLMUsage.total_tokens).label("total_tokens"),
            func.sum(LLMUsage.cost_usd).label("total_cost")
        ).filter(
            LLMUsage.task_id == self.task_id
        ).first()

        return {
            "total_tokens": int(result.total_tokens or 0),
            "total_cost": float(result.total_cost or 0.0)
        }

    def _get_user_daily_usage(self) -> Dict[str, Any]:
        """Get user usage for today."""
        if not self.user_id:
            return {"total_cost": 0.0}

        from sqlalchemy import func

        today_start = datetime.utcnow().replace(
            hour=0, minute=0, second=0, microsecond=0
        )

        result = self.db.query(
            func.sum(LLMUsage.cost_usd).label("total_cost")
        ).filter(
            LLMUsage.user_id == self.user_id,
            LLMUsage.timestamp >= today_start
        ).first()

        return {
            "total_cost": float(result.total_cost or 0.0)
        }

    def _log_usage(
        self,
        purpose: LLMPurpose,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        total_tokens: int,
        cost: float,
        latency_ms: float,
        status: str,
        error_message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Log usage to database."""
        usage_record = LLMUsage(
            task_id=self.task_id,
            user_id=self.user_id,
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            cost_usd=cost,
            latency_ms=latency_ms,
            status=status,
            error_message=error_message
        )

        self.db.add(usage_record)
        self.db.commit()

    def get_usage_summary(self) -> Dict[str, Any]:
        """
        Get usage summary for this gateway instance.

        Returns:
            Dictionary with usage statistics
        """
        return {
            "task_id": self.task_id,
            "user_id": self.user_id,
            "call_counts": {
                purpose.value: count
                for purpose, count in self._call_counts.items()
            },
            "total_tokens": self._total_tokens,
            "total_cost_usd": self._total_cost,
            "budgets": {
                "token_limit": BudgetLimits.MAX_TOKENS_PER_TASK,
                "cost_limit": BudgetLimits.MAX_COST_PER_TASK_USD,
                "token_usage_pct": (self._total_tokens / BudgetLimits.MAX_TOKENS_PER_TASK * 100),
                "cost_usage_pct": (self._total_cost / BudgetLimits.MAX_COST_PER_TASK_USD * 100)
            }
        }


# Convenience functions

def call_llm(
    purpose: LLMPurpose,
    messages: List[Dict[str, str]],
    task_id: Optional[str] = None,
    user_id: Optional[str] = None,
    **kwargs
) -> str:
    """
    Convenience function for making LLM calls.

    Args:
        purpose: Purpose of the LLM call
        messages: Chat messages
        task_id: Optional task ID
        user_id: Optional user ID
        **kwargs: Additional arguments to pass to chat_completion

    Returns:
        Generated text
    """
    gateway = LLMGateway(task_id=task_id, user_id=user_id)
    return gateway.chat_completion(purpose, messages, **kwargs)
