from dataclasses import dataclass
from pathlib import Path
import os

@dataclass
class CodeSnippet:
    file_path: str
    start_line: int
    end_line: int
    snippet: str

class CodeIndex:
    def __init__(self, workspace_path: str):
        self.workspace_path = Path(workspace_path)
        self.file_contents: dict[str, str] = {}  # file_path -> content

    def build_index(self) -> None:
        """Walk the workspace and read Python files, storing content in memory."""
        skip_dirs = {'.git', 'venv', 'node_modules', 'dist', 'build'}

        for py_file in self.workspace_path.rglob('*.py'):
            # Check if any part of the path is in skip_dirs
            if any(part in skip_dirs for part in py_file.parts):
                continue

            try:
                with open(py_file, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                self.file_contents[str(py_file)] = content
            except Exception as e:
                print(f"Error reading {py_file}: {e}")

    def search(self, bug_description: str, max_results: int = 10) -> list[CodeSnippet]:
        """Simple search: split bug_description into words, find files containing any word."""
        words = bug_description.lower().split()
        matching_snippets = []

        for file_path, content in self.file_contents.items():
            content_lower = content.lower()
            if any(word in content_lower for word in words):
                # Get first 40 lines as snippet
                lines = content.split('\n')[:40]
                snippet = '\n'.join(lines)
                code_snippet = CodeSnippet(
                    file_path=file_path,
                    start_line=1,
                    end_line=min(40, len(lines)),
                    snippet=snippet
                )
                matching_snippets.append(code_snippet)

                if len(matching_snippets) >= max_results:
                    break

        return matching_snippets