"""
Patch Schema - Structured patch format for precise code modifications.

Provides line-accurate patch application with validation.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from pathlib import Path
import json
from enum import Enum


class PatchType(Enum):
    """Type of patch operation."""
    REPLACE = "replace"  # Replace specific lines
    INSERT = "insert"    # Insert new lines
    DELETE = "delete"    # Delete lines


@dataclass
class CodePatch:
    """
    Structured code patch with line-level precision.

    Attributes:
        file_path: Relative path to the file to patch
        patch_type: Type of operation (replace, insert, delete)
        start_line: Starting line number (1-indexed)
        end_line: Ending line number (1-indexed, inclusive)
        new_code: New code to apply (for replace/insert)
        description: Human-readable description of the change
    """
    file_path: str
    patch_type: PatchType
    start_line: int
    end_line: int
    new_code: str = ""
    description: str = ""

    def __post_init__(self):
        """Validate patch data."""
        if isinstance(self.patch_type, str):
            self.patch_type = PatchType(self.patch_type)

        if self.start_line < 1:
            raise ValueError(f"start_line must be >= 1, got {self.start_line}")

        if self.end_line < self.start_line:
            raise ValueError(f"end_line ({self.end_line}) must be >= start_line ({self.start_line})")

        if self.patch_type in (PatchType.REPLACE, PatchType.INSERT) and not self.new_code:
            raise ValueError(f"new_code required for {self.patch_type.value} operations")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "file_path": self.file_path,
            "patch_type": self.patch_type.value,
            "start_line": self.start_line,
            "end_line": self.end_line,
            "new_code": self.new_code,
            "description": self.description
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CodePatch':
        """Create patch from dictionary."""
        return cls(
            file_path=data["file_path"],
            patch_type=PatchType(data["patch_type"]),
            start_line=data["start_line"],
            end_line=data["end_line"],
            new_code=data.get("new_code", ""),
            description=data.get("description", "")
        )


@dataclass
class PatchSet:
    """
    Collection of patches with metadata.

    Attributes:
        patches: List of CodePatch objects
        bug_description: Original bug description
        confidence: Confidence score (0-1)
        rationale: Explanation of why these patches fix the bug
    """
    patches: List[CodePatch] = field(default_factory=list)
    bug_description: str = ""
    confidence: float = 0.0
    rationale: str = ""

    def add_patch(self, patch: CodePatch):
        """Add a patch to the set."""
        self.patches.append(patch)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "patches": [p.to_dict() for p in self.patches],
            "bug_description": self.bug_description,
            "confidence": self.confidence,
            "rationale": self.rationale
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PatchSet':
        """Create patch set from dictionary."""
        patches = [CodePatch.from_dict(p) for p in data.get("patches", [])]
        return cls(
            patches=patches,
            bug_description=data.get("bug_description", ""),
            confidence=data.get("confidence", 0.0),
            rationale=data.get("rationale", "")
        )

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_json(cls, json_str: str) -> 'PatchSet':
        """Create patch set from JSON string."""
        data = json.loads(json_str)
        return cls.from_dict(data)

    def validate(self, workspace_path: str) -> List[str]:
        """
        Validate all patches against actual files.

        Args:
            workspace_path: Path to the workspace

        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        workspace = Path(workspace_path)

        for i, patch in enumerate(self.patches):
            # Check file exists
            file_path = workspace / patch.file_path
            if not file_path.exists():
                errors.append(f"Patch {i+1}: File does not exist: {patch.file_path}")
                continue

            # Check line numbers are valid
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    total_lines = len(lines)

                    if patch.start_line > total_lines:
                        errors.append(
                            f"Patch {i+1}: start_line ({patch.start_line}) exceeds "
                            f"file length ({total_lines}) in {patch.file_path}"
                        )

                    if patch.end_line > total_lines:
                        errors.append(
                            f"Patch {i+1}: end_line ({patch.end_line}) exceeds "
                            f"file length ({total_lines}) in {patch.file_path}"
                        )

            except Exception as e:
                errors.append(f"Patch {i+1}: Error reading {patch.file_path}: {e}")

        return errors


class PatchValidator:
    """Validates patches before application."""

    @staticmethod
    def validate_syntax(patch: CodePatch) -> List[str]:
        """
        Validate patch syntax (basic checks).

        Returns:
            List of validation errors
        """
        errors = []

        # Check line numbers
        if patch.start_line < 1:
            errors.append(f"Invalid start_line: {patch.start_line} (must be >= 1)")

        if patch.end_line < patch.start_line:
            errors.append(
                f"Invalid line range: {patch.start_line}-{patch.end_line} "
                f"(end_line must be >= start_line)"
            )

        # Check new_code for replace/insert
        if patch.patch_type in (PatchType.REPLACE, PatchType.INSERT):
            if not patch.new_code.strip():
                errors.append(f"{patch.patch_type.value} operation requires non-empty new_code")

        return errors

    @staticmethod
    def validate_file(patch: CodePatch, workspace_path: str) -> List[str]:
        """
        Validate patch against actual file.

        Returns:
            List of validation errors
        """
        errors = []
        file_path = Path(workspace_path) / patch.file_path

        if not file_path.exists():
            errors.append(f"File does not exist: {patch.file_path}")
            return errors

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                total_lines = len(lines)

                if patch.start_line > total_lines:
                    errors.append(
                        f"start_line ({patch.start_line}) exceeds file length ({total_lines})"
                    )

                if patch.end_line > total_lines:
                    errors.append(
                        f"end_line ({patch.end_line}) exceeds file length ({total_lines})"
                    )

        except Exception as e:
            errors.append(f"Error reading file: {e}")

        return errors
