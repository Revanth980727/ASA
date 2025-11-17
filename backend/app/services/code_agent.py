"""
Code Agent - Enhanced fix generator with structured patches and line-level precision.

Generates precise code fixes using LLMs with:
- Structured JSON patch output
- Line-accurate modifications
- Context-aware prompts
- Validation and safety checks
"""

import os
import json
from typing import List, Optional, Dict, Any
from openai import OpenAI

from app.services.patch_schema import CodePatch, PatchSet, PatchType
from app.services.patch_applicator import PatchApplicator

try:
    from app.services.llm_client import LLMClient
    HAS_LLM_CLIENT = True
except ImportError:
    HAS_LLM_CLIENT = False


class CodeAgent:
    """
    Enhanced code fix generator using LLMs and structured patches.

    Generates precise, line-accurate patches based on:
    - Bug description
    - Test failure logs
    - Extracted code context
    - Semantic code index
    """

    def __init__(self, api_key: str = None, task_id: Optional[str] = None, user_id: Optional[str] = None):
        """
        Initialize Code Agent.

        Args:
            api_key: OpenAI API key. If None, loads from OPENAI_API_KEY env var.
            task_id: Optional task ID for usage tracking
            user_id: Optional user ID for usage tracking
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key not provided. Set OPENAI_API_KEY environment variable.")

        self.task_id = task_id
        self.user_id = user_id

        # Use LLMClient wrapper if available for tracking, otherwise fallback to direct client
        if HAS_LLM_CLIENT:
            self.llm_client = LLMClient(api_key=self.api_key, task_id=task_id, user_id=user_id)
            self.client = None
        else:
            self.client = OpenAI(api_key=self.api_key)
            self.llm_client = None

    def generate_fix(
        self,
        bug_description: str,
        test_failure_log: str,
        code_context: str,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> PatchSet:
        """
        Generate a structured fix using LLM.

        Args:
            bug_description: Description of the bug to fix
            test_failure_log: Output from failing tests
            code_context: Relevant code snippets from semantic search
            additional_context: Optional additional context (file paths, etc.)

        Returns:
            PatchSet with generated patches
        """
        # Build comprehensive prompt
        prompt = self._build_fix_prompt(
            bug_description=bug_description,
            test_failure_log=test_failure_log,
            code_context=code_context,
            additional_context=additional_context
        )

        # Call LLM (with tracking if available)
        try:
            messages = [
                {
                    "role": "system",
                    "content": self._get_system_prompt()
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ]

            if self.llm_client:
                # Use tracked client
                response = self.llm_client.chat_completion(
                    messages=messages,
                    model="gpt-4",
                    temperature=0.2,
                    max_tokens=3000
                )
            else:
                # Fallback to direct client
                response = self.client.chat.completions.create(
                    model="gpt-4",
                    messages=messages,
                    temperature=0.2,
                    max_tokens=3000
                )

            # Parse response
            patch_json = response.choices[0].message.content.strip()

            # Extract JSON from markdown if needed
            patch_json = self._extract_json(patch_json)

            # Parse into PatchSet
            patch_set = PatchSet.from_json(patch_json)

            print(f"Generated {len(patch_set.patches)} patch(es)")
            return patch_set

        except Exception as e:
            print(f"Error generating fix: {e}")
            raise Exception(f"Failed to generate fix: {str(e)}")

    def _get_system_prompt(self) -> str:
        """Get the system prompt for the LLM."""
        return """You are an expert software engineer specializing in bug fixes.

Your task is to generate PRECISE, MINIMAL code patches that fix bugs.

CRITICAL REQUIREMENTS:
1. Output ONLY valid JSON matching the schema exactly
2. Use line numbers from the provided code context
3. Make MINIMAL changes - only what's needed to fix the bug
4. Provide clear descriptions for each patch
5. Include a rationale explaining why the patches fix the bug
6. Set a confidence score (0.0-1.0) based on how certain you are

PATCH TYPES:
- "replace": Replace lines start_line to end_line with new_code
- "insert": Insert new_code before start_line
- "delete": Delete lines start_line to end_line

OUTPUT SCHEMA:
{
  "patches": [
    {
      "file_path": "relative/path/to/file.py",
      "patch_type": "replace|insert|delete",
      "start_line": <line_number>,
      "end_line": <line_number>,
      "new_code": "<exact code to insert/replace>",
      "description": "What this patch does"
    }
  ],
  "bug_description": "The original bug",
  "confidence": 0.85,
  "rationale": "Why these patches fix the bug"
}

IMPORTANT:
- Line numbers are 1-indexed
- end_line is inclusive
- Preserve exact indentation in new_code
- Include complete function/method bodies
- Use \\n for newlines in JSON strings"""

    def _build_fix_prompt(
        self,
        bug_description: str,
        test_failure_log: str,
        code_context: str,
        additional_context: Optional[Dict[str, Any]]
    ) -> str:
        """Build the detailed fix-generation prompt."""
        prompt_parts = [
            "# Bug Fix Request\n",
            "## Bug Description",
            bug_description,
            "\n## Test Failure Log",
            "```",
            test_failure_log[-2000:],  # Last 2000 chars
            "```",
            "\n## Relevant Code Context",
            code_context
        ]

        if additional_context:
            prompt_parts.append("\n## Additional Context")
            for key, value in additional_context.items():
                prompt_parts.append(f"**{key}**: {value}")

        prompt_parts.extend([
            "\n## Your Task",
            "Analyze the bug, test failure, and code context.",
            "Generate MINIMAL, PRECISE patches to fix the bug.",
            "Output ONLY the JSON patch set (no explanations before or after).",
            "\nGenerate the patches now:"
        ])

        return "\n".join(prompt_parts)

    def _extract_json(self, response: str) -> str:
        """Extract JSON from LLM response (handles markdown code blocks)."""
        # Try to find JSON code block
        if "```json" in response:
            parts = response.split("```json")
            if len(parts) > 1:
                json_part = parts[1].split("```")[0]
                return json_part.strip()

        if "```" in response:
            parts = response.split("```")
            if len(parts) > 1:
                # Try middle part
                for part in parts[1:-1]:
                    part = part.strip()
                    if part.startswith('{'):
                        return part

        # No code blocks, try to find JSON object
        start = response.find('{')
        if start != -1:
            # Find matching closing brace
            depth = 0
            for i, char in enumerate(response[start:]):
                if char == '{':
                    depth += 1
                elif char == '}':
                    depth -= 1
                    if depth == 0:
                        return response[start:start+i+1]

        return response.strip()

    def apply_fix(
        self,
        patch_set: PatchSet,
        workspace_path: str,
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """
        Apply generated patches to workspace.

        Args:
            patch_set: PatchSet to apply
            workspace_path: Path to workspace
            dry_run: If True, validate without applying

        Returns:
            Results dictionary from PatchApplicator
        """
        applicator = PatchApplicator(workspace_path, create_backups=True)

        results = applicator.apply_patch_set(
            patch_set=patch_set,
            dry_run=dry_run,
            fail_fast=False  # Try to apply all patches
        )

        return results

    def preview_fix(
        self,
        patch_set: PatchSet,
        workspace_path: str
    ) -> str:
        """
        Generate a preview of what the patches will do.

        Args:
            patch_set: PatchSet to preview
            workspace_path: Path to workspace

        Returns:
            Human-readable preview string
        """
        applicator = PatchApplicator(workspace_path, create_backups=False)

        preview_parts = [
            f"Fix Preview ({len(patch_set.patches)} patches)",
            "=" * 60,
            f"\nBug: {patch_set.bug_description[:100]}...",
            f"Confidence: {patch_set.confidence:.2f}",
            f"Rationale: {patch_set.rationale}",
            "\n" + "=" * 60
        ]

        for i, patch in enumerate(patch_set.patches, 1):
            preview_parts.append(f"\n\n## Patch {i}/{len(patch_set.patches)}")
            preview_parts.append(applicator.get_patch_preview(patch))

        return "\n".join(preview_parts)


def generate_and_apply_fix(
    bug_description: str,
    test_failure_log: str,
    code_index,
    workspace_path: str,
    dry_run: bool = False
) -> Dict[str, Any]:
    """
    Convenience function: generate fix from code index and apply.

    Args:
        bug_description: Bug description
        test_failure_log: Test failure output
        code_index: CodeIndex or SemanticCodeIndex
        workspace_path: Workspace path
        dry_run: If True, validate without applying

    Returns:
        Dictionary with:
        - patch_set: Generated PatchSet
        - results: Application results
        - preview: Human-readable preview
    """
    agent = CodeAgent()

    # Get code context from index
    if hasattr(code_index, 'get_context'):
        # Semantic index
        code_context = code_index.get_context(bug_description, max_results=5)
    else:
        # Legacy index
        from app.services.code_index import CodeSnippet
        snippets = code_index.search(bug_description, max_results=5)

        context_parts = []
        for i, snippet in enumerate(snippets, 1):
            context_parts.append(
                f"### File {i}: {snippet.file_path} (lines {snippet.start_line}-{snippet.end_line})\n"
                f"```python\n{snippet.snippet}\n```"
            )
        code_context = "\n\n".join(context_parts)

    # Generate fix
    patch_set = agent.generate_fix(
        bug_description=bug_description,
        test_failure_log=test_failure_log,
        code_context=code_context
    )

    # Preview
    preview = agent.preview_fix(patch_set, workspace_path)
    print(preview)

    # Apply
    results = agent.apply_fix(patch_set, workspace_path, dry_run=dry_run)

    return {
        "patch_set": patch_set,
        "results": results,
        "preview": preview
    }
