from sqlalchemy import Column, String, DateTime, Text, Float, Integer
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
    metadata = Column(Text, nullable=True)  # JSON metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

