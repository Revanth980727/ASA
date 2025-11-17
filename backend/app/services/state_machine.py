"""
State Machine - Autonomous workflow orchestration for ASA.

Defines states, transitions, and conditional logic for the bug-fixing pipeline.
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Callable, Any
from datetime import datetime
import json


class TaskState(Enum):
    """All possible states in the ASA workflow."""
    # Initial states
    QUEUED = "QUEUED"
    INIT = "INIT"

    # Repository setup
    CLONING_REPO = "CLONING_REPO"
    INDEXING_CODE = "INDEXING_CODE"

    # Bug verification
    VERIFYING_BUG_BEHAVIOR = "VERIFYING_BUG_BEHAVIOR"  # CIT Agent E2E test
    RUNNING_TESTS_BEFORE_FIX = "RUNNING_TESTS_BEFORE_FIX"  # Unit tests

    # Fix generation
    GENERATING_FIX = "GENERATING_FIX"

    # Fix verification
    RUNNING_TESTS_AFTER_FIX = "RUNNING_TESTS_AFTER_FIX"  # Unit tests
    VERIFYING_FIX_BEHAVIOR = "VERIFYING_FIX_BEHAVIOR"  # CIT Agent E2E test

    # PR creation
    CREATING_PR_BRANCH = "CREATING_PR_BRANCH"

    # Terminal states
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    TIMEOUT = "TIMEOUT"
    RETRY = "RETRY"

    def is_terminal(self) -> bool:
        """Check if this is a terminal state."""
        return self in (TaskState.COMPLETED, TaskState.FAILED, TaskState.TIMEOUT)

    def is_successful(self) -> bool:
        """Check if this is a successful terminal state."""
        return self == TaskState.COMPLETED


class TransitionCondition(Enum):
    """Conditions that determine state transitions."""
    SUCCESS = "success"
    FAILURE = "failure"
    TIMEOUT = "timeout"
    RETRY_EXHAUSTED = "retry_exhausted"
    TESTS_PASS = "tests_pass"
    TESTS_FAIL = "tests_fail"
    BUG_CONFIRMED = "bug_confirmed"
    BUG_NOT_FOUND = "bug_not_found"
    FIX_VALIDATED = "fix_validated"
    FIX_INVALID = "fix_invalid"


@dataclass
class StateTransition:
    """Defines a transition between states."""
    from_state: TaskState
    to_state: TaskState
    condition: TransitionCondition
    description: str = ""

    def matches(self, current_state: TaskState, result: str) -> bool:
        """Check if this transition applies."""
        return (
            self.from_state == current_state and
            self.condition.value == result
        )


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""
    max_retries: int = 3
    retry_count: int = 0
    backoff_seconds: int = 5

    def can_retry(self) -> bool:
        """Check if we can retry."""
        return self.retry_count < self.max_retries

    def increment(self):
        """Increment retry counter."""
        self.retry_count += 1

    def reset(self):
        """Reset retry counter."""
        self.retry_count = 0


@dataclass
class StateContext:
    """Context information for a state."""
    state: TaskState
    entered_at: datetime
    exit_at: Optional[datetime] = None
    result: Optional[str] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def duration_seconds(self) -> Optional[float]:
        """Get duration in seconds."""
        if self.exit_at:
            return (self.exit_at - self.entered_at).total_seconds()
        return None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "state": self.state.value,
            "entered_at": self.entered_at.isoformat(),
            "exit_at": self.exit_at.isoformat() if self.exit_at else None,
            "result": self.result,
            "error": self.error,
            "duration_seconds": self.duration_seconds(),
            "metadata": self.metadata
        }


class StateMachine:
    """
    State machine for ASA workflow orchestration.

    Features:
    - Defined states and transitions
    - Conditional logic
    - Retry handling
    - State history tracking
    - Validation
    """

    def __init__(self, enable_cit: bool = False):
        """
        Initialize state machine.

        Args:
            enable_cit: Whether CIT Agent behavioral verification is enabled
        """
        self.enable_cit = enable_cit
        self.current_state = TaskState.QUEUED
        self.state_history: List[StateContext] = []
        self.retry_configs: Dict[TaskState, RetryConfig] = {
            TaskState.GENERATING_FIX: RetryConfig(max_retries=2),
            TaskState.RUNNING_TESTS_AFTER_FIX: RetryConfig(max_retries=1),
        }
        self.transitions = self._define_transitions()

    def _define_transitions(self) -> List[StateTransition]:
        """Define all valid state transitions."""
        transitions = [
            # Initial flow
            StateTransition(
                TaskState.QUEUED,
                TaskState.INIT,
                TransitionCondition.SUCCESS,
                "Task accepted and initialized"
            ),
            StateTransition(
                TaskState.INIT,
                TaskState.CLONING_REPO,
                TransitionCondition.SUCCESS,
                "Begin repository cloning"
            ),

            # Repository setup
            StateTransition(
                TaskState.CLONING_REPO,
                TaskState.INDEXING_CODE,
                TransitionCondition.SUCCESS,
                "Repository cloned successfully"
            ),
            StateTransition(
                TaskState.CLONING_REPO,
                TaskState.FAILED,
                TransitionCondition.FAILURE,
                "Failed to clone repository"
            ),

            # Code indexing
            StateTransition(
                TaskState.INDEXING_CODE,
                TaskState.VERIFYING_BUG_BEHAVIOR if self.enable_cit else TaskState.RUNNING_TESTS_BEFORE_FIX,
                TransitionCondition.SUCCESS,
                "Code indexed successfully"
            ),
            StateTransition(
                TaskState.INDEXING_CODE,
                TaskState.FAILED,
                TransitionCondition.FAILURE,
                "Failed to index code"
            ),

            # Bug verification (CIT - optional)
            StateTransition(
                TaskState.VERIFYING_BUG_BEHAVIOR,
                TaskState.RUNNING_TESTS_BEFORE_FIX,
                TransitionCondition.BUG_CONFIRMED,
                "Bug confirmed by E2E test"
            ),
            StateTransition(
                TaskState.VERIFYING_BUG_BEHAVIOR,
                TaskState.RUNNING_TESTS_BEFORE_FIX,
                TransitionCondition.BUG_NOT_FOUND,
                "E2E test passed, check unit tests"
            ),

            # Unit test verification
            StateTransition(
                TaskState.RUNNING_TESTS_BEFORE_FIX,
                TaskState.GENERATING_FIX,
                TransitionCondition.TESTS_FAIL,
                "Tests failed, bug confirmed"
            ),
            StateTransition(
                TaskState.RUNNING_TESTS_BEFORE_FIX,
                TaskState.FAILED,
                TransitionCondition.TESTS_PASS,
                "Tests pass, no bug to fix"
            ),
            StateTransition(
                TaskState.RUNNING_TESTS_BEFORE_FIX,
                TaskState.FAILED,
                TransitionCondition.FAILURE,
                "Failed to run tests"
            ),

            # Fix generation
            StateTransition(
                TaskState.GENERATING_FIX,
                TaskState.RUNNING_TESTS_AFTER_FIX,
                TransitionCondition.SUCCESS,
                "Fix generated and applied"
            ),
            StateTransition(
                TaskState.GENERATING_FIX,
                TaskState.RETRY,
                TransitionCondition.FAILURE,
                "Fix generation failed, retry"
            ),
            StateTransition(
                TaskState.GENERATING_FIX,
                TaskState.FAILED,
                TransitionCondition.RETRY_EXHAUSTED,
                "Fix generation failed, retries exhausted"
            ),

            # Fix verification (unit tests)
            StateTransition(
                TaskState.RUNNING_TESTS_AFTER_FIX,
                TaskState.VERIFYING_FIX_BEHAVIOR if self.enable_cit else TaskState.CREATING_PR_BRANCH,
                TransitionCondition.TESTS_PASS,
                "Unit tests pass after fix"
            ),
            StateTransition(
                TaskState.RUNNING_TESTS_AFTER_FIX,
                TaskState.RETRY,
                TransitionCondition.TESTS_FAIL,
                "Tests still failing, retry fix"
            ),
            StateTransition(
                TaskState.RUNNING_TESTS_AFTER_FIX,
                TaskState.FAILED,
                TransitionCondition.RETRY_EXHAUSTED,
                "Tests still failing, retries exhausted"
            ),

            # Fix verification (CIT - optional)
            StateTransition(
                TaskState.VERIFYING_FIX_BEHAVIOR,
                TaskState.CREATING_PR_BRANCH,
                TransitionCondition.FIX_VALIDATED,
                "E2E test passes after fix"
            ),
            StateTransition(
                TaskState.VERIFYING_FIX_BEHAVIOR,
                TaskState.CREATING_PR_BRANCH,
                TransitionCondition.FIX_INVALID,
                "E2E test fails, but unit tests pass (continue)"
            ),

            # PR creation
            StateTransition(
                TaskState.CREATING_PR_BRANCH,
                TaskState.COMPLETED,
                TransitionCondition.SUCCESS,
                "PR branch created successfully"
            ),
            StateTransition(
                TaskState.CREATING_PR_BRANCH,
                TaskState.COMPLETED,
                TransitionCondition.FAILURE,
                "PR creation failed, but fix succeeded"
            ),

            # Retry transitions
            StateTransition(
                TaskState.RETRY,
                TaskState.GENERATING_FIX,
                TransitionCondition.SUCCESS,
                "Retrying fix generation"
            ),
        ]

        return transitions

    def transition(self, result: str, error: Optional[str] = None, metadata: Optional[Dict] = None) -> TaskState:
        """
        Transition to next state based on current state and result.

        Args:
            result: Result condition (success, failure, etc.)
            error: Optional error message
            metadata: Optional metadata for state context

        Returns:
            New state after transition
        """
        # Record exit from current state
        if self.state_history:
            self.state_history[-1].exit_at = datetime.now()
            self.state_history[-1].result = result
            if error:
                self.state_history[-1].error = error

        # Find matching transition
        next_state = None
        for transition in self.transitions:
            if transition.matches(self.current_state, result):
                next_state = transition.to_state
                break

        if next_state is None:
            # No valid transition found
            raise ValueError(
                f"No valid transition from {self.current_state.value} with result '{result}'"
            )

        # Handle retry logic
        if next_state == TaskState.RETRY:
            # Check if we can retry the previous state
            retry_state = self._get_retry_state()
            if retry_state and self.retry_configs.get(retry_state):
                config = self.retry_configs[retry_state]
                if config.can_retry():
                    config.increment()
                    next_state = retry_state
                else:
                    # Retries exhausted
                    next_state = TaskState.FAILED
                    result = TransitionCondition.RETRY_EXHAUSTED.value

        # Enter new state
        self.current_state = next_state
        context = StateContext(
            state=next_state,
            entered_at=datetime.now(),
            metadata=metadata or {}
        )
        self.state_history.append(context)

        return next_state

    def _get_retry_state(self) -> Optional[TaskState]:
        """Get the state to retry (the state before RETRY)."""
        if len(self.state_history) >= 2:
            return self.state_history[-2].state
        return None

    def get_current_state(self) -> TaskState:
        """Get current state."""
        return self.current_state

    def is_terminal(self) -> bool:
        """Check if in terminal state."""
        return self.current_state.is_terminal()

    def is_successful(self) -> bool:
        """Check if completed successfully."""
        return self.current_state.is_successful()

    def get_history(self) -> List[StateContext]:
        """Get state history."""
        return self.state_history

    def get_summary(self) -> Dict[str, Any]:
        """Get workflow summary."""
        total_duration = 0.0
        if self.state_history:
            start = self.state_history[0].entered_at
            end = self.state_history[-1].exit_at or datetime.now()
            total_duration = (end - start).total_seconds()

        return {
            "current_state": self.current_state.value,
            "is_terminal": self.is_terminal(),
            "is_successful": self.is_successful(),
            "total_states": len(self.state_history),
            "total_duration_seconds": total_duration,
            "state_history": [s.to_dict() for s in self.state_history],
            "retry_counts": {
                state.value: config.retry_count
                for state, config in self.retry_configs.items()
                if config.retry_count > 0
            }
        }

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.get_summary(), indent=2)

    def visualize(self) -> str:
        """Create a text visualization of the state flow."""
        lines = ["ASA Workflow State Machine", "=" * 50, ""]

        for i, context in enumerate(self.state_history):
            duration = context.duration_seconds()
            duration_str = f"{duration:.2f}s" if duration else "ongoing"

            status_icon = "✓" if context.result == "success" else "✗" if context.result == "failure" else "•"

            lines.append(
                f"{i+1}. {status_icon} {context.state.value} ({duration_str})"
            )

            if context.error:
                lines.append(f"   Error: {context.error[:100]}")

            if context.metadata:
                for key, value in context.metadata.items():
                    lines.append(f"   {key}: {value}")

            if i < len(self.state_history) - 1:
                lines.append("   ↓")

        lines.append("")
        lines.append("=" * 50)
        lines.append(f"Final State: {self.current_state.value}")
        lines.append(f"Status: {'SUCCESS' if self.is_successful() else 'FAILED' if self.is_terminal() else 'IN PROGRESS'}")

        return "\n".join(lines)
