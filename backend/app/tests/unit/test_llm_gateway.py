"""
Unit Tests for LLM Gateway.

Tests LLM gateway functionality including budget enforcement,
error handling, retry logic, and prompt integration.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from openai import RateLimitError, APITimeoutError

from app.services.llm_gateway import LLMGateway
from app.core.limits import LLMPurpose
from app.core.errors import ASAError, ErrorType


class TestLLMGatewayBudgets:
    """Test budget enforcement in LLM Gateway."""

    @patch('app.services.llm_gateway.SessionLocal')
    @patch('app.services.llm_gateway.OpenAI')
    def test_budget_exceeded_tokens(self, mock_openai, mock_db):
        """Test that token budget is enforced."""
        # Mock database session
        mock_session = Mock()
        mock_db.return_value = mock_session

        # Mock usage query to return high token usage
        mock_result = Mock()
        mock_result.total_tokens = 200000  # Exceeds budget
        mock_result.total_cost = 0.0
        mock_session.query.return_value.filter.return_value.first.return_value = mock_result

        gateway = LLMGateway(task_id="test-task", db=mock_session)

        # Should raise budget exceeded error
        with pytest.raises(ASAError) as exc_info:
            gateway.chat_completion(
                purpose=LLMPurpose.FIX_GENERATION,
                messages=[{"role": "user", "content": "test"}]
            )

        assert exc_info.value.error_type == ErrorType.TOKEN_BUDGET_EXCEEDED

    @patch('app.services.llm_gateway.SessionLocal')
    @patch('app.services.llm_gateway.OpenAI')
    def test_budget_exceeded_cost(self, mock_openai, mock_db):
        """Test that cost budget is enforced."""
        # Mock database session
        mock_session = Mock()
        mock_db.return_value = mock_session

        # Mock usage query to return high cost
        mock_result = Mock()
        mock_result.total_tokens = 0
        mock_result.total_cost = 10.0  # Exceeds budget
        mock_session.query.return_value.filter.return_value.first.return_value = mock_result

        gateway = LLMGateway(task_id="test-task", db=mock_session)

        # Should raise budget exceeded error
        with pytest.raises(ASAError) as exc_info:
            gateway.chat_completion(
                purpose=LLMPurpose.FIX_GENERATION,
                messages=[{"role": "user", "content": "test"}]
            )

        assert exc_info.value.error_type == ErrorType.COST_BUDGET_EXCEEDED


class TestLLMGatewayErrorHandling:
    """Test error handling and classification."""

    @patch('app.services.llm_gateway.SessionLocal')
    @patch('app.services.llm_gateway.OpenAI')
    def test_rate_limit_error_classification(self, mock_openai, mock_db):
        """Test that rate limit errors are properly classified."""
        mock_session = Mock()
        mock_db.return_value = mock_session

        # Mock zero usage
        mock_result = Mock()
        mock_result.total_tokens = 0
        mock_result.total_cost = 0.0
        mock_session.query.return_value.filter.return_value.first.return_value = mock_result

        # Mock OpenAI to raise rate limit error
        mock_client = Mock()
        mock_openai.return_value = mock_client
        mock_client.chat.completions.create.side_effect = RateLimitError(
            "Rate limit exceeded",
            response=Mock(status_code=429),
            body={}
        )

        gateway = LLMGateway(task_id="test-task", db=mock_session)
        gateway.client = mock_client

        # Should raise ASAError with LLM_RATE_LIMIT type
        with pytest.raises(ASAError) as exc_info:
            gateway.chat_completion(
                purpose=LLMPurpose.FIX_GENERATION,
                messages=[{"role": "user", "content": "test"}]
            )

        assert exc_info.value.error_type == ErrorType.LLM_RATE_LIMIT

    @patch('app.services.llm_gateway.SessionLocal')
    @patch('app.services.llm_gateway.OpenAI')
    def test_timeout_error_classification(self, mock_openai, mock_db):
        """Test that timeout errors are properly classified."""
        mock_session = Mock()
        mock_db.return_value = mock_session

        mock_result = Mock()
        mock_result.total_tokens = 0
        mock_result.total_cost = 0.0
        mock_session.query.return_value.filter.return_value.first.return_value = mock_result

        # Mock timeout error
        mock_client = Mock()
        mock_openai.return_value = mock_client
        mock_client.chat.completions.create.side_effect = APITimeoutError(
            request=Mock()
        )

        gateway = LLMGateway(task_id="test-task", db=mock_session)
        gateway.client = mock_client

        with pytest.raises(ASAError) as exc_info:
            gateway.chat_completion(
                purpose=LLMPurpose.FIX_GENERATION,
                messages=[{"role": "user", "content": "test"}]
            )

        assert exc_info.value.error_type == ErrorType.LLM_TIMEOUT


class TestLLMGatewayUsageTracking:
    """Test usage tracking and logging."""

    @patch('app.services.llm_gateway.SessionLocal')
    @patch('app.services.llm_gateway.OpenAI')
    def test_usage_logged_on_success(self, mock_openai, mock_db):
        """Test that successful calls log usage."""
        mock_session = Mock()
        mock_db.return_value = mock_session

        mock_result = Mock()
        mock_result.total_tokens = 0
        mock_result.total_cost = 0.0
        mock_session.query.return_value.filter.return_value.first.return_value = mock_result

        # Mock successful response
        mock_response = Mock()
        mock_response.usage.prompt_tokens = 100
        mock_response.usage.completion_tokens = 50
        mock_response.usage.total_tokens = 150
        mock_response.choices = [Mock(message=Mock(content="test response"))]

        mock_client = Mock()
        mock_openai.return_value = mock_client
        mock_client.chat.completions.create.return_value = mock_response

        gateway = LLMGateway(task_id="test-task", db=mock_session)
        gateway.client = mock_client

        response = gateway.chat_completion(
            purpose=LLMPurpose.FIX_GENERATION,
            messages=[{"role": "user", "content": "test"}]
        )

        # Verify usage was logged
        assert mock_session.add.called
        assert mock_session.commit.called
        assert response == "test response"

    @patch('app.services.llm_gateway.SessionLocal')
    def test_get_usage_summary(self, mock_db):
        """Test getting usage summary."""
        mock_session = Mock()
        mock_db.return_value = mock_session

        gateway = LLMGateway(task_id="test-task", db=mock_session)
        gateway._total_tokens = 1000
        gateway._total_cost = 0.05

        summary = gateway.get_usage_summary()

        assert summary["task_id"] == "test-task"
        assert summary["total_tokens"] == 1000
        assert summary["total_cost_usd"] == 0.05
        assert "budgets" in summary


class TestLLMGatewayPromptIntegration:
    """Test integration with versioned prompts."""

    @patch('app.services.llm_gateway.SessionLocal')
    @patch('app.services.llm_gateway.OpenAI')
    @patch('app.services.llm_gateway.load_prompt')
    def test_chat_completion_with_prompt(self, mock_load_prompt, mock_openai, mock_db):
        """Test using versioned prompts."""
        mock_session = Mock()
        mock_db.return_value = mock_session

        mock_result = Mock()
        mock_result.total_tokens = 0
        mock_result.total_cost = 0.0
        mock_session.query.return_value.filter.return_value.first.return_value = mock_result

        # Mock prompt
        mock_prompt = Mock()
        mock_prompt.purpose = "GUARDIAN"
        mock_prompt.schema_version = "v1"
        mock_prompt.checksum = "test-checksum"
        mock_prompt.model_config = {"temperature": 0.0, "max_tokens": 1000}
        mock_prompt.get_messages.return_value = [
            {"role": "system", "content": "You are a guardian"},
            {"role": "user", "content": "Test"}
        ]
        mock_prompt.to_metadata.return_value = {"schema_version": "v1"}
        mock_prompt.validate_response.return_value = True
        mock_load_prompt.return_value = mock_prompt

        # Mock LLM response
        mock_response = Mock()
        mock_response.usage.prompt_tokens = 100
        mock_response.usage.completion_tokens = 50
        mock_response.usage.total_tokens = 150
        mock_response.choices = [Mock(message=Mock(
            content='{"safe": true, "risk_level": "low", "issues": [], "recommendation": "approve", "rationale": "OK"}'
        ))]

        mock_client = Mock()
        mock_openai.return_value = mock_client
        mock_client.chat.completions.create.return_value = mock_response

        gateway = LLMGateway(task_id="test-task", db=mock_session)
        gateway.client = mock_client

        result = gateway.chat_completion_with_prompt(
            purpose=LLMPurpose.GUARDIAN,
            version="v1",
            bug_description="Test bug",
            proposed_fix="Test fix",
            code_context="Test context"
        )

        assert result["safe"] is True
        assert result["risk_level"] == "low"
        mock_prompt.validate_response.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
