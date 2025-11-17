from sqlalchemy import Column, String, DateTime, Text
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
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

