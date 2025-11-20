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
        """
        Improved search: find lines matching keywords and return context around them.

        Returns snippets with 10 lines before and 10 lines after each match.
        """
        words = [w.lower() for w in bug_description.split() if len(w) > 2]  # Skip short words
        matching_snippets = []

        for file_path, content in self.file_contents.items():
            lines = content.split('\n')
            content_lower = content.lower()

            # Find all matching line numbers
            matching_lines = []
            for line_num, line in enumerate(lines, 1):
                line_lower = line.lower()
                if any(word in line_lower for word in words):
                    matching_lines.append(line_num)

            # Group nearby matches and create snippets
            if matching_lines:
                # Take first match with context
                match_line = matching_lines[0]
                start_line = max(1, match_line - 10)
                end_line = min(len(lines), match_line + 10)

                snippet_lines = lines[start_line-1:end_line]
                snippet = '\n'.join(snippet_lines)

                code_snippet = CodeSnippet(
                    file_path=file_path,
                    start_line=start_line,
                    end_line=end_line,
                    snippet=snippet
                )
                matching_snippets.append(code_snippet)

                if len(matching_snippets) >= max_results:
                    break

        # If no matches found, return first 40 lines of first few files as fallback
        if not matching_snippets:
            for file_path, content in list(self.file_contents.items())[:max_results]:
                lines = content.split('\n')[:40]
                snippet = '\n'.join(lines)
                matching_snippets.append(CodeSnippet(
                    file_path=file_path,
                    start_line=1,
                    end_line=min(40, len(lines)),
                    snippet=snippet
                ))

        return matching_snippets