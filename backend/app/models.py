from sqlalchemy import Column, String, DateTime, Text, Float, Integer, Boolean
from sqlalchemy.sql import func
from .database import Base
import uuid

class Task(Base):
    __tablename__ = "tasks"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    repo_url = Column(String, nullable=False)
    bug_description = Column(Text, nullable=False)
    test_command = Column(String, nullable=True)
    status = Column(String, nullable=False, default="QUEUED")
    workspace_path = Column(String, nullable=True)
    branch_name = Column(String, nullable=True)
    pr_url = Column(String, nullable=True)
    logs = Column(Text, nullable=True)
    test_output_before = Column(Text, nullable=True)
    e2e_test_path = Column(String, nullable=True)
    job_id = Column(String, nullable=True, index=True)  # RQ job ID for queue tracking
    user_id = Column(String, nullable=True, index=True)  # For per-user limits
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class LLMUsage(Base):
    """Track LLM API usage for cost and observability."""
    __tablename__ = "llm_usage"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    task_id = Column(String, nullable=True, index=True)
    user_id = Column(String, nullable=True, index=True)
    model = Column(String, nullable=False)
    prompt_tokens = Column(Integer, nullable=False, default=0)
    completion_tokens = Column(Integer, nullable=False, default=0)
    total_tokens = Column(Integer, nullable=False, default=0)
    cost_usd = Column(Float, nullable=False, default=0.0)
    latency_ms = Column(Float, nullable=False, default=0.0)
    status = Column(String, nullable=False, default="success")
    error_message = Column(Text, nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)


class TaskMetrics(Base):
    """Track metrics for task execution and success rates."""
    __tablename__ = "task_metrics"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    task_id = Column(String, nullable=False, index=True)
    metric_name = Column(String, nullable=False)
    metric_value = Column(Float, nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)


class PromptVersion(Base):
    """Track versioned prompts with checksums."""
    __tablename__ = "prompt_versions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False, index=True)
    version = Column(String, nullable=False, index=True)
    template = Column(Text, nullable=False)
    variables = Column(Text, nullable=False)  # JSON array of variable names
    checksum = Column(String, nullable=False)
    meta_data = Column(Text, nullable=True)  # JSON metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)


class Feedback(Base):
    """User feedback on task execution for RLHF."""
    __tablename__ = "feedback"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    task_id = Column(String, nullable=False, index=True)
    user_id = Column(String, nullable=True, index=True)
    rating = Column(Integer, nullable=True)  # 1-5 scale
    approved = Column(Boolean, nullable=False, default=False)
    comment = Column(Text, nullable=True)
    issues = Column(Text, nullable=True)  # JSON array of issues
    feedback_type = Column(String, nullable=False, default="user")  # user|auto
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)


class EvaluationCase(Base):
    """Golden set of test cases for evaluation framework."""
    __tablename__ = "evaluation_cases"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False, unique=True, index=True)
    repo_url = Column(String, nullable=False)
    bug_description = Column(Text, nullable=False)
    test_command = Column(String, nullable=True)
    expected_behavior = Column(Text, nullable=False)  # What the fix should achieve
    difficulty = Column(String, nullable=False, default="medium")  # easy|medium|hard
    category = Column(String, nullable=True)  # bug_type: logic|syntax|integration|etc
    extra_metadata = Column(Text, nullable=True)  # JSON for extra info
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class EvaluationResult(Base):
    """Results from running evaluation cases."""
    __tablename__ = "evaluation_results"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    evaluation_case_id = Column(String, nullable=False, index=True)
    task_id = Column(String, nullable=False, index=True)
    passed = Column(Boolean, nullable=False, default=False)
    execution_time_seconds = Column(Float, nullable=True)
    cost_usd = Column(Float, nullable=True)
    reviewer_notes = Column(Text, nullable=True)
    metrics = Column(Text, nullable=True)  # JSON: correctness, quality, etc.
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
