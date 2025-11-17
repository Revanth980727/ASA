"""
Container Manager - Lifecycle management for isolated sandbox containers.

Features:
- Container creation and destruction
- Resource limits and security constraints
- Output streaming
- Automatic cleanup
"""

import os
import time
import docker
from docker.errors import DockerException, APIError, NotFound
from typing import Optional, Dict, Any, List, Tuple
from pathlib import Path
import threading
import queue


class ContainerManager:
    """Manage isolated sandbox containers for task execution."""

    def __init__(
        self,
        image: str = "asa-sandbox:latest",
        auto_cleanup: bool = True
    ):
        """
        Initialize Container Manager.

        Args:
            image: Docker image to use
            auto_cleanup: Automatically remove containers after execution
        """
        self.image = image
        self.auto_cleanup = auto_cleanup

        try:
            self.client = docker.from_env()
            self.client.ping()
        except DockerException as e:
            raise RuntimeError(f"Docker is not available: {e}")

        # Track active containers for cleanup
        self.active_containers: Dict[str, Any] = {}
        self._cleanup_lock = threading.Lock()

    def create_container(
        self,
        task_id: str,
        workspace_path: str,
        command: Optional[List[str]] = None,
        mem_limit: str = "512m",
        cpu_quota: int = 50000,
        timeout: int = 300,
        network_mode: str = "none",
        enable_network: bool = False,
        environment: Optional[Dict[str, str]] = None
    ) -> str:
        """
        Create a new sandbox container.

        Args:
            task_id: Unique task identifier
            workspace_path: Path to workspace directory
            command: Command to run (None = default shell)
            mem_limit: Memory limit (e.g., "512m", "1g")
            cpu_quota: CPU quota (50000 = 50% of one CPU)
            timeout: Execution timeout in seconds
            network_mode: Network mode ("none", "bridge", "host")
            enable_network: Override network_mode to "bridge" if True
            environment: Additional environment variables

        Returns:
            Container ID
        """
        workspace = Path(workspace_path).resolve()
        if not workspace.exists():
            raise ValueError(f"Workspace does not exist: {workspace}")

        # Network configuration
        if enable_network:
            network_mode = "bridge"

        # Environment variables
        env = {
            "TASK_ID": task_id,
            "ASA_TIMEOUT": str(timeout),
            **(environment or {})
        }

        # Security options
        security_opt = [
            "no-new-privileges:true",
            "seccomp=default"
        ]

        # Container configuration
        container_config = {
            "image": self.image,
            "name": f"asa-sandbox-{task_id}",
            "command": command,
            "detach": True,
            "remove": self.auto_cleanup,
            "mem_limit": mem_limit,
            "memswap_limit": mem_limit,  # Prevent swap usage
            "cpu_quota": cpu_quota,
            "pids_limit": 100,
            "network_mode": network_mode,
            "security_opt": security_opt,
            "read_only": True,  # Read-only root filesystem
            "user": "1000:1000",  # Non-root user
            "volumes": {
                str(workspace): {
                    "bind": "/workspace",
                    "mode": "rw"
                },
                "/tmp": {  # Writable temp directory
                    "bind": "/tmp",
                    "mode": "rw"
                }
            },
            "environment": env,
            "labels": {
                "com.asa.type": "sandbox",
                "com.asa.task_id": task_id,
                "com.asa.auto_cleanup": str(self.auto_cleanup)
            },
            "cap_drop": ["ALL"],  # Drop all capabilities
            "cap_add": ["CHOWN", "DAC_OVERRIDE", "FOWNER", "SETGID", "SETUID"],
            "privileged": False
        }

        try:
            container = self.client.containers.create(**container_config)
            container_id = container.id

            # Track container
            with self._cleanup_lock:
                self.active_containers[container_id] = {
                    "task_id": task_id,
                    "container": container,
                    "created_at": time.time()
                }

            print(f"✓ Created container {container_id[:12]} for task {task_id}")
            return container_id

        except APIError as e:
            raise RuntimeError(f"Failed to create container: {e}")

    def start_container(self, container_id: str) -> None:
        """
        Start a container.

        Args:
            container_id: Container ID
        """
        try:
            container = self.client.containers.get(container_id)
            container.start()
            print(f"✓ Started container {container_id[:12]}")
        except NotFound:
            raise ValueError(f"Container not found: {container_id}")
        except APIError as e:
            raise RuntimeError(f"Failed to start container: {e}")

    def run_command(
        self,
        task_id: str,
        workspace_path: str,
        command: List[str],
        timeout: int = 300,
        stream_output: bool = False
    ) -> Tuple[int, str, str]:
        """
        Run a command in a new container.

        Args:
            task_id: Task identifier
            workspace_path: Workspace path
            command: Command to run
            timeout: Timeout in seconds
            stream_output: Stream output to console

        Returns:
            Tuple of (exit_code, stdout, stderr)
        """
        # Create container
        container_id = self.create_container(
            task_id=task_id,
            workspace_path=workspace_path,
            command=command,
            timeout=timeout
        )

        try:
            # Start container
            container = self.client.containers.get(container_id)
            container.start()

            # Wait for completion with timeout
            try:
                result = container.wait(timeout=timeout)
                exit_code = result['StatusCode']
            except Exception as e:
                # Timeout or other error
                print(f"Container timed out or errored: {e}")
                self.stop_container(container_id, timeout=10)
                exit_code = -1

            # Get logs
            logs = container.logs(stdout=True, stderr=True, timestamps=False)
            output = logs.decode('utf-8', errors='ignore')

            # Split stdout and stderr (if possible)
            # Note: Docker combines them, so we'll return output for both
            stdout = output
            stderr = ""

            return exit_code, stdout, stderr

        finally:
            # Cleanup
            if self.auto_cleanup:
                self.remove_container(container_id, force=True)

    def stop_container(self, container_id: str, timeout: int = 10) -> None:
        """
        Stop a running container.

        Args:
            container_id: Container ID
            timeout: Timeout before force kill
        """
        try:
            container = self.client.containers.get(container_id)
            container.stop(timeout=timeout)
            print(f"✓ Stopped container {container_id[:12]}")
        except NotFound:
            pass  # Already removed
        except APIError as e:
            print(f"Warning: Failed to stop container: {e}")

    def remove_container(self, container_id: str, force: bool = False) -> None:
        """
        Remove a container.

        Args:
            container_id: Container ID
            force: Force removal even if running
        """
        try:
            container = self.client.containers.get(container_id)
            container.remove(force=force)

            # Remove from tracking
            with self._cleanup_lock:
                self.active_containers.pop(container_id, None)

            print(f"✓ Removed container {container_id[:12]}")
        except NotFound:
            pass  # Already removed
        except APIError as e:
            print(f"Warning: Failed to remove container: {e}")

    def get_container_logs(
        self,
        container_id: str,
        tail: int = 100,
        follow: bool = False
    ) -> str:
        """
        Get container logs.

        Args:
            container_id: Container ID
            tail: Number of lines to return (None = all)
            follow: Stream logs in real-time

        Returns:
            Log output
        """
        try:
            container = self.client.containers.get(container_id)
            logs = container.logs(
                stdout=True,
                stderr=True,
                tail=tail if tail else "all",
                follow=follow,
                timestamps=True
            )

            if follow:
                # Return generator for streaming
                return logs
            else:
                return logs.decode('utf-8', errors='ignore')

        except NotFound:
            return f"Container not found: {container_id}"
        except APIError as e:
            return f"Error getting logs: {e}"

    def cleanup_old_containers(self, max_age_seconds: int = 3600) -> int:
        """
        Remove containers older than max_age_seconds.

        Args:
            max_age_seconds: Maximum age in seconds

        Returns:
            Number of containers removed
        """
        removed = 0
        current_time = time.time()

        with self._cleanup_lock:
            to_remove = []
            for container_id, info in self.active_containers.items():
                age = current_time - info['created_at']
                if age > max_age_seconds:
                    to_remove.append(container_id)

            for container_id in to_remove:
                try:
                    self.remove_container(container_id, force=True)
                    removed += 1
                except Exception as e:
                    print(f"Failed to remove old container {container_id}: {e}")

        # Also cleanup any orphaned containers with ASA labels
        try:
            orphaned = self.client.containers.list(
                all=True,
                filters={"label": "com.asa.type=sandbox"}
            )

            for container in orphaned:
                try:
                    created_at = container.attrs['Created']
                    # Parse created_at and check age
                    # For simplicity, remove all labeled containers
                    container.remove(force=True)
                    removed += 1
                except Exception:
                    pass

        except Exception as e:
            print(f"Failed to cleanup orphaned containers: {e}")

        if removed > 0:
            print(f"✓ Cleaned up {removed} old containers")

        return removed

    def cleanup_all(self) -> int:
        """
        Remove all ASA sandbox containers.

        Returns:
            Number of containers removed
        """
        removed = 0

        # Stop and remove tracked containers
        with self._cleanup_lock:
            container_ids = list(self.active_containers.keys())

        for container_id in container_ids:
            try:
                self.remove_container(container_id, force=True)
                removed += 1
            except Exception as e:
                print(f"Failed to remove container {container_id}: {e}")

        # Cleanup orphaned containers
        removed += self.cleanup_old_containers(max_age_seconds=0)

        return removed

    def get_container_stats(self, container_id: str) -> Dict[str, Any]:
        """
        Get container resource usage statistics.

        Args:
            container_id: Container ID

        Returns:
            Statistics dictionary
        """
        try:
            container = self.client.containers.get(container_id)
            stats = container.stats(stream=False)

            # Parse useful metrics
            cpu_stats = stats.get('cpu_stats', {})
            mem_stats = stats.get('memory_stats', {})

            return {
                "cpu_usage": cpu_stats.get('cpu_usage', {}).get('total_usage', 0),
                "memory_usage": mem_stats.get('usage', 0),
                "memory_limit": mem_stats.get('limit', 0),
                "network_rx": stats.get('networks', {}).get('eth0', {}).get('rx_bytes', 0),
                "network_tx": stats.get('networks', {}).get('eth0', {}).get('tx_bytes', 0),
            }
        except NotFound:
            return {}
        except APIError as e:
            print(f"Failed to get stats: {e}")
            return {}

    def list_active_containers(self) -> List[Dict[str, Any]]:
        """
        List all active ASA containers.

        Returns:
            List of container information
        """
        with self._cleanup_lock:
            return [
                {
                    "container_id": cid[:12],
                    "task_id": info['task_id'],
                    "age_seconds": time.time() - info['created_at']
                }
                for cid, info in self.active_containers.items()
            ]

    def ensure_image_available(self) -> bool:
        """
        Ensure sandbox image is available (pull if needed).

        Returns:
            True if image is available
        """
        try:
            self.client.images.get(self.image)
            print(f"✓ Image {self.image} is available")
            return True
        except NotFound:
            print(f"Image {self.image} not found, building...")
            # TODO: Trigger build or pull
            return False
        except APIError as e:
            print(f"Failed to check image: {e}")
            return False
