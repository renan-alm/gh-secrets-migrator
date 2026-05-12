"""Tests for migrator permission validation error messages."""
import pytest
from unittest.mock import Mock, patch

from src.core.config import MigrationConfig
from src.core.migrator import Migrator
from src.utils.logger import Logger


class TestMigratorValidationMessages:
    """Validate concise runtime permission and not-found messages."""

    @pytest.fixture
    def mock_logger(self):
        """Create a mock logger."""
        logger = Mock(spec=Logger)
        logger.debug = Mock()
        logger.info = Mock()
        logger.warn = Mock()
        logger.error = Mock()
        logger.success = Mock()
        return logger

    @pytest.fixture
    def migration_config(self):
        """Create base config for repo-to-repo tests."""
        return MigrationConfig(
            source_org="source-org",
            source_repo="source-repo",
            target_org="target-org",
            target_repo="target-repo",
            source_pat="source-token",
            target_pat="target-token",
        )

    @patch('src.clients.github.Github')
    def test_source_repository_not_found_message(self, mock_github_class, migration_config, mock_logger):
        """Source repository 404 should mention missing source repository."""
        mock_source_github = Mock()
        mock_target_github = Mock()

        mock_source_github.get_repo.side_effect = Exception("404 Not Found")
        mock_github_class.side_effect = [mock_source_github, mock_target_github]

        migrator = Migrator(migration_config, mock_logger)

        with pytest.raises(RuntimeError) as exc:
            migrator._validate_permissions()

        assert str(exc.value) == "Source repository 'source-org/source-repo' not found."

    @patch('src.clients.github.Github')
    def test_target_repository_not_found_message(self, mock_github_class, migration_config, mock_logger):
        """Target repository 404 should mention missing target repository."""
        mock_source_github = Mock()
        mock_target_github = Mock()

        mock_source_repo = Mock()
        mock_source_repo.get_secrets.return_value = []
        mock_source_github.get_repo.return_value = mock_source_repo
        mock_target_github.get_repo.side_effect = Exception("404 Not Found")

        mock_github_class.side_effect = [mock_source_github, mock_target_github]

        migrator = Migrator(migration_config, mock_logger)

        with pytest.raises(RuntimeError) as exc:
            migrator._validate_permissions()

        assert str(exc.value) == "Target repository 'target-org/target-repo' not found."

    @patch('src.clients.github.Github')
    def test_source_organization_not_found_message(self, mock_github_class, migration_config, mock_logger):
        """Source organization 404 should mention missing source organization."""
        mock_source_github = Mock()
        mock_target_github = Mock()

        mock_source_github.get_organization.side_effect = Exception("404 Not Found")
        mock_github_class.side_effect = [mock_source_github, mock_target_github]

        migrator = Migrator(migration_config, mock_logger)

        with pytest.raises(RuntimeError) as exc:
            migrator._validate_org_permissions()

        assert str(exc.value) == "Source organization 'source-org' not found."

    @patch('src.clients.github.Github')
    def test_target_organization_not_found_message(self, mock_github_class, migration_config, mock_logger):
        """Target organization 404 should mention missing target organization."""
        mock_source_github = Mock()
        mock_target_github = Mock()

        mock_source_org = Mock()
        mock_source_org.get_secrets.return_value = []
        mock_source_github.get_organization.return_value = mock_source_org
        mock_target_github.get_organization.side_effect = Exception("404 Not Found")

        mock_github_class.side_effect = [mock_source_github, mock_target_github]

        migrator = Migrator(migration_config, mock_logger)

        with pytest.raises(RuntimeError) as exc:
            migrator._validate_org_permissions()

        assert str(exc.value) == "Target organization 'target-org' not found."

    @patch('src.clients.github.Github')
    def test_source_workflow_repository_not_found_message(
        self, mock_github_class, migration_config, mock_logger
    ):
        """Org mode should clearly report missing source workflow repository."""
        mock_source_github = Mock()
        mock_target_github = Mock()

        mock_source_github.get_repo.side_effect = Exception("404 Not Found")
        mock_github_class.side_effect = [mock_source_github, mock_target_github]

        migrator = Migrator(migration_config, mock_logger)

        with pytest.raises(RuntimeError) as exc:
            migrator._validate_org_workflow_repository()

        assert str(exc.value) == "Source workflow repository 'source-org/source-repo' not found."

    @patch('src.clients.github.Github')
    def test_org_to_org_run_fails_before_workflow_generation(
        self, mock_github_class, migration_config, mock_logger
    ):
        """run() should stop before workflow generation when workflow repo validation fails."""
        migration_config.org_to_org = True
        mock_github_class.return_value = Mock()

        migrator = Migrator(migration_config, mock_logger)
        migrator._validate_org_permissions = Mock()
        migrator._validate_org_workflow_repository = Mock(
            side_effect=RuntimeError("Source workflow repository 'source-org/source-repo' not found.")
        )
        migrator._wait_for_rate_limit_reset = Mock()
        migrator._migrate_org_secrets_workflow = Mock()

        with pytest.raises(RuntimeError) as exc:
            migrator.run()

        assert str(exc.value) == "Source workflow repository 'source-org/source-repo' not found."
        migrator._migrate_org_secrets_workflow.assert_not_called()
