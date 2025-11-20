"""
AST Parser Service - Uses tree-sitter for structural code parsing.

Extracts functions, classes, and methods from Python source code.
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from pathlib import Path
import tree_sitter_python as tspython
from tree_sitter import Language, Parser


@dataclass
class CodeNode:
    """Represents a parsed code node (function, class, method, import, etc.)"""
    type: str  # 'function', 'class', 'method', 'import', 'module_level'
    name: str
    file_path: str
    start_line: int
    end_line: int
    code: str
    docstring: Optional[str] = None
    signature: Optional[str] = None


class ASTParser:
    """Parse Python code using tree-sitter to extract structural elements."""

    def __init__(self):
        """Initialize the tree-sitter parser for Python."""
        self.parser = Parser()
        # tree-sitter 0.21+ requires a name parameter
        self.parser.set_language(Language(tspython.language(), "python"))

    def parse_file(self, file_path: str) -> List[CodeNode]:
        """
        Parse a Python file and extract all code nodes.

        Args:
            file_path: Path to the Python file

        Returns:
            List of CodeNode objects representing functions, classes, methods
        """
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                source_code = f.read()
        except Exception as e:
            print(f"Error reading file {file_path}: {e}")
            return []

        # Parse the source code
        tree = self.parser.parse(bytes(source_code, "utf8"))
        root_node = tree.root_node

        # Extract code nodes
        nodes = []
        self._extract_nodes(root_node, source_code, file_path, nodes)

        return nodes

    def _extract_nodes(self, node, source_code: str, file_path: str, nodes: List[CodeNode]):
        """
        Recursively extract code nodes from the AST.

        Args:
            node: tree-sitter node
            source_code: Original source code
            file_path: Path to the file
            nodes: List to append extracted nodes to
        """
        # Extract functions
        if node.type == 'function_definition':
            code_node = self._extract_function(node, source_code, file_path)
            if code_node:
                nodes.append(code_node)

        # Extract classes
        elif node.type == 'class_definition':
            code_node = self._extract_class(node, source_code, file_path)
            if code_node:
                nodes.append(code_node)

            # Also extract methods within the class
            for child in node.children:
                if child.type == 'block':
                    for stmt in child.children:
                        if stmt.type == 'function_definition':
                            method_node = self._extract_function(stmt, source_code, file_path, is_method=True)
                            if method_node:
                                nodes.append(method_node)

        # Extract import statements (critical for import-related bugs!)
        elif node.type in ('import_statement', 'import_from_statement'):
            code_node = self._extract_import(node, source_code, file_path)
            if code_node:
                nodes.append(code_node)

        # Extract module-level code (expressions, assignments, etc.)
        elif node.type == 'expression_statement' and node.parent and node.parent.type == 'module':
            code_node = self._extract_module_level_code(node, source_code, file_path)
            if code_node:
                nodes.append(code_node)

        # Recursively process children
        for child in node.children:
            self._extract_nodes(child, source_code, file_path, nodes)

    def _extract_function(self, node, source_code: str, file_path: str, is_method: bool = False) -> Optional[CodeNode]:
        """Extract function or method details."""
        try:
            # Get function name
            name_node = node.child_by_field_name('name')
            if not name_node:
                return None
            name = source_code[name_node.start_byte:name_node.end_byte]

            # Get line numbers
            start_line = node.start_point[0] + 1
            end_line = node.end_point[0] + 1

            # Get full code
            code = source_code[node.start_byte:node.end_byte]

            # Try to extract docstring
            docstring = self._extract_docstring(node, source_code)

            # Get function signature
            params_node = node.child_by_field_name('parameters')
            params = source_code[params_node.start_byte:params_node.end_byte] if params_node else "()"
            signature = f"def {name}{params}"

            return CodeNode(
                type='method' if is_method else 'function',
                name=name,
                file_path=file_path,
                start_line=start_line,
                end_line=end_line,
                code=code,
                docstring=docstring,
                signature=signature
            )
        except Exception as e:
            print(f"Error extracting function: {e}")
            return None

    def _extract_class(self, node, source_code: str, file_path: str) -> Optional[CodeNode]:
        """Extract class details."""
        try:
            # Get class name
            name_node = node.child_by_field_name('name')
            if not name_node:
                return None
            name = source_code[name_node.start_byte:name_node.end_byte]

            # Get line numbers
            start_line = node.start_point[0] + 1
            end_line = node.end_point[0] + 1

            # Get full code
            code = source_code[node.start_byte:node.end_byte]

            # Try to extract docstring
            docstring = self._extract_docstring(node, source_code)

            # Get class signature (name + bases)
            superclasses_node = node.child_by_field_name('superclasses')
            bases = source_code[superclasses_node.start_byte:superclasses_node.end_byte] if superclasses_node else ""
            signature = f"class {name}{bases}"

            return CodeNode(
                type='class',
                name=name,
                file_path=file_path,
                start_line=start_line,
                end_line=end_line,
                code=code,
                docstring=docstring,
                signature=signature
            )
        except Exception as e:
            print(f"Error extracting class: {e}")
            return None

    def _extract_docstring(self, node, source_code: str) -> Optional[str]:
        """Extract docstring from a function or class node."""
        try:
            body = node.child_by_field_name('body')
            if not body:
                return None

            # Look for first string in the body
            for child in body.children:
                if child.type == 'expression_statement':
                    for expr_child in child.children:
                        if expr_child.type == 'string':
                            docstring = source_code[expr_child.start_byte:expr_child.end_byte]
                            # Remove quotes
                            docstring = docstring.strip('"""').strip("'''").strip('"').strip("'")
                            return docstring.strip()
            return None
        except Exception:
            return None

    def _extract_import(self, node, source_code: str, file_path: str) -> Optional[CodeNode]:
        """Extract import statement details."""
        try:
            # Get line numbers
            start_line = node.start_point[0] + 1
            end_line = node.end_point[0] + 1

            # Get full import statement
            code = source_code[node.start_byte:node.end_byte]

            # Extract a name for the import
            # For "import foo" -> name is "foo"
            # For "from foo import bar" -> name is "foo.bar"
            # For "import foo as bar" -> name is "foo (as bar)"
            name = code.strip()
            if len(name) > 50:
                name = name[:47] + "..."

            return CodeNode(
                type='import',
                name=name,
                file_path=file_path,
                start_line=start_line,
                end_line=end_line,
                code=code,
                docstring=None,
                signature=code.strip()
            )
        except Exception as e:
            print(f"Error extracting import: {e}")
            return None

    def _extract_module_level_code(self, node, source_code: str, file_path: str) -> Optional[CodeNode]:
        """Extract module-level code (expressions, assignments at module scope)."""
        try:
            # Get line numbers
            start_line = node.start_point[0] + 1
            end_line = node.end_point[0] + 1

            # Get code
            code = source_code[node.start_byte:node.end_byte]

            # Skip if it's just whitespace or comments
            if not code.strip() or code.strip().startswith('#'):
                return None

            # Create a short name from the code
            name = code.strip()
            if len(name) > 50:
                name = name[:47] + "..."

            return CodeNode(
                type='module_level',
                name=name,
                file_path=file_path,
                start_line=start_line,
                end_line=end_line,
                code=code,
                docstring=None,
                signature=None
            )
        except Exception as e:
            print(f"Error extracting module-level code: {e}")
            return None

    def parse_workspace(self, workspace_path: str) -> List[CodeNode]:
        """
        Parse all Python files in a workspace.

        Args:
            workspace_path: Path to the workspace directory

        Returns:
            List of all CodeNode objects found in the workspace
        """
        workspace = Path(workspace_path)
        skip_dirs = {'.git', 'venv', 'node_modules', 'dist', 'build', '__pycache__'}

        all_nodes = []
        for py_file in workspace.rglob('*.py'):
            # Skip directories
            if any(part in skip_dirs for part in py_file.parts):
                continue

            nodes = self.parse_file(str(py_file))
            all_nodes.extend(nodes)

        print(f"Parsed {len(all_nodes)} code nodes from workspace")
        return all_nodes
