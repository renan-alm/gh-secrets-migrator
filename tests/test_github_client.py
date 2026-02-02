"""Tests for GitHub client module."""
from unittest.mock import Mock, patch
import pytest
from github import UnknownObjectException
from src.clients.github import GitHubClient
from src.utils.logger import Logger


class TestGitHubClientEnvironments:
    """Test cases for GitHubClient environment operations."""

    @pytest.fixture
    def mock_logger(self):
        """Create a mock logger."""
        logger = Mock(spec=Logger)
        logger.debug = Mock()
        logger.error = Mock()
        return logger

    @pytest.fixture
    def github_client(self, mock_logger):
        """Create a GitHubClient with mocked Github client."""
        with patch('src.clients.github.Github'):
            client = GitHubClient(pat="test-token", logger=mock_logger)
            client.client = Mock()
            return client

    def test_create_environment_when_not_exists(self, github_client, mock_logger):
        """Test creating an environment that doesn't exist."""
        # Setup mocks
        mock_repo = Mock()
        mock_repo.get_environment.side_effect = UnknownObjectException(
            404, "Not Found", None
        )
        mock_repo.create_environment = Mock()
        github_client.client.get_repo.return_value = mock_repo

        # Execute
        github_client.create_environment("test-org", "test-repo", "production")

        # Verify
        github_client.client.get_repo.assert_called_once_with("test-org/test-repo")
        mock_repo.get_environment.assert_called_once_with("production")
        mock_repo.create_environment.assert_called_once_with("production")
        mock_logger.debug.assert_any_call(
            "Created environment 'production' in test-org/test-repo"
        )

    def test_create_environment_when_already_exists(self, github_client, mock_logger):
        """Test creating an environment that already exists - should skip creation."""
        # Setup mocks
        mock_repo = Mock()
        mock_env = Mock()  # Represents an existing environment
        mock_repo.get_environment.return_value = mock_env
        mock_repo.create_environment = Mock()
        github_client.client.get_repo.return_value = mock_repo

        # Execute
        github_client.create_environment("test-org", "test-repo", "staging")

        # Verify
        github_client.client.get_repo.assert_called_once_with("test-org/test-repo")
        mock_repo.get_environment.assert_called_once_with("staging")
        # create_environment should NOT be called since environment exists
        mock_repo.create_environment.assert_not_called()
        mock_logger.debug.assert_any_call(
            "Environment 'staging' already exists in test-org/test-repo, skipping creation"
        )

    def test_create_environment_handles_creation_error(self, github_client, mock_logger):
        """Test handling of errors during environment creation."""
        # Setup mocks
        mock_repo = Mock()
        mock_repo.get_environment.side_effect = UnknownObjectException(
            404, "Not Found", None
        )
        mock_repo.create_environment.side_effect = Exception("Permission denied")
        github_client.client.get_repo.return_value = mock_repo

        # Execute and verify exception is raised
        with pytest.raises(RuntimeError, match="Failed to create environment 'dev'"):
            github_client.create_environment("test-org", "test-repo", "dev")

        # Verify error was logged
        mock_logger.error.assert_called()

    def test_create_environment_handles_repo_not_found(self, github_client, mock_logger):
        """Test handling when repository is not found."""
        # Setup mocks
        github_client.client.get_repo.side_effect = Exception("404 Not Found")

        # Execute and verify exception is raised
        with pytest.raises(RuntimeError, match="Failed to create environment"):
            github_client.create_environment("test-org", "test-repo", "production")

        # Verify error was logged
        mock_logger.error.assert_called()

    def test_create_environment_with_special_characters(self, github_client, mock_logger):
        """Test creating environment with special characters in name."""
        # Setup mocks
        mock_repo = Mock()
        mock_repo.get_environment.side_effect = UnknownObjectException(
            404, "Not Found", None
        )
        mock_repo.create_environment = Mock()
        github_client.client.get_repo.return_value = mock_repo

        env_name = "prod-env_123"

        # Execute
        github_client.create_environment("org", "repo", env_name)

        # Verify environment name is used as-is
        mock_repo.get_environment.assert_called_once_with(env_name)
        mock_repo.create_environment.assert_called_once_with(env_name)


class TestRateLimitHandling:
    """Test cases for rate limit handling in GitHubClient."""

    @pytest.fixture
    def mock_logger(self):
        """Create a mock logger."""
        logger = Mock(spec=Logger)
        logger.debug = Mock()
        logger.error = Mock()
        logger.warn = Mock()
        return logger

    @pytest.fixture
    def github_client(self, mock_logger):
        """Create a GitHubClient with mocked Github client."""
        with patch('src.clients.github.Github'):
            client = GitHubClient(pat="test-token", logger=mock_logger)
            client.client = Mock()
            return client

    def test_get_rate_limit_info_returns_correct_values(self, github_client):
        """Test that get_rate_limit_info returns correct values with new PyGithub 2.7.0+ API."""
        from datetime import datetime, timezone
        import time

        # Mock the new PyGithub 2.7.0+ API structure: resources.core
        reset_time = datetime.now(timezone.utc).timestamp() + 3600  # 1 hour from now
        reset_datetime = datetime.fromtimestamp(reset_time, tz=timezone.utc)
        
        mock_core = Mock()
        mock_core.remaining = 4500
        mock_core.limit = 5000
        mock_core.reset = reset_datetime
        
        mock_resources = Mock()
        mock_resources.core = mock_core
        
        mock_rate_limit = Mock()
        mock_rate_limit.resources = mock_resources
        
        github_client.client.get_rate_limit.return_value = mock_rate_limit

        # Execute
        result = github_client.get_rate_limit_info()

        # Verify
        assert result['remaining'] == 4500
        assert result['limit'] == 5000
        assert result['reset_time'] > 0
        assert result['reset_in_seconds'] >= 0

    def test_get_rate_limit_info_handles_exception_gracefully(self, github_client, mock_logger):
        """Test that get_rate_limit_info returns fallback values when API fails."""
        # Simulate the exact error from PyGithub API change
        github_client.client.get_rate_limit.side_effect = AttributeError(
            "'RateLimitOverview' object has no attribute 'core'"
        )

        # Execute
        result = github_client.get_rate_limit_info()

        # Verify fallback values are returned
        assert result['remaining'] == -1
        assert result['limit'] == -1
        assert result['reset_time'] == -1
        assert result['reset_in_seconds'] == -1
        
        # Verify debug log was called
        mock_logger.debug.assert_called()

    def test_get_rate_limit_info_handles_network_error(self, github_client, mock_logger):
        """Test that get_rate_limit_info handles network errors gracefully."""
        github_client.client.get_rate_limit.side_effect = ConnectionError("Network unavailable")

        # Execute
        result = github_client.get_rate_limit_info()

        # Verify fallback values
        assert result['remaining'] == -1
        assert result['limit'] == -1
        assert result['reset_time'] == -1
        assert result['reset_in_seconds'] == -1

    def test_log_rate_limit_continues_on_failure(self, github_client, mock_logger):
        """Test that _log_rate_limit does not raise exceptions when rate limit fails."""
        github_client.client.get_rate_limit.side_effect = Exception("API Error")

        # Execute - should not raise
        github_client._log_rate_limit("test_operation")

        # Verify no exception was raised and debug was called for the failure
        mock_logger.debug.assert_called()

    def test_log_rate_limit_logs_info_on_success(self, github_client, mock_logger):
        """Test that _log_rate_limit logs rate limit info when successful."""
        from datetime import datetime, timezone
        
        reset_datetime = datetime.fromtimestamp(
            datetime.now(timezone.utc).timestamp() + 3600, tz=timezone.utc
        )
        
        mock_core = Mock(remaining=4000, limit=5000, reset=reset_datetime)
        mock_resources = Mock(core=mock_core)
        mock_rate_limit = Mock(resources=mock_resources)
        github_client.client.get_rate_limit.return_value = mock_rate_limit

        # Execute
        github_client._log_rate_limit("fetch_secrets")

        # Verify debug was called with rate limit info
        assert any(
            "fetch_secrets" in str(call) and "4000" in str(call)
            for call in mock_logger.debug.call_args_list
        )


class TestMigrationResilienceWithRateLimitFailures:
    """Test that core migration operations succeed even when rate limit calls fail."""

    @pytest.fixture
    def mock_logger(self):
        """Create a mock logger."""
        logger = Mock(spec=Logger)
        logger.debug = Mock()
        logger.error = Mock()
        logger.warn = Mock()
        logger.info = Mock()
        return logger

    @pytest.fixture
    def github_client_with_failing_rate_limit(self, mock_logger):
        """Create a GitHubClient where rate limit calls always fail."""
        with patch('src.clients.github.Github'):
            client = GitHubClient(pat="test-token", logger=mock_logger)
            client.client = Mock()
            # Make rate limit always fail
            client.client.get_rate_limit.side_effect = AttributeError(
                "'RateLimitOverview' object has no attribute 'core'"
            )
            return client

    def test_list_repo_secrets_succeeds_despite_rate_limit_failure(
        self, github_client_with_failing_rate_limit
    ):
        """Test that list_repo_secrets works even when rate limit API fails."""
        # Setup mock repo with secrets
        mock_secret1 = Mock()
        mock_secret1.name = "SECRET_1"
        mock_secret2 = Mock()
        mock_secret2.name = "SECRET_2"
        
        mock_repo = Mock()
        mock_repo.get_secrets.return_value = [mock_secret1, mock_secret2]
        github_client_with_failing_rate_limit.client.get_repo.return_value = mock_repo

        # Execute
        result = github_client_with_failing_rate_limit.list_repo_secrets("org", "repo")

        # Verify secrets were returned despite rate limit failure
        assert len(result) == 2
        assert "SECRET_1" in result
        assert "SECRET_2" in result

    def test_create_environment_succeeds_despite_rate_limit_failure(
        self, github_client_with_failing_rate_limit, mock_logger
    ):
        """Test that create_environment works even when rate limit API fails."""
        # Setup mock
        mock_repo = Mock()
        mock_repo.get_environment.side_effect = UnknownObjectException(404, "Not Found", None)
        mock_repo.create_environment = Mock()
        github_client_with_failing_rate_limit.client.get_repo.return_value = mock_repo

        # Execute - should not raise
        github_client_with_failing_rate_limit.create_environment("org", "repo", "production")

        # Verify environment was created
        mock_repo.create_environment.assert_called_once_with("production")

    def test_get_rate_limit_info_fallback_allows_continued_operation(
        self, github_client_with_failing_rate_limit
    ):
        """Test that fallback rate limit values don't block operations."""
        # Get rate limit info (will fail and return fallback)
        rate_info = github_client_with_failing_rate_limit.get_rate_limit_info()
        
        # Verify fallback values
        assert rate_info['remaining'] == -1
        
        # Now verify we can still perform operations
        mock_repo = Mock()
        mock_repo.default_branch = "main"
        github_client_with_failing_rate_limit.client.get_user.return_value.get_repo.return_value = mock_repo

        # This should work despite rate limit failure
        branch = github_client_with_failing_rate_limit.get_default_branch("org", "repo")
        assert branch == "main"
