"""
Fix Agent - LLM-driven code fix generation.

Handles:
- Generating code fixes from test failures
- Applying patches to source files
"""

import os
import json
from typing import List, Dict, Any
from pathlib import Path
from openai import OpenAI

from app.services.code_index import CodeIndex, CodeSnippet
try:
    from app.services.semantic_index import SemanticCodeIndex, SearchResult
except ImportError:
    SemanticCodeIndex = None
    SearchResult = None


class FixAgent:
    """LLM-driven agent for generating code fixes."""

    def __init__(self, api_key: str = None):
        """
        Initialize FixAgent with OpenAI API key.

        Args:
            api_key: OpenAI API key. If None, will try to load from OPENAI_API_KEY env var.
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key not provided. Set OPENAI_API_KEY environment variable.")

        self.client = OpenAI(api_key=self.api_key)

    def generate_patch(self, task, failing_output: str, code_index) -> List[Dict[str, str]]:
        """
        Generate a structured patch to fix the failing tests.

        Args:
            task: Task object with bug_description attribute
            failing_output: Output from the failing test run
            code_index: CodeIndex or SemanticCodeIndex instance for searching relevant code

        Returns:
            List of patch dictionaries with format:
            [
                {
                    "file_path": "path/to/file.py",
                    "old_snippet": "original code",
                    "new_snippet": "fixed code"
                }
            ]
        """
        # Get context using semantic or simple search
        if hasattr(code_index, 'get_context'):
            # SemanticCodeIndex has a get_context method
            context = code_index.get_context(task.bug_description, max_results=5)
        else:
            # Legacy CodeIndex - search and build context manually
            snippets = code_index.search(task.bug_description, max_results=5)
            context = self._build_context(snippets)

        # Create prompt for LLM
        prompt = self._create_fix_prompt(
            bug_description=task.bug_description,
            failing_output=failing_output,
            code_context=context
        )

        # Call OpenAI API
        try:
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert software engineer that fixes bugs in Python code. "
                                   "You provide minimal, focused patches in JSON format."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.2,
                max_tokens=2000
            )

            # Parse the response
            patch_json = response.choices[0].message.content.strip()

            # Extract JSON from markdown code blocks if present
            if "```json" in patch_json:
                patch_json = patch_json.split("```json")[1].split("```")[0].strip()
            elif "```" in patch_json:
                patch_json = patch_json.split("```")[1].split("```")[0].strip()

            patches = json.loads(patch_json)

            # Validate patch format
            if not isinstance(patches, list):
                patches = [patches]

            for patch in patches:
                if not all(k in patch for k in ["file_path", "old_snippet", "new_snippet"]):
                    raise ValueError(f"Invalid patch format: {patch}")

            return patches

        except Exception as e:
            print(f"Error generating patch: {e}")
            raise Exception(f"Failed to generate patch: {str(e)}")

    def _build_context(self, snippets: List[CodeSnippet]) -> str:
        """Build context string from code snippets."""
        if not snippets:
            return "No relevant code found."

        context_parts = []
        for i, snippet in enumerate(snippets, 1):
            context_parts.append(
                f"### File {i}: {snippet.file_path} (lines {snippet.start_line}-{snippet.end_line})\n"
                f"```python\n{snippet.snippet}\n```"
            )

        return "\n\n".join(context_parts)

    def _create_fix_prompt(self, bug_description: str, failing_output: str, code_context: str) -> str:
        """Create the prompt for the LLM to generate a fix."""
        return f"""You are tasked with fixing a bug in a Python codebase.

**Bug Description:**
{bug_description}

**Failing Test Output:**
```
{failing_output[-2000:]}
```

**Relevant Code Context:**
{code_context}

**Your Task:**
Analyze the bug description, test failure, and code context. Generate a minimal patch to fix the issue.

**Output Format:**
Respond with ONLY a JSON array of patches. Each patch must have:
- "file_path": The full path to the file (use paths from the code context)
- "old_snippet": The exact code to replace (must match the file exactly, including whitespace)
- "new_snippet": The corrected code

**Important Guidelines:**
1. Keep patches minimal - only change what's necessary
2. Ensure "old_snippet" matches the file EXACTLY (whitespace matters)
3. Provide complete function/method bodies, not fragments
4. Include proper indentation
5. Only fix the specific bug described

**Example Output:**
[
  {{
    "file_path": "/path/to/file.py",
    "old_snippet": "def broken_function():\\n    return wrong_value",
    "new_snippet": "def broken_function():\\n    return correct_value"
  }}
]

Generate the patch now (JSON only, no explanations):"""


def apply_patches(patches: List[Dict[str, str]], workspace_path: str = None) -> None:
    """
    Apply a list of patches to source files.

    Args:
        patches: List of patch dictionaries with file_path, old_snippet, new_snippet
        workspace_path: Optional workspace path to prepend to relative file paths
    """
    for i, patch in enumerate(patches, 1):
        file_path = patch["file_path"]
        old_snippet = patch["old_snippet"]
        new_snippet = patch["new_snippet"]

        # If workspace_path is provided and file_path is not absolute, join them
        if workspace_path and not Path(file_path).is_absolute():
            file_path = str(Path(workspace_path) / file_path)

        # Read the file
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except FileNotFoundError:
            print(f"Warning: File not found: {file_path}")
            continue

        # Apply the patch
        if old_snippet not in content:
            print(f"Warning: old_snippet not found in {file_path}")
            print(f"Looking for:\n{old_snippet[:200]}...")
            continue

        new_content = content.replace(old_snippet, new_snippet, 1)

        # Write back
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)

        print(f"Applied patch {i}/{len(patches)} to {file_path}")
