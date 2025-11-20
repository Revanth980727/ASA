"""
Unit Tests for Prompt Loader and Versioning.

Tests prompt loading, schema validation, and version management.
"""

import pytest
import json
from pathlib import Path

from app.core.prompt_loader import PromptLoader, PromptVersion, load_prompt
from app.core.limits import LLMPurpose


class TestPromptLoader:
    """Test the PromptLoader class."""

    def test_load_guardian_prompt(self):
        """Test loading the guardian prompt."""
        loader = PromptLoader()
        prompt = loader.load_prompt(LLMPurpose.GUARDIAN, version="v1")

        assert prompt is not None
        assert prompt.purpose == "GUARDIAN"
        assert prompt.schema_version == "v1"
        assert prompt.version == "1.0.0"
        assert prompt.checksum is not None

    def test_load_cit_prompt(self):
        """Test loading the CIT generation prompt."""
        loader = PromptLoader()
        prompt = loader.load_prompt(LLMPurpose.CIT_GENERATION, version="v1")

        assert prompt is not None
        assert prompt.purpose == "CIT_GENERATION"
        assert prompt.schema_version == "v1"

    def test_load_code_agent_prompt(self):
        """Test loading the code agent (fix generation) prompt."""
        loader = PromptLoader()
        prompt = loader.load_prompt(LLMPurpose.FIX_GENERATION, version="v1")

        assert prompt is not None
        assert prompt.purpose == "FIX_GENERATION"
        assert prompt.schema_version == "v1"

    def test_prompt_caching(self):
        """Test that prompts are cached."""
        loader = PromptLoader()

        # Load same prompt twice
        prompt1 = loader.load_prompt(LLMPurpose.GUARDIAN, "v1")
        prompt2 = loader.load_prompt(LLMPurpose.GUARDIAN, "v1")

        # Should return same cached instance
        assert prompt1 is prompt2

    def test_load_nonexistent_version(self):
        """Test that loading nonexistent version raises error."""
        loader = PromptLoader()

        with pytest.raises(FileNotFoundError):
            loader.load_prompt(LLMPurpose.GUARDIAN, version="v999")


class TestPromptVersion:
    """Test the PromptVersion class."""

    def test_render_user_prompt(self):
        """Test rendering user prompt with variables."""
        loader = PromptLoader()
        prompt = loader.load_prompt(LLMPurpose.GUARDIAN, "v1")

        rendered = prompt.render_user_prompt(
            bug_description="Test bug",
            proposed_fix="Test fix",
            code_context="Test context"
        )

        assert "Test bug" in rendered
        assert "Test fix" in rendered
        assert "Test context" in rendered

    def test_get_messages(self):
        """Test getting OpenAI-formatted messages."""
        loader = PromptLoader()
        prompt = loader.load_prompt(LLMPurpose.GUARDIAN, "v1")

        messages = prompt.get_messages(
            bug_description="Test",
            proposed_fix="Fix",
            code_context="Context"
        )

        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"
        assert "Test" in messages[1]["content"]

    def test_validate_response_valid(self):
        """Test validating a valid response."""
        loader = PromptLoader()
        prompt = loader.load_prompt(LLMPurpose.GUARDIAN, "v1")

        # Valid guardian response
        response = {
            "safe": True,
            "risk_level": "low",
            "issues": [],
            "recommendation": "approve",
            "rationale": "No issues found"
        }

        # Should not raise
        assert prompt.validate_response(response) is True

    def test_validate_response_missing_field(self):
        """Test that missing required fields raise ValueError."""
        loader = PromptLoader()
        prompt = loader.load_prompt(LLMPurpose.GUARDIAN, "v1")

        # Missing 'safe' field
        response = {
            "risk_level": "low",
            "issues": [],
            "recommendation": "approve",
            "rationale": "Test"
        }

        with pytest.raises(ValueError, match="missing required field"):
            prompt.validate_response(response)

    def test_to_metadata(self):
        """Test converting prompt to metadata dict."""
        loader = PromptLoader()
        prompt = loader.load_prompt(LLMPurpose.GUARDIAN, "v1")

        metadata = prompt.to_metadata()

        assert "prompt_version" in metadata
        assert "schema_version" in metadata
        assert "checksum" in metadata
        assert "purpose" in metadata
        assert metadata["schema_version"] == "v1"


class TestPromptSchemas:
    """Test that prompt schemas are well-formed."""

    def test_guardian_schema_structure(self):
        """Test that guardian prompt has correct schema structure."""
        loader = PromptLoader()
        prompt = loader.load_prompt(LLMPurpose.GUARDIAN, "v1")

        schema = prompt.output_schema

        assert schema["type"] == "object"
        assert "required" in schema
        assert "properties" in schema
        assert "safe" in schema["required"]
        assert "risk_level" in schema["required"]

    def test_cit_schema_structure(self):
        """Test that CIT prompt has correct schema structure."""
        loader = PromptLoader()
        prompt = loader.load_prompt(LLMPurpose.CIT_GENERATION, "v1")

        schema = prompt.output_schema

        assert schema["type"] == "object"
        assert "required" in schema
        assert "test_code" in schema["required"]
        assert "expected_behavior" in schema["required"]

    def test_code_agent_schema_structure(self):
        """Test that code agent prompt has correct schema structure."""
        loader = PromptLoader()
        prompt = loader.load_prompt(LLMPurpose.FIX_GENERATION, "v1")

        schema = prompt.output_schema

        assert schema["type"] == "object"
        assert "required" in schema
        assert "patches" in schema["required"]
        assert "rationale" in schema["required"]
        assert "confidence" in schema["required"]


class TestConvenienceFunctions:
    """Test convenience functions."""

    def test_load_prompt_function(self):
        """Test the load_prompt convenience function."""
        prompt = load_prompt(LLMPurpose.GUARDIAN, "v1")

        assert prompt is not None
        assert prompt.purpose == "GUARDIAN"

    def test_load_prompt_uses_singleton(self):
        """Test that load_prompt uses singleton loader."""
        prompt1 = load_prompt(LLMPurpose.GUARDIAN, "v1")
        prompt2 = load_prompt(LLMPurpose.GUARDIAN, "v1")

        # Should be same cached instance
        assert prompt1 is prompt2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
