"""
LLM Client Wrapper with Token Usage and Cost Tracking.

⚠️ DEPRECATED: This module is deprecated in favor of llm_gateway.py
⚠️ Use app.services.llm_gateway.LLMGateway instead for:
   - Model pinning per purpose
   - Budget enforcement
   - Centralized LLM configuration

Provides:
- Automatic token usage logging
- Cost calculation based on model pricing
- Per-task and per-user usage tracking
- OpenTelemetry span instrumentation
- Usage limit enforcement
"""

import os
import time
import warnings
from typing import Optional, Dict, Any, List
from datetime import datetime
from openai import OpenAI
from openai.types.chat import ChatCompletion

from app.database import SessionLocal
from app.models import LLMUsage


# Pricing per 1M tokens (as of Jan 2025)
# Source: https://openai.com/api/pricing/
MODEL_PRICING = {
    "gpt-4": {
        "input": 30.0,   # $30 per 1M input tokens
        "output": 60.0,  # $60 per 1M output tokens
    },
    "gpt-4-turbo": {
        "input": 10.0,   # $10 per 1M input tokens
        "output": 30.0,  # $30 per 1M output tokens
    },
    "gpt-4o": {
        "input": 2.50,   # $2.50 per 1M input tokens
        "output": 10.0,  # $10 per 1M output tokens
    },
    "gpt-4o-mini": {
        "input": 0.15,   # $0.15 per 1M input tokens
        "output": 0.60,  # $0.60 per 1M output tokens
    },
    "gpt-3.5-turbo": {
        "input": 0.50,   # $0.50 per 1M input tokens
        "output": 1.50,  # $1.50 per 1M output tokens
    },
}


class LLMClient:
    """
    Wrapper around OpenAI client with usage tracking and observability.

    Features:
    - Automatic token usage logging to database
    - Cost calculation based on model pricing
    - OpenTelemetry span creation
    - Usage limit enforcement (optional)
    - Per-task and per-user tracking
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        task_id: Optional[str] = None,
        user_id: Optional[str] = None,
        enable_otel: bool = True
    ):
        """
        Initialize LLM client with tracking.

        ⚠️ DEPRECATED: Use LLMGateway from app.services.llm_gateway instead.

        Args:
            api_key: OpenAI API key. If None, loads from OPENAI_API_KEY env var
            task_id: Optional task ID for tracking usage per task
            user_id: Optional user ID for tracking usage per user
            enable_otel: Enable OpenTelemetry instrumentation
        """
        # Emit deprecation warning
        warnings.warn(
            "LLMClient is deprecated. Use LLMGateway from app.services.llm_gateway instead. "
            "LLMGateway provides model pinning, purpose-based routing, and better budget enforcement.",
            DeprecationWarning,
            stacklevel=2
        )

        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key not provided. Set OPENAI_API_KEY environment variable.")

        self.client = OpenAI(api_key=self.api_key)
        self.task_id = task_id
        self.user_id = user_id
        self.enable_otel = enable_otel

        # Import OpenTelemetry tracer if enabled
        self.tracer = None
        if enable_otel:
            try:
                from opentelemetry import trace
                self.tracer = trace.get_tracer(__name__)
            except ImportError:
                self.enable_otel = False

    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str = "gpt-4",
        temperature: float = 0.2,
        max_tokens: int = 2000,
        **kwargs
    ) -> ChatCompletion:
        """
        Create chat completion with automatic usage tracking.

        Args:
            messages: Chat messages
            model: Model name (e.g., "gpt-4", "gpt-4-turbo")
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            **kwargs: Additional arguments passed to OpenAI API

        Returns:
            ChatCompletion response
        """
        start_time = time.time()

        # Create OpenTelemetry span if enabled
        span_context = None
        if self.enable_otel and self.tracer:
            span_context = self.tracer.start_as_current_span(
                "llm.chat_completion",
                attributes={
                    "llm.model": model,
                    "llm.temperature": temperature,
                    "llm.max_tokens": max_tokens,
                    "llm.task_id": self.task_id or "none",
                    "llm.user_id": self.user_id or "none",
                }
            )

        try:
            # Call OpenAI API
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs
            )

            # Calculate latency
            latency_ms = (time.time() - start_time) * 1000

            # Extract usage information
            usage = response.usage
            prompt_tokens = usage.prompt_tokens if usage else 0
            completion_tokens = usage.completion_tokens if usage else 0
            total_tokens = usage.total_tokens if usage else 0

            # Calculate cost
            cost_usd = self._calculate_cost(model, prompt_tokens, completion_tokens)

            # Log usage to database
            self._log_usage(
                model=model,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                cost_usd=cost_usd,
                latency_ms=latency_ms,
                status="success"
            )

            # Add span attributes
            if span_context:
                span_context.__enter__()
                span = span_context.__enter__()
                span.set_attribute("llm.prompt_tokens", prompt_tokens)
                span.set_attribute("llm.completion_tokens", completion_tokens)
                span.set_attribute("llm.total_tokens", total_tokens)
                span.set_attribute("llm.cost_usd", cost_usd)
                span.set_attribute("llm.latency_ms", latency_ms)
                span.set_attribute("llm.status", "success")

            return response

        except Exception as e:
            # Log failed request
            latency_ms = (time.time() - start_time) * 1000
            self._log_usage(
                model=model,
                prompt_tokens=0,
                completion_tokens=0,
                total_tokens=0,
                cost_usd=0.0,
                latency_ms=latency_ms,
                status="error",
                error_message=str(e)
            )

            # Add error to span
            if span_context:
                span = span_context.__enter__()
                span.set_attribute("llm.status", "error")
                span.set_attribute("llm.error", str(e))
                span.set_attribute("llm.latency_ms", latency_ms)

            raise

        finally:
            if span_context:
                span_context.__exit__(None, None, None)

    def _calculate_cost(self, model: str, prompt_tokens: int, completion_tokens: int) -> float:
        """
        Calculate cost in USD based on token usage.

        Args:
            model: Model name
            prompt_tokens: Number of input tokens
            completion_tokens: Number of output tokens

        Returns:
            Cost in USD
        """
        # Get pricing for model (default to gpt-4 if unknown)
        pricing = MODEL_PRICING.get(model, MODEL_PRICING["gpt-4"])

        # Calculate cost (pricing is per 1M tokens)
        input_cost = (prompt_tokens / 1_000_000) * pricing["input"]
        output_cost = (completion_tokens / 1_000_000) * pricing["output"]

        return input_cost + output_cost

    def _log_usage(
        self,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        total_tokens: int,
        cost_usd: float,
        latency_ms: float,
        status: str,
        error_message: Optional[str] = None
    ) -> None:
        """
        Log LLM usage to database.

        Args:
            model: Model name
            prompt_tokens: Number of input tokens
            completion_tokens: Number of output tokens
            total_tokens: Total tokens used
            cost_usd: Cost in USD
            latency_ms: Request latency in milliseconds
            status: Request status ("success" or "error")
            error_message: Optional error message
        """
        try:
            db = SessionLocal()

            usage_record = LLMUsage(
                task_id=self.task_id,
                user_id=self.user_id,
                model=model,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                cost_usd=cost_usd,
                latency_ms=latency_ms,
                status=status,
                error_message=error_message,
                timestamp=datetime.utcnow()
            )

            db.add(usage_record)
            db.commit()
            db.close()

        except Exception as e:
            # Don't let logging errors break the main flow
            print(f"Warning: Failed to log LLM usage: {e}")

    def get_task_usage(self, task_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get total usage statistics for a task.

        Args:
            task_id: Task ID (defaults to current task_id)

        Returns:
            Dictionary with usage statistics
        """
        task_id = task_id or self.task_id
        if not task_id:
            raise ValueError("No task_id provided")

        db = SessionLocal()
        try:
            from sqlalchemy import func

            # Query usage for this task
            result = db.query(
                func.count(LLMUsage.id).label("request_count"),
                func.sum(LLMUsage.total_tokens).label("total_tokens"),
                func.sum(LLMUsage.cost_usd).label("total_cost_usd"),
                func.avg(LLMUsage.latency_ms).label("avg_latency_ms"),
            ).filter(LLMUsage.task_id == task_id).first()

            return {
                "task_id": task_id,
                "request_count": result.request_count or 0,
                "total_tokens": result.total_tokens or 0,
                "total_cost_usd": float(result.total_cost_usd or 0.0),
                "avg_latency_ms": float(result.avg_latency_ms or 0.0),
            }
        finally:
            db.close()

    def get_user_usage(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get total usage statistics for a user.

        Args:
            user_id: User ID (defaults to current user_id)

        Returns:
            Dictionary with usage statistics
        """
        user_id = user_id or self.user_id
        if not user_id:
            raise ValueError("No user_id provided")

        db = SessionLocal()
        try:
            from sqlalchemy import func

            # Query usage for this user
            result = db.query(
                func.count(LLMUsage.id).label("request_count"),
                func.sum(LLMUsage.total_tokens).label("total_tokens"),
                func.sum(LLMUsage.cost_usd).label("total_cost_usd"),
                func.avg(LLMUsage.latency_ms).label("avg_latency_ms"),
            ).filter(LLMUsage.user_id == user_id).first()

            return {
                "user_id": user_id,
                "request_count": result.request_count or 0,
                "total_tokens": result.total_tokens or 0,
                "total_cost_usd": float(result.total_cost_usd or 0.0),
                "avg_latency_ms": float(result.avg_latency_ms or 0.0),
            }
        finally:
            db.close()

    def check_usage_limits(
        self,
        max_cost_per_task: Optional[float] = None,
        max_cost_per_user: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Check if usage is within limits.

        Args:
            max_cost_per_task: Maximum cost (USD) per task
            max_cost_per_user: Maximum cost (USD) per user

        Returns:
            Dictionary with limit check results
        """
        result = {
            "within_limits": True,
            "violations": []
        }

        # Check task limits
        if max_cost_per_task and self.task_id:
            task_usage = self.get_task_usage()
            if task_usage["total_cost_usd"] > max_cost_per_task:
                result["within_limits"] = False
                result["violations"].append({
                    "type": "task_cost_limit",
                    "task_id": self.task_id,
                    "current_cost": task_usage["total_cost_usd"],
                    "limit": max_cost_per_task
                })

        # Check user limits
        if max_cost_per_user and self.user_id:
            user_usage = self.get_user_usage()
            if user_usage["total_cost_usd"] > max_cost_per_user:
                result["within_limits"] = False
                result["violations"].append({
                    "type": "user_cost_limit",
                    "user_id": self.user_id,
                    "current_cost": user_usage["total_cost_usd"],
                    "limit": max_cost_per_user
                })

        return result
