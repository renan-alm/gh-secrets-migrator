"""Tests for endpoint configuration functionality."""
from unittest.mock import Mock, patch
import pytest
from src.core.config import MigrationConfig
from src.clients.github import GitHubClient
from src.core.workflow_generator import (
    normalize_endpoint,
    extract_gh_host,
    should_set_gh_host,
    derive_web_host,
    DEFAULT_GITHUB_ENDPOINT,
    generate_environment_secret_steps,
    generate_org_secret_steps,
    generate_repo_secret_steps,
    generate_workflow
)
from src.utils.logger import Logger


class TestNormalizeEndpoint:
    """Test the normalize_endpoint helper function."""

    def test_normalize_with_trailing_slash(self):
        """Test normalizing endpoint with trailing slash."""
        assert normalize_endpoint("https://api.github.com/") == "https://api.github.com"

    def test_normalize_without_trailing_slash(self):
        """Test normalizing endpoint without trailing slash."""
        assert normalize_endpoint("https://api.github.com") == "https://api.github.com"

    def test_normalize_ghec_with_trailing_slash(self):
        """Test normalizing GHEC endpoint with trailing slash."""
        assert normalize_endpoint("https://us.api.github.com/") == "https://us.api.github.com"


class TestExtractGhHost:
    """Test the extract_gh_host helper function."""

    def test_extract_standard_github(self):
        """Test extracting hostname from standard GitHub.com."""
        assert extract_gh_host("https://api.github.com") == "api.github.com"

    def test_extract_ghec_us(self):
        """Test extracting hostname from GHEC US."""
        assert extract_gh_host("https://us.api.github.com") == "us.api.github.com"

    def test_extract_ghec_eu(self):
        """Test extracting hostname from GHEC EU."""
        assert extract_gh_host("https://eu.api.github.com") == "eu.api.github.com"

    def test_extract_ghes(self):
        """Test extracting hostname from GHES."""
        assert extract_gh_host("https://github.example.com/api/v3") == "github.example.com"

    def test_extract_http(self):
        """Test extracting hostname from HTTP endpoint."""
        assert extract_gh_host("http://localhost:8080/api/v3") == "localhost:8080"

    def test_extract_with_trailing_slash(self):
        """Test extracting hostname with trailing slash."""
        assert extract_gh_host("https://api.github.com/") == "api.github.com"


class TestDeriveWebHost:
    """Test the derive_web_host helper function."""

    def test_derive_standard_github(self):
        """Test deriving web host from standard GitHub.com API endpoint."""
        assert derive_web_host("https://api.github.com") == "https://github.com"

    def test_derive_ghec_us(self):
        """Test deriving web host from GHEC US API endpoint."""
        assert derive_web_host("https://us.api.github.com") == "https://us.github.com"

    def test_derive_ghec_eu(self):
        """Test deriving web host from GHEC EU API endpoint."""
        assert derive_web_host("https://eu.api.github.com") == "https://eu.github.com"

    def test_derive_ghes(self):
        """Test deriving web host from GHES API endpoint."""
        assert derive_web_host("https://github.example.com/api/v3") == "https://github.example.com"

    def test_derive_ghes_with_port(self):
        """Test deriving web host from GHES with port."""
        assert derive_web_host("https://github.example.com:8443/api/v3") == "https://github.example.com:8443"


class TestShouldSetGhHost:
    """Test the should_set_gh_host helper function."""

    def test_should_not_set_for_default(self):
        """Test that GH_HOST should not be set for default endpoint."""
        assert should_set_gh_host(DEFAULT_GITHUB_ENDPOINT) is False
        assert should_set_gh_host("https://api.github.com") is False

    def test_should_not_set_for_default_with_trailing_slash(self):
        """Test that GH_HOST should not be set for default endpoint with trailing slash."""
        assert should_set_gh_host("https://api.github.com/") is False

    def test_should_set_for_ghec_us(self):
        """Test that GH_HOST should be set for GHEC US."""
        assert should_set_gh_host("https://us.api.github.com") is True

    def test_should_set_for_ghec_eu(self):
        """Test that GH_HOST should be set for GHEC EU."""
        assert should_set_gh_host("https://eu.api.github.com") is True

    def test_should_set_for_ghes(self):
        """Test that GH_HOST should be set for GHES."""
        assert should_set_gh_host("https://github.example.com/api/v3") is True


class TestEndpointConfiguration:
    """Test endpoint configuration in MigrationConfig."""

    def test_config_default_endpoints(self):
        """Test that default endpoints are set correctly."""
        config = MigrationConfig(
            source_org="test-org",
            target_org="target-org",
            source_pat="test-pat",
            target_pat="test-pat"
        )
        assert config.source_endpoint == "https://api.github.com"
        assert config.target_endpoint == "https://api.github.com"

    def test_config_custom_source_endpoint(self):
        """Test custom source endpoint."""
        config = MigrationConfig(
            source_org="test-org",
            target_org="target-org",
            source_pat="test-pat",
            target_pat="test-pat",
            source_endpoint="https://us.api.github.com"
        )
        assert config.source_endpoint == "https://us.api.github.com"
        assert config.target_endpoint == "https://api.github.com"

    def test_config_custom_target_endpoint(self):
        """Test custom target endpoint."""
        config = MigrationConfig(
            source_org="test-org",
            target_org="target-org",
            source_pat="test-pat",
            target_pat="test-pat",
            target_endpoint="https://eu.api.github.com"
        )
        assert config.source_endpoint == "https://api.github.com"
        assert config.target_endpoint == "https://eu.api.github.com"

    def test_config_both_custom_endpoints(self):
        """Test both custom endpoints."""
        config = MigrationConfig(
            source_org="test-org",
            target_org="target-org",
            source_pat="test-pat",
            target_pat="test-pat",
            source_endpoint="https://us.api.github.com",
            target_endpoint="https://eu.api.github.com"
        )
        assert config.source_endpoint == "https://us.api.github.com"
        assert config.target_endpoint == "https://eu.api.github.com"

    def test_config_ghes_endpoint(self):
        """Test GitHub Enterprise Server endpoint format."""
        config = MigrationConfig(
            source_org="test-org",
            target_org="target-org",
            source_pat="test-pat",
            target_pat="test-pat",
            source_endpoint="https://github.example.com/api/v3"
        )
        assert config.source_endpoint == "https://github.example.com/api/v3"


class TestGitHubClientWithEndpoints:
    """Test GitHubClient with custom endpoints."""

    @pytest.fixture
    def mock_logger(self):
        """Create a mock logger."""
        logger = Mock(spec=Logger)
        logger.debug = Mock()
        logger.error = Mock()
        return logger

    def test_client_initialization_default_endpoint(self, mock_logger):
        """Test client initialization with default endpoint."""
        with patch('src.clients.github.Github') as mock_github_class:
            client = GitHubClient(pat="test-token", logger=mock_logger)
            mock_github_class.assert_called_once_with("test-token", base_url="https://api.github.com")
            assert client.base_url == "https://api.github.com"

    def test_client_initialization_custom_endpoint(self, mock_logger):
        """Test client initialization with custom endpoint."""
        with patch('src.clients.github.Github') as mock_github_class:
            client = GitHubClient(
                pat="test-token",
                logger=mock_logger,
                base_url="https://us.api.github.com"
            )
            mock_github_class.assert_called_once_with("test-token", base_url="https://us.api.github.com")
            assert client.base_url == "https://us.api.github.com"

    def test_client_initialization_ghes_endpoint(self, mock_logger):
        """Test client initialization with GHES endpoint."""
        with patch('src.clients.github.Github') as mock_github_class:
            client = GitHubClient(
                pat="test-token",
                logger=mock_logger,
                base_url="https://github.example.com/api/v3"
            )
            mock_github_class.assert_called_once_with(
                "test-token",
                base_url="https://github.example.com/api/v3"
            )
            assert client.base_url == "https://github.example.com/api/v3"


class TestWorkflowGeneratorWithEndpoints:
    """Test workflow generator with custom endpoints."""

    def test_environment_secret_steps_default_endpoint(self):
        """Test environment secret steps with default endpoint."""
        env_secrets = {"production": ["DB_PASSWORD"]}
        steps = generate_environment_secret_steps(
            env_secrets, "source-org", "source-repo", "target-org", "target-repo"
        )
        # Should not contain GH_HOST for default endpoint
        assert "GH_HOST:" not in steps
        assert "DB_PASSWORD" in steps

    def test_environment_secret_steps_custom_endpoint(self):
        """Test environment secret steps with custom endpoint."""
        env_secrets = {"production": ["DB_PASSWORD"]}
        steps = generate_environment_secret_steps(
            env_secrets, "source-org", "source-repo", "target-org", "target-repo",
            target_endpoint="https://us.api.github.com"
        )
        # Should contain GH_HOST for custom endpoint
        assert "GH_HOST: 'us.api.github.com'" in steps
        assert "DB_PASSWORD" in steps

    def test_org_secret_steps_default_endpoint(self):
        """Test org secret steps with default endpoint."""
        org_secrets = ["API_KEY"]
        steps = generate_org_secret_steps(org_secrets, "target-org")
        # Should not contain GH_HOST for default endpoint
        assert "GH_HOST:" not in steps
        assert "API_KEY" in steps

    def test_org_secret_steps_custom_endpoint(self):
        """Test org secret steps with custom endpoint."""
        org_secrets = ["API_KEY"]
        steps = generate_org_secret_steps(
            org_secrets, "target-org",
            target_endpoint="https://eu.api.github.com"
        )
        # Should contain GH_HOST for custom endpoint
        assert "GH_HOST: 'eu.api.github.com'" in steps
        assert "API_KEY" in steps

    def test_repo_secret_steps_default_endpoint(self):
        """Test repo secret steps with default endpoint."""
        repo_secrets = ["SECRET_KEY"]
        steps = generate_repo_secret_steps(repo_secrets, "target-org", "target-repo")
        # Should not contain GH_HOST for default endpoint
        assert "GH_HOST:" not in steps
        assert "SECRET_KEY" in steps

    def test_repo_secret_steps_custom_endpoint(self):
        """Test repo secret steps with custom endpoint."""
        repo_secrets = ["SECRET_KEY"]
        steps = generate_repo_secret_steps(
            repo_secrets, "target-org", "target-repo",
            target_endpoint="https://us.api.github.com"
        )
        # Should contain GH_HOST for custom endpoint
        assert "GH_HOST: 'us.api.github.com'" in steps
        assert "SECRET_KEY" in steps

    def test_workflow_with_custom_endpoints(self):
        """Test complete workflow generation with custom endpoints."""
        repo_secrets = ["SECRET_KEY"]
        workflow = generate_workflow(
            "source-org", "source-repo", "target-org", "target-repo",
            "migrate-secrets",
            repo_secrets=repo_secrets,
            source_endpoint="https://us.api.github.com",
            target_endpoint="https://eu.api.github.com"
        )
        # Should contain GH_HOST for target endpoint in migration steps
        assert "GH_HOST: 'eu.api.github.com'" in workflow
        # Should contain GH_HOST for source endpoint in cleanup step
        assert "GH_HOST: 'us.api.github.com'" in workflow
        assert "SECRET_KEY" in workflow

    def test_workflow_default_endpoints_no_gh_host(self):
        """Test workflow with default endpoints doesn't set GH_HOST."""
        repo_secrets = ["SECRET_KEY"]
        workflow = generate_workflow(
            "source-org", "source-repo", "target-org", "target-repo",
            "migrate-secrets",
            repo_secrets=repo_secrets
        )
        # Should not contain GH_HOST when using default endpoints
        # Count occurrences - should be 0
        gh_host_count = workflow.count("GH_HOST:")
        assert gh_host_count == 0

    def test_workflow_ghes_endpoint(self):
        """Test workflow generation with GHES endpoint."""
        repo_secrets = ["SECRET_KEY"]
        workflow = generate_workflow(
            "source-org", "source-repo", "target-org", "target-repo",
            "migrate-secrets",
            repo_secrets=repo_secrets,
            target_endpoint="https://github.example.com/api/v3"
        )
        # Should contain GH_HOST with only hostname (no path)
        assert "GH_HOST: 'github.example.com'" in workflow

    def test_workflow_with_env_secrets_custom_endpoint(self):
        """Test workflow with environment secrets and custom endpoint."""
        env_secrets = {"production": ["DB_PASSWORD"], "staging": ["API_KEY"]}
        workflow = generate_workflow(
            "source-org", "source-repo", "target-org", "target-repo",
            "migrate-secrets",
            env_secrets=env_secrets,
            target_endpoint="https://us.api.github.com"
        )
        # Should contain GH_HOST for custom endpoint
        assert "GH_HOST: 'us.api.github.com'" in workflow
        assert "DB_PASSWORD" in workflow
        assert "API_KEY" in workflow

    def test_workflow_with_org_secrets_custom_endpoint(self):
        """Test workflow with org secrets and custom endpoint."""
        org_secrets = ["ORG_SECRET_1", "ORG_SECRET_2"]
        workflow = generate_workflow(
            "source-org", "source-repo", "target-org", "target-repo",
            "migrate-org-secrets",
            org_secrets=org_secrets,
            target_endpoint="https://eu.api.github.com"
        )
        # Should contain GH_HOST for custom endpoint
        assert "GH_HOST: 'eu.api.github.com'" in workflow
        assert "ORG_SECRET_1" in workflow
        assert "ORG_SECRET_2" in workflow


class TestEndpointURLFormats:
    """Test various endpoint URL formats."""

    def test_ghec_data_residency_us(self):
        """Test GHEC Data Residency US endpoint."""
        config = MigrationConfig(
            source_org="test-org",
            target_org="target-org",
            source_pat="test-pat",
            target_pat="test-pat",
            target_endpoint="https://us.api.github.com"
        )
        assert config.target_endpoint == "https://us.api.github.com"

    def test_ghec_data_residency_eu(self):
        """Test GHEC Data Residency EU endpoint."""
        config = MigrationConfig(
            source_org="test-org",
            target_org="target-org",
            source_pat="test-pat",
            target_pat="test-pat",
            target_endpoint="https://eu.api.github.com"
        )
        assert config.target_endpoint == "https://eu.api.github.com"

    def test_ghes_with_path(self):
        """Test GHES endpoint with API path."""
        config = MigrationConfig(
            source_org="test-org",
            target_org="target-org",
            source_pat="test-pat",
            target_pat="test-pat",
            source_endpoint="https://github.company.com/api/v3"
        )
        assert config.source_endpoint == "https://github.company.com/api/v3"

    def test_http_endpoint(self):
        """Test HTTP (non-HTTPS) endpoint for local testing."""
        config = MigrationConfig(
            source_org="test-org",
            target_org="target-org",
            source_pat="test-pat",
            target_pat="test-pat",
            source_endpoint="http://localhost:8080/api/v3"
        )
        assert config.source_endpoint == "http://localhost:8080/api/v3"
