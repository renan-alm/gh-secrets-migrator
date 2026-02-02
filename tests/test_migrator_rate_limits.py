"""Tests for Migrator rate limit handling and resilience."""
import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timezone

from src.core.migrator import Migrator
from src.core.config import MigrationConfig
from src.utils.logger import Logger


class TestMigratorRateLimitChecks:
    """Test cases for Migrator._check_rate_limits() method."""

    @pytest.fixture
    def mock_logger(self):
        """Create a mock logger with all required methods."""
        logger = Mock(spec=Logger)
        logger.debug = Mock()
        logger.info = Mock()
        logger.warn = Mock()
        logger.error = Mock()
        logger.success = Mock()
        return logger

    @pytest.fixture
    def migration_config(self):
        """Create a test migration config."""
        return MigrationConfig(
            source_org="source-org",
            source_repo="source-repo",
            target_org="target-org",
            target_repo="target-repo",
            source_pat="source-pat-token",
            target_pat="target-pat-token",
        )

    def _create_rate_limit_mock(self, remaining=5000, limit=5000):
        """Helper to create a properly structured rate limit mock for PyGithub 2.7.0+."""
        reset_time = datetime.now(timezone.utc).timestamp() + 3600
        reset_datetime = datetime.fromtimestamp(reset_time, tz=timezone.utc)
        
        mock_core = Mock()
        mock_core.remaining = remaining
        mock_core.limit = limit
        mock_core.reset = reset_datetime
        
        mock_resources = Mock()
        mock_resources.core = mock_core
        
        mock_rate_limit = Mock()
        mock_rate_limit.resources = mock_resources
        
        return mock_rate_limit

    @patch('src.clients.github.Github')
    def test_check_rate_limits_returns_true_when_sufficient(
        self, mock_github_class, migration_config, mock_logger
    ):
        """Test that _check_rate_limits returns True when both APIs have sufficient limits."""
        # Setup mock GitHub clients
        mock_source_github = Mock()
        mock_target_github = Mock()
        mock_source_github.get_rate_limit.return_value = self._create_rate_limit_mock(
            remaining=4000, limit=5000
        )
        mock_target_github.get_rate_limit.return_value = self._create_rate_limit_mock(
            remaining=3500, limit=5000
        )
        
        # Return different mocks for source and target PATs
        mock_github_class.side_effect = [mock_source_github, mock_target_github]
        
        # Create migrator
        migrator = Migrator(migration_config, mock_logger)
        
        # Execute
        result = migrator._check_rate_limits("test_checkpoint")
        
        # Verify
        assert result is True

    @patch('src.clients.github.Github')
    def test_check_rate_limits_returns_true_when_rate_limit_api_fails(
        self, mock_github_class, migration_config, mock_logger
    ):
        """Test that _check_rate_limits returns True (doesn't block) when rate limit API errors."""
        # Setup mock GitHub clients where rate limit fails
        mock_source_github = Mock()
        mock_target_github = Mock()
        
        # Simulate the PyGithub 2.7.0+ error
        mock_source_github.get_rate_limit.side_effect = AttributeError(
            "'RateLimitOverview' object has no attribute 'core'"
        )
        mock_target_github.get_rate_limit.side_effect = AttributeError(
            "'RateLimitOverview' object has no attribute 'core'"
        )
        
        mock_github_class.side_effect = [mock_source_github, mock_target_github]
        
        # Create migrator
        migrator = Migrator(migration_config, mock_logger)
        
        # Execute - should return True (fallback behavior allows continuation)
        result = migrator._check_rate_limits("test_checkpoint")
        
        # Verify - when rate limit fails, remaining is -1, and the check should allow continuation
        # The logic is: (source_info['remaining'] > 30 if source_ok else True)
        # When remaining is -1, source_ok is False (remaining >= 0 is False), so it returns True
        assert result is True

    @patch('src.clients.github.Github')
    def test_check_rate_limits_warns_on_low_remaining(
        self, mock_github_class, migration_config, mock_logger
    ):
        """Test that _check_rate_limits logs warning when remaining < 50."""
        # Setup mock with low remaining
        mock_source_github = Mock()
        mock_target_github = Mock()
        mock_source_github.get_rate_limit.return_value = self._create_rate_limit_mock(
            remaining=25, limit=5000
        )
        mock_target_github.get_rate_limit.return_value = self._create_rate_limit_mock(
            remaining=5000, limit=5000
        )
        
        mock_github_class.side_effect = [mock_source_github, mock_target_github]
        
        # Create migrator
        migrator = Migrator(migration_config, mock_logger)
        
        # Execute
        result = migrator._check_rate_limits("test_checkpoint")
        
        # Verify warning was logged (remaining < 50)
        assert any(
            "rate limit low" in str(call).lower() or "25" in str(call)
            for call in mock_logger.warn.call_args_list
        )
        
        # Should return False because 25 < 30
        assert result is False

    @patch('src.clients.github.Github')
    def test_check_rate_limits_returns_false_when_critically_low(
        self, mock_github_class, migration_config, mock_logger
    ):
        """Test that _check_rate_limits returns False when remaining <= 30."""
        mock_source_github = Mock()
        mock_target_github = Mock()
        mock_source_github.get_rate_limit.return_value = self._create_rate_limit_mock(
            remaining=20, limit=5000
        )
        mock_target_github.get_rate_limit.return_value = self._create_rate_limit_mock(
            remaining=5000, limit=5000
        )
        
        mock_github_class.side_effect = [mock_source_github, mock_target_github]
        
        migrator = Migrator(migration_config, mock_logger)
        result = migrator._check_rate_limits("test_checkpoint")
        
        # Should return False because source has only 20 remaining (< 30)
        assert result is False


class TestMigratorResilienceWithRateLimitFailures:
    """Integration-style tests ensuring migration succeeds despite rate limit failures."""

    @pytest.fixture
    def mock_logger(self):
        """Create a mock logger with all required methods."""
        logger = Mock(spec=Logger)
        logger.debug = Mock()
        logger.info = Mock()
        logger.warn = Mock()
        logger.error = Mock()
        logger.success = Mock()
        return logger

    @pytest.fixture
    def migration_config(self):
        """Create a test migration config."""
        return MigrationConfig(
            source_org="source-org",
            source_repo="source-repo",
            target_org="target-org",
            target_repo="target-repo",
            source_pat="source-pat-token",
            target_pat="target-pat-token",
        )

    @patch('src.clients.github.Github')
    def test_migrator_initialization_succeeds_with_failing_rate_limits(
        self, mock_github_class, migration_config, mock_logger
    ):
        """Test that Migrator can be initialized even when rate limit API fails."""
        mock_github = Mock()
        mock_github.get_rate_limit.side_effect = AttributeError(
            "'RateLimitOverview' object has no attribute 'core'"
        )
        mock_github_class.return_value = mock_github
        
        # Should not raise
        migrator = Migrator(migration_config, mock_logger)
        
        assert migrator is not None
        assert migrator.source_api is not None
        assert migrator.target_api is not None

    @patch('src.clients.github.Github')
    def test_rate_limit_check_does_not_block_when_api_unavailable(
        self, mock_github_class, migration_config, mock_logger
    ):
        """Test that rate limit checks gracefully handle API failures without blocking."""
        mock_source_github = Mock()
        mock_target_github = Mock()
        
        # Both APIs fail to get rate limit
        mock_source_github.get_rate_limit.side_effect = ConnectionError("Network error")
        mock_target_github.get_rate_limit.side_effect = ConnectionError("Network error")
        
        mock_github_class.side_effect = [mock_source_github, mock_target_github]
        
        migrator = Migrator(migration_config, mock_logger)
        
        # Should return True (allow continuation) when rate limit is unavailable
        result = migrator._check_rate_limits("network_test")
        assert result is True

    @patch('src.clients.github.Github')
    def test_source_api_operations_work_despite_rate_limit_failure(
        self, mock_github_class, migration_config, mock_logger
    ):
        """Test that source API operations work even when rate limit calls fail."""
        mock_source_github = Mock()
        mock_target_github = Mock()
        
        # Rate limit fails
        mock_source_github.get_rate_limit.side_effect = AttributeError("API changed")
        mock_target_github.get_rate_limit.side_effect = AttributeError("API changed")
        
        # But repo operations work
        mock_repo = Mock()
        mock_secret = Mock()
        mock_secret.name = "MY_SECRET"
        mock_repo.get_secrets.return_value = [mock_secret]
        mock_source_github.get_repo.return_value = mock_repo
        
        mock_github_class.side_effect = [mock_source_github, mock_target_github]
        
        migrator = Migrator(migration_config, mock_logger)
        
        # Source API should still work
        secrets = migrator.source_api.list_repo_secrets("org", "repo")
        assert "MY_SECRET" in secrets

    @patch('src.clients.github.Github')
    def test_wait_for_rate_limit_reset_handles_failures(
        self, mock_github_class, migration_config, mock_logger
    ):
        """Test that _wait_for_rate_limit_reset doesn't crash when rate limit API fails."""
        mock_source_github = Mock()
        mock_target_github = Mock()
        
        # Rate limit API fails
        mock_source_github.get_rate_limit.side_effect = AttributeError("API changed")
        mock_target_github.get_rate_limit.side_effect = AttributeError("API changed")
        
        mock_github_class.side_effect = [mock_source_github, mock_target_github]
        
        migrator = Migrator(migration_config, mock_logger)
        
        # Should not raise - when rate limit is unavailable (returns -1),
        # the wait logic should skip waiting
        migrator._wait_for_rate_limit_reset()
        
        # If we get here without exception, the test passes

    @patch('src.clients.github.Github')
    def test_full_rate_limit_info_structure_with_new_api(
        self, mock_github_class, migration_config, mock_logger
    ):
        """Test that the new PyGithub 2.7.0+ API structure works correctly end-to-end."""
        reset_time = datetime.now(timezone.utc).timestamp() + 1800  # 30 min from now
        reset_datetime = datetime.fromtimestamp(reset_time, tz=timezone.utc)
        
        # Create properly structured mock for PyGithub 2.7.0+
        mock_core = Mock()
        mock_core.remaining = 4500
        mock_core.limit = 5000
        mock_core.reset = reset_datetime
        
        mock_resources = Mock()
        mock_resources.core = mock_core
        
        mock_rate_limit = Mock()
        mock_rate_limit.resources = mock_resources
        
        mock_github = Mock()
        mock_github.get_rate_limit.return_value = mock_rate_limit
        mock_github_class.return_value = mock_github
        
        migrator = Migrator(migration_config, mock_logger)
        
        # Get rate limit info
        info = migrator.source_api.get_rate_limit_info()
        
        # Verify all fields are correctly populated
        assert info['remaining'] == 4500
        assert info['limit'] == 5000
        assert info['reset_time'] > 0
        assert 0 <= info['reset_in_seconds'] <= 1800 + 5  # Allow small timing variance
