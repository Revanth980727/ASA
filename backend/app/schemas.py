from pydantic import BaseModel, Field, field_validator, ConfigDict
from datetime import datetime
from typing import Optional, List, Dict, Any

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
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    task_id: str = Field(alias="id")
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
    schema_version: str = Field(default="v1", description="API schema version")

class TaskListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    task_id: str = Field(alias="id")
    repo_url: str
    bug_description: str
    status: str
    pr_url: Optional[str]
    logs: Optional[str]
    created_at: datetime
    updated_at: datetime

class FeedbackSubmit(BaseModel):
    """User feedback for RLHF (Reinforcement Learning from Human Feedback)"""
    rating: int = Field(..., ge=1, le=5, description="Rating from 1-5")
    approved: bool = Field(..., description="Whether the fix is approved")
    comment: Optional[str] = Field(None, description="Optional feedback comment")
    issues: Optional[List[str]] = Field(default_factory=list, description="List of issues found")


# LLM Response Schemas with versioning

class GuardianResponse(BaseModel):
    """Guardian LLM response schema (v1)"""
    schema_version: str = Field(default="v1", description="Schema version")
    safe: bool = Field(..., description="Overall safety verdict")
    risk_level: str = Field(..., description="Risk level: low, medium, high, critical")
    issues: List[Dict[str, Any]] = Field(default_factory=list, description="Security/policy issues found")
    recommendation: str = Field(..., description="Action: approve, reject, require_review")
    rationale: str = Field(..., description="Explanation of decision")


class CITResponse(BaseModel):
    """CIT generation LLM response schema (v1)"""
    schema_version: str = Field(default="v1", description="Schema version")
    test_code: str = Field(..., description="Complete Playwright test code")
    test_description: str = Field(..., description="Brief description of what the test verifies")
    expected_behavior: Dict[str, str] = Field(..., description="Expected test results before/after fix")
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0, description="Confidence in test quality")


class CodeAgentPatch(BaseModel):
    """Individual patch in a code fix"""
    file_path: str = Field(..., description="Relative path to file to patch")
    patch_type: str = Field(..., description="Type: replace, insert, delete")
    start_line: int = Field(..., ge=1, description="Starting line number (1-indexed)")
    end_line: Optional[int] = Field(None, ge=1, description="Ending line number (for replace/delete)")
    new_code: Optional[str] = Field(None, description="New code (for replace/insert)")
    description: str = Field(..., description="What this patch does")


class CodeAgentResponse(BaseModel):
    """Code agent (fix generation) LLM response schema (v1)"""
    schema_version: str = Field(default="v1", description="Schema version")
    patches: List[CodeAgentPatch] = Field(..., min_length=1, description="List of patches to apply")
    rationale: str = Field(..., description="Why these patches fix the bug")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score for fix quality")
    test_plan: Optional[str] = Field(None, description="How to verify the fix works")

