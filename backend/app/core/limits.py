"""
Configuration for limits, budgets, and model pinning.

This module defines all constraints for the ASA system:
- LLM token budgets per purpose
- Cost limits
- Model selection per agent type
- Timeout configurations
"""

from typing import Dict, Any
from enum import Enum


class LLMPurpose(str, Enum):
    """Different purposes for LLM calls, each with its own model and budget."""
    CODE_ANALYSIS = "code_analysis"  # Analyzing code structure
    BUG_DETECTION = "bug_detection"  # Detecting bugs
    FIX_GENERATION = "fix_generation"  # Generating bug fixes
    TEST_GENERATION = "test_generation"  # Generating test cases
    CODE_REVIEW = "code_review"  # Reviewing code quality
    SEMANTIC_SEARCH = "semantic_search"  # Code search queries
    CIT_GENERATION = "cit_generation"  # E2E test generation
    GUARDIAN = "guardian"  # Security/safety checks


class ModelConfig:
    """Configuration for a specific LLM model."""

    def __init__(
        self,
        provider: str,
        model: str,
        version: str,
        max_tokens_per_call: int,
        max_calls_per_task: int,
        temperature: float = 0.2
    ):
        self.provider = provider
        self.model = model
        self.version = version
        self.max_tokens_per_call = max_tokens_per_call
        self.max_calls_per_task = max_calls_per_task
        self.temperature = temperature

    def __repr__(self):
        return f"{self.provider}:{self.model}:{self.version}"


# ============================================================================
# MODEL PINNING PER PURPOSE
# ============================================================================

MODEL_CONFIGS: Dict[LLMPurpose, ModelConfig] = {
    # Fix generation - most critical, use best model
    LLMPurpose.FIX_GENERATION: ModelConfig(
        provider="openai",
        model="gpt-4o",
        version="2024-05-13",
        max_tokens_per_call=4000,
        max_calls_per_task=5,  # Max 5 fix attempts
        temperature=0.2  # Lower for determinism
    ),

    # Code analysis - medium complexity
    LLMPurpose.CODE_ANALYSIS: ModelConfig(
        provider="openai",
        model="gpt-4o-mini",
        version="2024-07-18",
        max_tokens_per_call=2000,
        max_calls_per_task=10,
        temperature=0.1
    ),

    # Bug detection - needs reasoning
    LLMPurpose.BUG_DETECTION: ModelConfig(
        provider="openai",
        model="gpt-4o",
        version="2024-05-13",
        max_tokens_per_call=3000,
        max_calls_per_task=3,
        temperature=0.1
    ),

    # Test generation - creative but structured
    LLMPurpose.TEST_GENERATION: ModelConfig(
        provider="openai",
        model="gpt-4o-mini",
        version="2024-07-18",
        max_tokens_per_call=2000,
        max_calls_per_task=5,
        temperature=0.3
    ),

    # Code review - quality assessment
    LLMPurpose.CODE_REVIEW: ModelConfig(
        provider="openai",
        model="gpt-4o-mini",
        version="2024-07-18",
        max_tokens_per_call=1500,
        max_calls_per_task=5,
        temperature=0.2
    ),

    # Semantic search - simple embeddings
    LLMPurpose.SEMANTIC_SEARCH: ModelConfig(
        provider="openai",
        model="gpt-4o-mini",
        version="2024-07-18",
        max_tokens_per_call=1000,
        max_calls_per_task=20,  # Allow many searches
        temperature=0.0
    ),

    # CIT generation - E2E test creation
    LLMPurpose.CIT_GENERATION: ModelConfig(
        provider="openai",
        model="gpt-4o",
        version="2024-05-13",
        max_tokens_per_call=3000,
        max_calls_per_task=3,
        temperature=0.3
    ),

    # Guardian - security checks
    LLMPurpose.GUARDIAN: ModelConfig(
        provider="openai",
        model="gpt-4o-mini",
        version="2024-07-18",
        max_tokens_per_call=1000,
        max_calls_per_task=5,
        temperature=0.0  # Deterministic for safety
    ),
}


# ============================================================================
# BUDGET LIMITS
# ============================================================================

class BudgetLimits:
    """Global budget limits for the system."""

    # Per-task limits
    MAX_TOKENS_PER_TASK = 50000  # Total tokens across all LLM calls
    MAX_COST_PER_TASK_USD = 2.00  # Maximum cost per task
    MAX_TIME_PER_TASK_SECONDS = 3600  # 1 hour

    # Per-user limits (daily)
    MAX_TASKS_PER_USER_PER_DAY = 50
    MAX_COST_PER_USER_PER_DAY_USD = 20.00

    # Global limits (daily)
    MAX_TOTAL_COST_PER_DAY_USD = 500.00
    MAX_TOTAL_TASKS_PER_DAY = 1000


# ============================================================================
# TIMEOUT CONFIGURATIONS
# ============================================================================

class TimeoutConfig:
    """Timeout configurations for different operations."""

    # LLM call timeouts
    LLM_CALL_TIMEOUT_SECONDS = 60  # Max time for single LLM API call

    # Test execution timeouts
    TEST_RUN_TIMEOUT_SECONDS = 300  # 5 minutes
    TEST_INSTALL_TIMEOUT_SECONDS = 180  # 3 minutes

    # Git operations
    GIT_CLONE_TIMEOUT_SECONDS = 300  # 5 minutes
    GIT_PUSH_TIMEOUT_SECONDS = 60  # 1 minute

    # Code indexing
    CODE_INDEX_TIMEOUT_SECONDS = 120  # 2 minutes

    # CIT test execution
    CIT_TEST_TIMEOUT_SECONDS = 600  # 10 minutes


# ============================================================================
# MODEL PRICING (for cost calculation)
# ============================================================================

MODEL_PRICING: Dict[str, Dict[str, float]] = {
    # OpenAI pricing (per 1M tokens)
    "gpt-4o": {
        "input": 2.50,
        "output": 10.00
    },
    "gpt-4o-mini": {
        "input": 0.15,
        "output": 0.60
    },
    "gpt-4-turbo": {
        "input": 10.00,
        "output": 30.00
    },
    "gpt-4": {
        "input": 30.00,
        "output": 60.00
    },
    "gpt-3.5-turbo": {
        "input": 0.50,
        "output": 1.50
    },
}


def get_model_config(purpose: LLMPurpose) -> ModelConfig:
    """
    Get model configuration for a specific purpose.

    Args:
        purpose: LLM purpose

    Returns:
        ModelConfig for the purpose

    Raises:
        ValueError: If purpose not configured
    """
    if purpose not in MODEL_CONFIGS:
        raise ValueError(f"No model configured for purpose: {purpose}")

    return MODEL_CONFIGS[purpose]


def calculate_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    """
    Calculate cost for an LLM call.

    Args:
        model: Model name
        prompt_tokens: Number of prompt tokens
        completion_tokens: Number of completion tokens

    Returns:
        Cost in USD
    """
    # Find pricing for model (handle version suffixes)
    pricing = None
    for model_name, model_pricing in MODEL_PRICING.items():
        if model.startswith(model_name):
            pricing = model_pricing
            break

    if not pricing:
        # Unknown model, use gpt-4o pricing as conservative estimate
        pricing = MODEL_PRICING["gpt-4o"]

    input_cost = (prompt_tokens / 1_000_000) * pricing["input"]
    output_cost = (completion_tokens / 1_000_000) * pricing["output"]

    return input_cost + output_cost


def get_budget_summary() -> Dict[str, Any]:
    """
    Get summary of all budget configurations.

    Returns:
        Dictionary with budget information
    """
    return {
        "per_task": {
            "max_tokens": BudgetLimits.MAX_TOKENS_PER_TASK,
            "max_cost_usd": BudgetLimits.MAX_COST_PER_TASK_USD,
            "max_time_seconds": BudgetLimits.MAX_TIME_PER_TASK_SECONDS
        },
        "per_user_daily": {
            "max_tasks": BudgetLimits.MAX_TASKS_PER_USER_PER_DAY,
            "max_cost_usd": BudgetLimits.MAX_COST_PER_USER_PER_DAY_USD
        },
        "global_daily": {
            "max_cost_usd": BudgetLimits.MAX_TOTAL_COST_PER_DAY_USD,
            "max_tasks": BudgetLimits.MAX_TOTAL_TASKS_PER_DAY
        },
        "models": {
            purpose.value: {
                "model": f"{config.provider}:{config.model}",
                "max_tokens": config.max_tokens_per_call,
                "max_calls": config.max_calls_per_task
            }
            for purpose, config in MODEL_CONFIGS.items()
        }
    }
