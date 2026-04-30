"""Tests for environment secret migration in the Migrator and GitHubClient."""
import pytest
from unittest.mock import Mock, patch, call
from github import UnknownObjectException

from src.core.migrator import Migrator
from src.core.config import MigrationConfig
from src.clients.github import GitHubClient
from src.utils.logger import Logger


class TestGitHubClientListEnvironments:
    """Test cases for GitHubClient.list_environments()."""

    @pytest.fixture
    def mock_logger(self):
        logger = Mock(spec=Logger)
        logger.debug = Mock()
        logger.error = Mock()
        return logger

    @pytest.fixture
    def github_client(self, mock_logger):
        with patch('src.clients.github.Github'):
            client = GitHubClient(pat="test-token", logger=mock_logger)
            client.client = Mock()
            return client

    def test_list_environments_returns_names(self, github_client):
        """Test listing environments returns their names."""
        mock_repo = Mock()
        env1, env2 = Mock(name="production"), Mock(name="staging")
        env1.name = "production"
        env2.name = "staging"
        mock_repo.get_environments.return_value = [env1, env2]
        github_client.client.get_repo.return_value = mock_repo

        result = github_client.list_environments("org", "repo")

        assert result == ["production", "staging"]
        github_client.client.get_repo.assert_called_once_with("org/repo")

    def test_list_environments_empty(self, github_client):
        """Test listing environments when none exist."""
        mock_repo = Mock()
        mock_repo.get_environments.return_value = []
        github_client.client.get_repo.return_value = mock_repo

        result = github_client.list_environments("org", "repo")

        assert result == []

    def test_list_environments_handles_error(self, github_client):
        """Test that list_environments returns empty list on error."""
        github_client.client.get_repo.side_effect = Exception("API error")

        result = github_client.list_environments("org", "repo")

        assert result == []


class TestGitHubClientListEnvironmentSecrets:
    """Test cases for GitHubClient.list_environment_secrets()."""

    @pytest.fixture
    def mock_logger(self):
        logger = Mock(spec=Logger)
        logger.debug = Mock()
        logger.error = Mock()
        return logger

    @pytest.fixture
    def github_client(self, mock_logger):
        with patch('src.clients.github.Github'):
            client = GitHubClient(pat="test-token", logger=mock_logger)
            client.client = Mock()
            return client

    def test_list_environment_secrets_returns_names(self, github_client):
        """Test listing secrets for a specific environment."""
        mock_repo = Mock()
        mock_env = Mock()
        secret1, secret2 = Mock(), Mock()
        secret1.name = "DB_PASSWORD"
        secret2.name = "API_KEY"
        mock_env.get_secrets.return_value = [secret1, secret2]
        mock_repo.get_environment.return_value = mock_env
        github_client.client.get_repo.return_value = mock_repo

        result = github_client.list_environment_secrets("org", "repo", "production")

        assert result == ["DB_PASSWORD", "API_KEY"]

    def test_list_environment_secrets_empty(self, github_client):
        """Test listing secrets when environment has none."""
        mock_repo = Mock()
        mock_env = Mock()
        mock_env.get_secrets.return_value = []
        mock_repo.get_environment.return_value = mock_env
        github_client.client.get_repo.return_value = mock_repo

        result = github_client.list_environment_secrets("org", "repo", "production")

        assert result == []

    def test_list_environment_secrets_handles_missing_env(self, github_client):
        """Test that missing environment returns empty list."""
        mock_repo = Mock()
        mock_repo.get_environment.side_effect = UnknownObjectException(404, "Not Found", None)
        github_client.client.get_repo.return_value = mock_repo

        result = github_client.list_environment_secrets("org", "repo", "nonexistent")

        assert result == []


class TestGitHubClientListAllEnvironmentsWithSecrets:
    """Test cases for GitHubClient.list_all_environments_with_secrets()."""

    @pytest.fixture
    def mock_logger(self):
        logger = Mock(spec=Logger)
        logger.debug = Mock()
        logger.error = Mock()
        return logger

    @pytest.fixture
    def github_client(self, mock_logger):
        with patch('src.clients.github.Github'):
            client = GitHubClient(pat="test-token", logger=mock_logger)
            client.client = Mock()
            return client

    def test_list_all_environments_with_secrets(self, github_client):
        """Test listing all environments with their secret names."""
        mock_repo = Mock()

        # Set up environments
        env_prod = Mock()
        env_prod.name = "production"
        env_staging = Mock()
        env_staging.name = "staging"
        mock_repo.get_environments.return_value = [env_prod, env_staging]

        # Set up secrets per environment
        prod_secret = Mock()
        prod_secret.name = "DB_PASSWORD"
        staging_secret = Mock()
        staging_secret.name = "API_KEY"

        prod_env_obj = Mock()
        prod_env_obj.get_secrets.return_value = [prod_secret]
        staging_env_obj = Mock()
        staging_env_obj.get_secrets.return_value = [staging_secret]

        mock_repo.get_environment.side_effect = lambda name: {
            "production": prod_env_obj,
            "staging": staging_env_obj,
        }[name]

        github_client.client.get_repo.return_value = mock_repo

        result = github_client.list_all_environments_with_secrets("org", "repo")

        assert result == {
            "production": ["DB_PASSWORD"],
            "staging": ["API_KEY"],
        }

    def test_list_all_environments_with_secrets_empty_repo(self, github_client):
        """Test with a repo that has no environments."""
        mock_repo = Mock()
        mock_repo.get_environments.return_value = []
        github_client.client.get_repo.return_value = mock_repo

        result = github_client.list_all_environments_with_secrets("org", "repo")

        assert result == {}

    def test_list_all_environments_with_secrets_partial_failure(self, github_client):
        """Test that one env failing to list secrets doesn't break others."""
        mock_repo = Mock()

        env_prod = Mock()
        env_prod.name = "production"
        env_broken = Mock()
        env_broken.name = "broken"
        mock_repo.get_environments.return_value = [env_prod, env_broken]

        prod_secret = Mock()
        prod_secret.name = "SECRET_A"
        prod_env_obj = Mock()
        prod_env_obj.get_secrets.return_value = [prod_secret]

        broken_env_obj = Mock()
        broken_env_obj.get_secrets.side_effect = Exception("Permission denied")

        mock_repo.get_environment.side_effect = lambda name: {
            "production": prod_env_obj,
            "broken": broken_env_obj,
        }[name]

        github_client.client.get_repo.return_value = mock_repo

        result = github_client.list_all_environments_with_secrets("org", "repo")

        assert result["production"] == ["SECRET_A"]
        assert result["broken"] == []

    def test_list_all_environments_with_secrets_handles_repo_error(self, github_client):
        """Test that a repo-level error returns empty dict."""
        github_client.client.get_repo.side_effect = Exception("Not found")

        result = github_client.list_all_environments_with_secrets("org", "repo")

        assert result == {}


class TestMigratorRecreateEnvironments:
    """Test cases for Migrator._recreate_environments()."""

    @pytest.fixture
    def mock_logger(self):
        logger = Mock(spec=Logger)
        logger.debug = Mock()
        logger.info = Mock()
        logger.warn = Mock()
        logger.error = Mock()
        logger.success = Mock()
        return logger

    @pytest.fixture
    def migration_config(self):
        return MigrationConfig(
            source_org="source-org",
            source_repo="source-repo",
            target_org="target-org",
            target_repo="target-repo",
            source_pat="source-pat-token",
            target_pat="target-pat-token",
        )

    @patch('src.clients.github.Github')
    def test_recreate_environments_creates_all(
        self, mock_github_class, migration_config, mock_logger
    ):
        """Test that all source environments are recreated in the target."""
        mock_github_class.return_value = Mock()
        migrator = Migrator(migration_config, mock_logger)

        migrator.source_api = Mock(spec=GitHubClient)
        migrator.target_api = Mock(spec=GitHubClient)

        migrator.source_api.list_environments.return_value = ["production", "staging"]
        migrator.target_api.create_environment.return_value = True

        migrator._recreate_environments()

        migrator.source_api.list_environments.assert_called_once_with("source-org", "source-repo")
        assert migrator.target_api.create_environment.call_count == 2
        migrator.target_api.create_environment.assert_any_call("target-org", "target-repo", "production")
        migrator.target_api.create_environment.assert_any_call("target-org", "target-repo", "staging")
        mock_logger.success.assert_called()

    @patch('src.clients.github.Github')
    def test_recreate_environments_no_envs(
        self, mock_github_class, migration_config, mock_logger
    ):
        """Test that no environments means nothing is created."""
        mock_github_class.return_value = Mock()
        migrator = Migrator(migration_config, mock_logger)

        migrator.source_api = Mock(spec=GitHubClient)
        migrator.target_api = Mock(spec=GitHubClient)

        migrator.source_api.list_environments.return_value = []

        migrator._recreate_environments()

        migrator.target_api.create_environment.assert_not_called()
        mock_logger.info.assert_any_call("No environments to recreate")

    @patch('src.clients.github.Github')
    def test_recreate_environments_skips_existing(
        self, mock_github_class, migration_config, mock_logger
    ):
        """Test that already-existing environments are logged as skipped."""
        mock_github_class.return_value = Mock()
        migrator = Migrator(migration_config, mock_logger)

        migrator.source_api = Mock(spec=GitHubClient)
        migrator.target_api = Mock(spec=GitHubClient)

        migrator.source_api.list_environments.return_value = ["production", "staging"]
        # production is new, staging already exists
        migrator.target_api.create_environment.side_effect = [True, False]

        migrator._recreate_environments()

        mock_logger.success.assert_called_once()
        assert "production" in mock_logger.success.call_args[0][0]
        # Skipped envs are logged
        skipped_logged = any(
            "Skipping" in str(c) and "staging" in str(c)
            for c in mock_logger.info.call_args_list
        )
        assert skipped_logged

    @patch('src.clients.github.Github')
    def test_recreate_environments_handles_partial_failure(
        self, mock_github_class, migration_config, mock_logger
    ):
        """Test that one environment failing doesn't stop others."""
        mock_github_class.return_value = Mock()
        migrator = Migrator(migration_config, mock_logger)

        migrator.source_api = Mock(spec=GitHubClient)
        migrator.target_api = Mock(spec=GitHubClient)

        migrator.source_api.list_environments.return_value = ["production", "staging", "dev"]
        migrator.target_api.create_environment.side_effect = [
            True,                                    # production succeeds
            RuntimeError("Permission denied"),       # staging fails
            True,                                    # dev succeeds
        ]

        migrator._recreate_environments()

        assert migrator.target_api.create_environment.call_count == 3
        mock_logger.warn.assert_called_once()
        assert "staging" in mock_logger.warn.call_args[0][0]

    @patch('src.clients.github.Github')
    def test_recreate_environments_raises_on_unexpected_error(
        self, mock_github_class, migration_config, mock_logger
    ):
        """Test that unexpected errors during env listing propagate."""
        mock_github_class.return_value = Mock()
        migrator = Migrator(migration_config, mock_logger)

        migrator.source_api = Mock(spec=GitHubClient)
        migrator.target_api = Mock(spec=GitHubClient)

        migrator.source_api.list_environments.side_effect = Exception("Network failure")

        with pytest.raises(RuntimeError, match="Failed to recreate environments"):
            migrator._recreate_environments()


class TestMigratorEnvironmentSecretsInRun:
    """Test that the run() method correctly lists and passes env secrets to workflow."""

    @pytest.fixture
    def mock_logger(self):
        logger = Mock(spec=Logger)
        logger.debug = Mock()
        logger.info = Mock()
        logger.warn = Mock()
        logger.error = Mock()
        logger.success = Mock()
        return logger

    @pytest.fixture
    def migration_config(self):
        return MigrationConfig(
            source_org="source-org",
            source_repo="source-repo",
            target_org="target-org",
            target_repo="target-repo",
            source_pat="source-pat-token",
            target_pat="target-pat-token",
        )

    @patch('src.core.migrator.generate_workflow')
    @patch('src.clients.github.Github')
    def test_run_passes_env_secrets_to_workflow(
        self, mock_github_class, mock_generate_workflow,
        migration_config, mock_logger
    ):
        """Test that run() fetches env secrets and passes them to generate_workflow."""
        mock_github_class.return_value = Mock()
        migrator = Migrator(migration_config, mock_logger)

        migrator.source_api = Mock(spec=GitHubClient)
        migrator.target_api = Mock(spec=GitHubClient)

        # Stub all methods called during run()
        migrator._validate_permissions = Mock()
        migrator._wait_for_rate_limit_reset = Mock()
        migrator._recreate_environments = Mock()
        migrator._check_rate_limits = Mock()
        migrator._get_workflow_run_url = Mock(return_value="")

        migrator.source_api.list_repo_secrets.return_value = ["APP_SECRET"]
        migrator.source_api.list_all_environments_with_secrets.return_value = {
            "production": ["DB_PASSWORD"],
            "staging": ["API_KEY"],
        }
        migrator.source_api.get_default_branch.return_value = "main"
        migrator.source_api.get_commit_sha.return_value = "abc123"
        migrator.source_api.delete_branch.return_value = None
        migrator.source_api.create_repo_secret.return_value = None
        migrator.source_api.create_branch.return_value = None
        migrator.source_api.create_file.return_value = None
        migrator.source_api.get_rate_limit_info.return_value = {
            'remaining': 5000, 'limit': 5000, 'reset_time': 0, 'reset_in_seconds': 0
        }

        mock_generate_workflow.return_value = "workflow-yaml-content"

        migrator.run()

        # Verify env secrets were fetched
        migrator.source_api.list_all_environments_with_secrets.assert_called_once_with(
            "source-org", "source-repo"
        )

        # Verify env secrets were passed to generate_workflow
        mock_generate_workflow.assert_called_once()
        call_kwargs = mock_generate_workflow.call_args
        assert call_kwargs.kwargs.get("env_secrets") == {
            "production": ["DB_PASSWORD"],
            "staging": ["API_KEY"],
        }

    @patch('src.core.migrator.generate_workflow')
    @patch('src.clients.github.Github')
    def test_run_handles_no_env_secrets(
        self, mock_github_class, mock_generate_workflow,
        migration_config, mock_logger
    ):
        """Test that run() works when there are no environment secrets."""
        mock_github_class.return_value = Mock()
        migrator = Migrator(migration_config, mock_logger)

        migrator.source_api = Mock(spec=GitHubClient)
        migrator.target_api = Mock(spec=GitHubClient)

        migrator._validate_permissions = Mock()
        migrator._wait_for_rate_limit_reset = Mock()
        migrator._recreate_environments = Mock()
        migrator._check_rate_limits = Mock()
        migrator._get_workflow_run_url = Mock(return_value="")

        migrator.source_api.list_repo_secrets.return_value = ["SECRET_1"]
        migrator.source_api.list_all_environments_with_secrets.return_value = {}
        migrator.source_api.get_default_branch.return_value = "main"
        migrator.source_api.get_commit_sha.return_value = "abc123"
        migrator.source_api.delete_branch.return_value = None
        migrator.source_api.create_repo_secret.return_value = None
        migrator.source_api.create_branch.return_value = None
        migrator.source_api.create_file.return_value = None
        migrator.source_api.get_rate_limit_info.return_value = {
            'remaining': 5000, 'limit': 5000, 'reset_time': 0, 'reset_in_seconds': 0
        }

        mock_generate_workflow.return_value = "workflow-yaml-content"

        migrator.run()

        # Verify generate_workflow was called with empty env_secrets
        call_kwargs = mock_generate_workflow.call_args
        assert call_kwargs.kwargs.get("env_secrets") == {}

    @patch('src.core.migrator.generate_workflow')
    @patch('src.clients.github.Github')
    def test_run_skips_env_recreation_when_flag_set(
        self, mock_github_class, mock_generate_workflow,
        mock_logger
    ):
        """Test that --skip-envs flag skips environment recreation but still lists env secrets."""
        config = MigrationConfig(
            source_org="source-org",
            source_repo="source-repo",
            target_org="target-org",
            target_repo="target-repo",
            source_pat="source-pat-token",
            target_pat="target-pat-token",
            skip_envs=True,
        )
        mock_github_class.return_value = Mock()
        migrator = Migrator(config, mock_logger)

        migrator.source_api = Mock(spec=GitHubClient)
        migrator.target_api = Mock(spec=GitHubClient)

        migrator._validate_permissions = Mock()
        migrator._wait_for_rate_limit_reset = Mock()
        migrator._check_rate_limits = Mock()
        migrator._get_workflow_run_url = Mock(return_value="")

        migrator.source_api.list_repo_secrets.return_value = ["SECRET_1"]
        migrator.source_api.list_all_environments_with_secrets.return_value = {
            "production": ["DB_PASSWORD"],
        }
        migrator.source_api.get_default_branch.return_value = "main"
        migrator.source_api.get_commit_sha.return_value = "abc123"
        migrator.source_api.delete_branch.return_value = None
        migrator.source_api.create_repo_secret.return_value = None
        migrator.source_api.create_branch.return_value = None
        migrator.source_api.create_file.return_value = None
        migrator.source_api.get_rate_limit_info.return_value = {
            'remaining': 5000, 'limit': 5000, 'reset_time': 0, 'reset_in_seconds': 0
        }

        mock_generate_workflow.return_value = "workflow-yaml-content"

        migrator.run()

        # _recreate_environments should NOT have been called directly
        # (we didn't mock it, and skip_envs=True skips that call)
        mock_logger.info.assert_any_call("Skipping environment recreation (--skip-envs flag set)")

        # But env secrets should still be listed and passed to workflow
        migrator.source_api.list_all_environments_with_secrets.assert_called_once()

    @patch('src.core.migrator.generate_workflow')
    @patch('src.clients.github.Github')
    def test_run_logs_env_secrets_info(
        self, mock_github_class, mock_generate_workflow,
        migration_config, mock_logger
    ):
        """Test that run() logs environment secret details for the user."""
        mock_github_class.return_value = Mock()
        migrator = Migrator(migration_config, mock_logger)

        migrator.source_api = Mock(spec=GitHubClient)
        migrator.target_api = Mock(spec=GitHubClient)

        migrator._validate_permissions = Mock()
        migrator._wait_for_rate_limit_reset = Mock()
        migrator._recreate_environments = Mock()
        migrator._check_rate_limits = Mock()
        migrator._get_workflow_run_url = Mock(return_value="")

        migrator.source_api.list_repo_secrets.return_value = ["SECRET_1"]
        migrator.source_api.list_all_environments_with_secrets.return_value = {
            "production": ["DB_PASSWORD", "API_KEY"],
            "staging": [],
        }
        migrator.source_api.get_default_branch.return_value = "main"
        migrator.source_api.get_commit_sha.return_value = "abc123"
        migrator.source_api.delete_branch.return_value = None
        migrator.source_api.create_repo_secret.return_value = None
        migrator.source_api.create_branch.return_value = None
        migrator.source_api.create_file.return_value = None
        migrator.source_api.get_rate_limit_info.return_value = {
            'remaining': 5000, 'limit': 5000, 'reset_time': 0, 'reset_in_seconds': 0
        }

        mock_generate_workflow.return_value = "workflow-yaml-content"

        migrator.run()

        # Verify env secrets info was logged
        info_calls = [str(c) for c in mock_logger.info.call_args_list]
        assert any("Environment secrets to migrate" in c for c in info_calls)
        assert any("production" in c and "DB_PASSWORD" in c for c in info_calls)
        assert any("staging" in c and "(no secrets, skipping from workflow)" in c for c in info_calls)

    @patch('src.core.migrator.generate_workflow')
    @patch('src.clients.github.Github')
    def test_run_returns_early_when_only_system_secrets(
        self, mock_github_class, mock_generate_workflow,
        migration_config, mock_logger
    ):
        """Test that run() returns early if only system secrets and no env secrets exist."""
        mock_github_class.return_value = Mock()
        migrator = Migrator(migration_config, mock_logger)

        migrator.source_api = Mock(spec=GitHubClient)
        migrator.target_api = Mock(spec=GitHubClient)

        migrator._validate_permissions = Mock()
        migrator._wait_for_rate_limit_reset = Mock()
        migrator._recreate_environments = Mock()
        migrator._check_rate_limits = Mock()

        # Only system secrets exist
        migrator.source_api.list_repo_secrets.return_value = [
            "github_token", "SECRETS_MIGRATOR_PAT"
        ]
        # No environment secrets either
        migrator.source_api.list_all_environments_with_secrets.return_value = {}
        migrator.source_api.get_rate_limit_info.return_value = {
            'remaining': 5000, 'limit': 5000, 'reset_time': 0, 'reset_in_seconds': 0
        }

        migrator.run()

        # generate_workflow should never be called
        mock_generate_workflow.assert_not_called()

    @patch('src.core.migrator.generate_workflow')
    @patch('src.clients.github.Github')
    def test_run_proceeds_with_only_env_secrets(
        self, mock_github_class, mock_generate_workflow,
        migration_config, mock_logger
    ):
        """Test that run() proceeds when there are no repo secrets but env secrets exist."""
        mock_github_class.return_value = Mock()
        migrator = Migrator(migration_config, mock_logger)

        migrator.source_api = Mock(spec=GitHubClient)
        migrator.target_api = Mock(spec=GitHubClient)

        migrator._validate_permissions = Mock()
        migrator._wait_for_rate_limit_reset = Mock()
        migrator._recreate_environments = Mock()
        migrator._check_rate_limits = Mock()

        # No repo secrets (only system ones)
        migrator.source_api.list_repo_secrets.return_value = [
            "github_token", "SECRETS_MIGRATOR_PAT"
        ]
        # But environment secrets exist
        migrator.source_api.list_all_environments_with_secrets.return_value = {
            "production": ["DB_PASSWORD", "API_KEY"]
        }
        migrator.source_api.get_rate_limit_info.return_value = {
            'remaining': 5000, 'limit': 5000, 'reset_time': 0, 'reset_in_seconds': 0
        }
        migrator.source_api.get_default_branch.return_value = "main"
        migrator.source_api.get_commit_sha.return_value = "abc123"
        migrator.source_api.delete_branch.return_value = None
        migrator.source_api.create_repo_secret.return_value = None
        migrator.source_api.create_branch.return_value = None
        migrator.source_api.create_file.return_value = "sha456"
        migrator._get_workflow_run_url = Mock(return_value="")
        mock_generate_workflow.return_value = "workflow content"

        migrator.run()

        # generate_workflow SHOULD be called since env secrets exist
        mock_generate_workflow.assert_called_once()
        call_kwargs = mock_generate_workflow.call_args
        # env_secrets should include the production environment
        assert "production" in (call_kwargs.kwargs.get('env_secrets') or call_kwargs[1].get('env_secrets', {}))
