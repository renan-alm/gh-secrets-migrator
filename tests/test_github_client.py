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
