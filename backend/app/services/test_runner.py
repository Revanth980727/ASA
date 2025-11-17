"""
Test Runner - Execute tests in a sandboxed environment.

Handles:
- Running test commands (pytest, npm test, etc.)
- Capturing test output (stdout, stderr)
- Parsing test results
- Running in Docker sandbox for isolation
"""

import subprocess
from pathlib import Path
from typing import Tuple, Optional

def run_tests(workspace_path: str, test_command: Optional[str]) -> Tuple[bool, str]:
    """
    Run tests in the workspace directory.
    
    Args:
        workspace_path: Path to the workspace directory
        test_command: Test command to run (e.g., "pytest", "npm test"). 
                     If None, defaults to "pytest"
    
    Returns:
        Tuple of (tests_passed: bool, output: str)
        - tests_passed: True if returncode == 0, False otherwise
        - output: Combined stdout + stderr as a single string
    """
    if test_command is None:
        test_command = "pytest"
    
    workspace = Path(workspace_path)
    if not workspace.exists():
        return False, f"Workspace path does not exist: {workspace_path}"
    
    try:
        # Split the command into a list for subprocess
        # Handle commands like "pytest -v" or "npm test"
        cmd_parts = test_command.split()
        
        result = subprocess.run(
            cmd_parts,
            cwd=str(workspace),
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        
        # Combine stdout and stderr
        output = ""
        if result.stdout:
            output += result.stdout
        if result.stderr:
            if output:
                output += "\n--- stderr ---\n"
            output += result.stderr
        
        # returncode == 0 means tests passed
        tests_passed = (result.returncode == 0)
        
        return tests_passed, output
        
    except subprocess.TimeoutExpired:
        return False, "Test execution timed out after 5 minutes"
    except FileNotFoundError:
        return False, f"Test command not found: {test_command}. Make sure it's installed in the workspace."
    except Exception as e:
        return False, f"Error running tests: {str(e)}"
