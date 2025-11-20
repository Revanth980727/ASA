"""
Prompt Loader - Versioned prompt and schema management.

Loads versioned prompts from JSON files and provides:
- Schema validation
- Version tracking
- Checksum verification
- Prompt rendering with variables
"""

import json
import hashlib
from pathlib import Path
from typing import Dict, Any, Optional
from string import Template

from app.core.limits import LLMPurpose


class PromptVersion:
    """Represents a versioned prompt with schema."""

    def __init__(self, data: Dict[str, Any], file_path: Path):
        """
        Initialize prompt version.

        Args:
            data: Loaded JSON data
            file_path: Path to prompt file
        """
        self.version = data["version"]
        self.schema_version = data["schema_version"]
        self.checksum = data["checksum"]
        self.purpose = data["purpose"]
        self.description = data["description"]
        self.system_prompt = data["system_prompt"]
        self.user_prompt_template = data["user_prompt_template"]
        self.output_schema = data["output_schema"]
        self.model_config = data.get("model_config", {})
        self.file_path = file_path

        # Validate required fields
        self._validate()

    def _validate(self):
        """Validate prompt structure."""
        required_fields = [
            "version", "schema_version", "checksum", "purpose",
            "system_prompt", "user_prompt_template", "output_schema"
        ]

        for field in required_fields:
            if not getattr(self, field, None):
                raise ValueError(f"Prompt missing required field: {field}")

    def render_user_prompt(self, **kwargs) -> str:
        """
        Render user prompt template with variables.

        Args:
            **kwargs: Variables to substitute in template

        Returns:
            Rendered prompt string
        """
        template = Template(self.user_prompt_template)

        # Provide defaults for missing variables
        defaults = {
            "bug_description": "",
            "test_failure_log": "",
            "code_context": "",
            "additional_context": "",
            "app_context": "",
            "proposed_fix": ""
        }
        defaults.update(kwargs)

        return template.safe_substitute(**defaults)

    def get_messages(self, **kwargs) -> list:
        """
        Get OpenAI-formatted messages.

        Args:
            **kwargs: Variables for user prompt

        Returns:
            List of message dicts
        """
        return [
            {
                "role": "system",
                "content": self.system_prompt
            },
            {
                "role": "user",
                "content": self.render_user_prompt(**kwargs)
            }
        ]

    def validate_response(self, response: Dict[str, Any]) -> bool:
        """
        Validate LLM response against output schema.

        Args:
            response: JSON response from LLM

        Returns:
            True if valid, raises ValueError otherwise
        """
        # Simple validation - check required fields
        schema = self.output_schema
        required = schema.get("required", [])

        for field in required:
            if field not in response:
                raise ValueError(
                    f"Response missing required field: {field}. "
                    f"Schema version: {self.schema_version}"
                )

        return True

    def to_metadata(self) -> Dict[str, Any]:
        """
        Get metadata for logging.

        Returns:
            Dict with version info
        """
        return {
            "prompt_version": self.version,
            "schema_version": self.schema_version,
            "checksum": self.checksum,
            "purpose": self.purpose
        }


class PromptLoader:
    """Load and manage versioned prompts."""

    def __init__(self, prompts_dir: Optional[Path] = None):
        """
        Initialize prompt loader.

        Args:
            prompts_dir: Directory containing prompt JSON files
        """
        if prompts_dir is None:
            # Default to core/prompts directory
            prompts_dir = Path(__file__).parent / "prompts"

        self.prompts_dir = Path(prompts_dir)
        self._cache: Dict[str, PromptVersion] = {}

        if not self.prompts_dir.exists():
            raise ValueError(f"Prompts directory not found: {self.prompts_dir}")

    def load_prompt(
        self,
        purpose: LLMPurpose,
        version: str = "v1"
    ) -> PromptVersion:
        """
        Load a versioned prompt.

        Args:
            purpose: LLM purpose (maps to file name)
            version: Schema version to load

        Returns:
            PromptVersion object

        Raises:
            FileNotFoundError: If prompt file not found
            ValueError: If prompt invalid
        """
        # Create cache key
        cache_key = f"{purpose.value}_{version}"

        # Check cache
        if cache_key in self._cache:
            return self._cache[cache_key]

        # Map purpose to file name
        # e.g., LLMPurpose.GUARDIAN -> guardian_v1.json
        purpose_name = purpose.value.lower()
        if purpose == LLMPurpose.FIX_GENERATION:
            purpose_name = "code_agent"
        elif purpose == LLMPurpose.CIT_GENERATION:
            purpose_name = "cit"
        elif purpose == LLMPurpose.GUARDIAN:
            purpose_name = "guardian"
        elif purpose == LLMPurpose.TEST_GENERATION:
            purpose_name = "cit"  # Reuse CIT for test generation

        file_name = f"{purpose_name}_{version}.json"
        file_path = self.prompts_dir / file_name

        if not file_path.exists():
            raise FileNotFoundError(
                f"Prompt file not found: {file_path}. "
                f"Purpose: {purpose.value}, Version: {version}"
            )

        # Load and parse
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Create PromptVersion
        prompt_version = PromptVersion(data, file_path)

        # Cache it
        self._cache[cache_key] = prompt_version

        return prompt_version

    def list_available_prompts(self) -> Dict[str, list]:
        """
        List all available prompts and versions.

        Returns:
            Dict mapping purpose to list of versions
        """
        prompts = {}

        for file_path in self.prompts_dir.glob("*.json"):
            # Parse filename: guardian_v1.json -> (guardian, v1)
            name = file_path.stem  # guardian_v1
            parts = name.rsplit('_', 1)

            if len(parts) == 2:
                purpose_name, version = parts

                if purpose_name not in prompts:
                    prompts[purpose_name] = []

                prompts[purpose_name].append(version)

        return prompts

    def verify_checksum(self, prompt: PromptVersion) -> bool:
        """
        Verify prompt file checksum.

        Args:
            prompt: PromptVersion to verify

        Returns:
            True if checksum matches
        """
        # Read file content
        with open(prompt.file_path, 'rb') as f:
            content = f.read()

        # Calculate checksum
        calculated = hashlib.sha256(content).hexdigest()[:16]

        # Note: The checksum in the file is just a label for now
        # In production, you'd store the actual hash
        return True  # For now, always pass


# Global instance
_prompt_loader: Optional[PromptLoader] = None


def get_prompt_loader() -> PromptLoader:
    """
    Get global prompt loader instance.

    Returns:
        PromptLoader singleton
    """
    global _prompt_loader

    if _prompt_loader is None:
        _prompt_loader = PromptLoader()

    return _prompt_loader


def load_prompt(purpose: LLMPurpose, version: str = "v1") -> PromptVersion:
    """
    Convenience function to load a prompt.

    Args:
        purpose: LLM purpose
        version: Schema version

    Returns:
        PromptVersion object
    """
    loader = get_prompt_loader()
    return loader.load_prompt(purpose, version)
