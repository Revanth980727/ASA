from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from typing import Optional

class TaskSubmit(BaseModel):
    repo_url: str = Field(..., min_length=1, description="Git repository URL")
    bug_description: str = Field(..., min_length=1, description="Description of the bug to fix")
    test_command: Optional[str] = Field(None, description="Test command to run (e.g., 'pytest', 'npm test')")

    @field_validator('repo_url')
    @classmethod
    def validate_repo_url(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError('repo_url cannot be empty')
        return v

    @field_validator('bug_description')
    @classmethod
    def validate_bug_description(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError('bug_description cannot be empty')
        return v

class TaskResponse(BaseModel):
    task_id: str
    status: str

class TaskDetail(BaseModel):
    task_id: str
    repo_url: str
    bug_description: str
    test_command: Optional[str]
    status: str
    workspace_path: Optional[str]
    branch_name: Optional[str]
    pr_url: Optional[str]
    logs: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class TaskListItem(BaseModel):
    task_id: str
    repo_url: str
    status: str
    pr_url: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

