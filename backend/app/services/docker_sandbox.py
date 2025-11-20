"""
Docker Sandbox - Isolated test execution environment.

Provides disposable Docker containers for running Playwright tests safely.
"""

import subprocess
import json
import tempfile
import shutil
from pathlib import Path
from typing import Optional, Dict, Any, Tuple


class DockerSandbox:
    """Manage Docker containers for isolated test execution."""

    def __init__(self, image: str = "mcr.microsoft.com/playwright:v1.40.0-jammy"):
        """
        Initialize Docker sandbox.

        Args:
            image: Docker image to use (default: official Playwright image)
        """
        self.image = image
        self._ensure_docker_available()

    def _ensure_docker_available(self):
        """Check if Docker is available."""
        try:
            result = subprocess.run(
                ['docker', '--version'],
                capture_output=True,
                text=True,
                check=True
            )
            print(f"Docker available: {result.stdout.strip()}")
        except (subprocess.CalledProcessError, FileNotFoundError):
            raise Exception("Docker is not available. Please install Docker and ensure it's running.")

    def pull_image(self):
        """Pull the Docker image if not already present."""
        print(f"Pulling Docker image: {self.image}")
        try:
            subprocess.run(
                ['docker', 'pull', self.image],
                check=True,
                capture_output=True,
                text=True
            )
            print("Image pulled successfully")
        except subprocess.CalledProcessError as e:
            print(f"Warning: Could not pull image: {e.stderr}")
            # Continue anyway - image might already exist

    def run_test(
        self,
        test_file_path: str,
        workspace_path: str,
        timeout: int = 60
    ) -> Tuple[int, str, str]:
        """
        Run a Playwright test in an isolated Docker container.

        Args:
            test_file_path: Path to the test file (relative to workspace)
            workspace_path: Path to the workspace directory
            timeout: Timeout in seconds

        Returns:
            Tuple of (exit_code, stdout, stderr)
        """
        workspace = Path(workspace_path).resolve()
        test_file = Path(test_file_path)

        # Ensure workspace exists
        if not workspace.exists():
            raise ValueError(f"Workspace does not exist: {workspace}")

        # Ensure test file exists
        full_test_path = workspace / test_file if not test_file.is_absolute() else test_file
        if not full_test_path.exists():
            raise ValueError(f"Test file does not exist: {full_test_path}")

        # Get relative path of test file from workspace
        try:
            rel_test_path = full_test_path.relative_to(workspace)
        except ValueError:
            # Test file is not in workspace, copy it
            rel_test_path = Path("generated_test.spec.js")
            temp_test = workspace / rel_test_path
            shutil.copy(full_test_path, temp_test)

        print(f"Running test in Docker: {rel_test_path}")

        # Build docker run command
        # Mount workspace as /workspace in container
        # Run npx playwright test
        cmd = [
            'docker', 'run',
            '--rm',  # Remove container after execution
            '--network', 'none',  # Disable network access for security
            '-v', f'{workspace}:/workspace',  # Mount workspace
            '-w', '/workspace',  # Set working directory
            self.image,
            'npx', 'playwright', 'test', str(rel_test_path),
            '--reporter=json'  # JSON output for parsing
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout
            )

            return result.returncode, result.stdout, result.stderr

        except subprocess.TimeoutExpired:
            print(f"Test execution timed out after {timeout} seconds")
            return -1, "", f"Test execution timed out after {timeout} seconds"
        except Exception as e:
            print(f"Error running test: {e}")
            return -1, "", str(e)

    def run_command(
        self,
        command: str,
        workspace_path: str,
        timeout: int = 30,
        allow_network: bool = False
    ) -> Tuple[int, str, str]:
        """
        Run an arbitrary command in a Docker container.

        Args:
            command: Command to run
            workspace_path: Path to mount as workspace
            timeout: Timeout in seconds
            allow_network: Allow network access (only for trusted setup operations)

        Returns:
            Tuple of (exit_code, stdout, stderr)
        """
        workspace = Path(workspace_path).resolve()

        # Use network isolation by default for security
        network_mode = 'host' if allow_network else 'none'

        cmd = [
            'docker', 'run',
            '--rm',
            '--network', network_mode,  # Disable network by default for security
            '-v', f'{workspace}:/workspace',
            '-w', '/workspace',
            self.image,
            'sh', '-c', command
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            return result.returncode, result.stdout, result.stderr

        except subprocess.TimeoutExpired:
            return -1, "", f"Command timed out after {timeout} seconds"
        except Exception as e:
            return -1, "", str(e)

    def setup_playwright_project(self, workspace_path: str) -> bool:
        """
        Setup a basic Playwright project in the workspace.

        Args:
            workspace_path: Path to workspace

        Returns:
            True if successful, False otherwise
        """
        workspace = Path(workspace_path)

        # Create package.json if it doesn't exist
        package_json_path = workspace / "package.json"
        if not package_json_path.exists():
            package_json = {
                "name": "asa-test-workspace",
                "version": "1.0.0",
                "devDependencies": {
                    "@playwright/test": "^1.40.0"
                }
            }
            with open(package_json_path, 'w') as f:
                json.dump(package_json, f, indent=2)
            print("Created package.json")

        # Create playwright.config.js if it doesn't exist
        config_path = workspace / "playwright.config.js"
        if not config_path.exists():
            config = """
module.exports = {
  testDir: '.',
  timeout: 30000,
  use: {
    headless: true,
    viewport: { width: 1280, height: 720 },
    actionTimeout: 10000,
  },
  reporter: [['json', { outputFile: 'test-results.json' }]],
};
"""
            with open(config_path, 'w') as f:
                f.write(config)
            print("Created playwright.config.js")

        # Install dependencies using Docker
        # Note: This requires network access, so we allow it for this trusted setup operation
        print("Installing Playwright dependencies...")
        exit_code, stdout, stderr = self.run_command(
            "npm install",
            str(workspace),
            timeout=120,
            allow_network=True  # Network required for npm install
        )

        if exit_code != 0:
            print(f"Warning: npm install failed: {stderr}")
            return False

        print("Playwright setup complete")
        return True
