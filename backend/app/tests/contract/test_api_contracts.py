"""
Contract Tests for ASA API Endpoints.

Tests that API inputs and outputs match expected schemas.
"""

import pytest
from fastapi.testclient import TestClient
from typing import Dict, Any

# Import main app
try:
    from app.main import app
except ImportError:
    # Fallback for local testing
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    from app.main import app


client = TestClient(app)


class TestTaskEndpointContract:
    """Contract tests for /api/v1/task endpoints."""

    def test_create_task_request_schema(self):
        """Test that create task request matches expected schema."""
        # Valid request
        valid_request = {
            "repo_url": "https://github.com/user/repo",
            "bug_description": "Button doesn't work",
            "test_command": "pytest tests/"
        }

        response = client.post("/api/v1/task", json=valid_request)

        # Should not fail on schema validation
        assert response.status_code in [200, 201, 202], (
            f"Unexpected status: {response.status_code}. "
            f"Response: {response.text}"
        )

    def test_create_task_response_schema(self):
        """Test that create task response matches expected schema."""
        request_data = {
            "repo_url": "https://github.com/user/repo",
            "bug_description": "Test bug",
            "test_command": "pytest"
        }

        response = client.post("/api/v1/task", json=request_data)

        if response.status_code in [200, 201, 202]:
            data = response.json()

            # Check required fields in response
            assert "task_id" in data, "Response missing task_id"
            assert isinstance(data["task_id"], str), "task_id must be string"

            # Optional: Check for standard fields
            if "status" in data:
                assert isinstance(data["status"], str)

    def test_create_task_missing_required_fields(self):
        """Test that missing required fields are rejected."""
        # Missing bug_description
        invalid_request = {
            "repo_url": "https://github.com/user/repo",
            "test_command": "pytest"
        }

        response = client.post("/api/v1/task", json=invalid_request)

        # Should return validation error
        assert response.status_code == 422, (
            f"Should reject invalid input. Got: {response.status_code}"
        )

    def test_get_task_response_schema(self):
        """Test that get task response matches schema."""
        # First create a task
        create_response = client.post("/api/v1/task", json={
            "repo_url": "https://github.com/user/repo",
            "bug_description": "Test",
            "test_command": "pytest"
        })

        if create_response.status_code not in [200, 201, 202]:
            pytest.skip("Cannot test get without successful create")

        task_id = create_response.json()["task_id"]

        # Get the task
        get_response = client.get(f"/api/v1/task/{task_id}")

        assert get_response.status_code == 200, (
            f"GET failed: {get_response.status_code}"
        )

        data = get_response.json()

        # Check response schema
        required_fields = ["id", "status", "bug_description"]
        for field in required_fields:
            assert field in data, f"Response missing required field: {field}"

        # Validate types
        assert isinstance(data["id"], str)
        assert isinstance(data["status"], str)
        assert isinstance(data["bug_description"], str)


class TestUsageEndpointContract:
    """Contract tests for /api/v1/usage endpoints."""

    def test_get_usage_response_schema(self):
        """Test that usage endpoint returns valid schema."""
        # This might require authentication, handle gracefully
        response = client.get("/api/v1/usage")

        if response.status_code == 200:
            data = response.json()

            # Check for expected structure
            if isinstance(data, dict):
                # Should have usage metrics
                possible_fields = ["total_tokens", "total_cost", "task_count"]
                has_usage_field = any(field in data for field in possible_fields)
                assert has_usage_field, "Usage response missing metrics"
        elif response.status_code == 401:
            # Authentication required, that's fine
            pytest.skip("Authentication required for usage endpoint")
        else:
            pytest.fail(f"Unexpected status: {response.status_code}")


class TestHealthEndpointContract:
    """Contract tests for health/status endpoints."""

    def test_health_check_schema(self):
        """Test health check returns expected schema."""
        # Try common health check paths
        possible_paths = ["/health", "/api/health", "/"]

        found_health = False

        for path in possible_paths:
            response = client.get(path)

            if response.status_code == 200:
                found_health = True
                # Health check should return some status
                data = response.json()

                # Check for status indicator
                if isinstance(data, dict):
                    assert "status" in data or "healthy" in data or "message" in data
                break

        # It's okay if no health endpoint exists
        if not found_health:
            pytest.skip("No health check endpoint found")


def test_error_response_schema():
    """Test that error responses follow a consistent schema."""
    # Try to get non-existent task
    response = client.get("/api/v1/task/nonexistent-id-12345")

    # Should return 404 or similar
    assert response.status_code >= 400, "Should return error for invalid ID"

    # Error response should have consistent structure
    data = response.json()

    # Common error fields
    possible_error_fields = ["detail", "error", "message"]
    has_error_field = any(field in data for field in possible_error_fields)

    assert has_error_field, (
        f"Error response missing standard field. Got: {data.keys()}"
    )


def test_api_returns_json():
    """Test that API endpoints return JSON content type."""
    # Test various endpoints
    endpoints = [
        ("/api/v1/task", "post", {"repo_url": "https://github.com/user/repo", "bug_description": "test", "test_command": "pytest"}),
        ("/api/v1/usage", "get", None),
    ]

    for path, method, body in endpoints:
        if method == "post":
            response = client.post(path, json=body)
        else:
            response = client.get(path)

        # Check content type
        content_type = response.headers.get("content-type", "")

        # Should be JSON (might include charset)
        assert "application/json" in content_type.lower(), (
            f"{path} should return JSON. Got: {content_type}"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
