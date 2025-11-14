"""Tests for configuration module."""
from src.core.config import MigrationConfig


class TestMigrationConfig:
    """Test cases for MigrationConfig."""

    def test_config_repo_to_repo_minimal(self):
        """Test basic repo-to-repo configuration."""
        config = MigrationConfig(
            source_org="source-org",
            source_repo="source-repo",
            target_org="target-org",
            target_repo="target-repo",
            source_pat="test-pat",
            target_pat="test-pat",
        )
        assert config.source_org == "source-org"
        assert config.source_repo == "source-repo"
        assert config.target_org == "target-org"
        assert config.target_repo == "target-repo"
        assert config.org_to_org is False
        assert config.skip_envs is False

    def test_config_org_to_org(self):
        """Test org-to-org configuration."""
        config = MigrationConfig(
            source_org="source-org",
            source_repo="source-repo",
            target_org="target-org",
            source_pat="test-pat",
            target_pat="test-pat",
            org_to_org=True,
        )
        assert config.org_to_org is True
        # target_repo defaults to empty string when not provided
        assert config.target_repo == ""

    def test_config_skip_envs(self):
        """Test skip_envs configuration."""
        config = MigrationConfig(
            source_org="source-org",
            source_repo="source-repo",
            target_org="target-org",
            target_repo="target-repo",
            source_pat="test-pat",
            target_pat="test-pat",
            skip_envs=True,
        )
        assert config.skip_envs is True

    def test_config_verbose(self):
        """Test verbose configuration."""
        config = MigrationConfig(
            source_org="source-org",
            source_repo="source-repo",
            target_org="target-org",
            target_repo="target-repo",
            source_pat="test-pat",
            target_pat="test-pat",
            verbose=True,
        )
        assert config.verbose is True

    def test_config_all_flags(self):
        """Test configuration with all flags set."""
        config = MigrationConfig(
            source_org="source-org",
            source_repo="source-repo",
            target_org="target-org",
            target_repo="target-repo",
            source_pat="source-token",
            target_pat="target-token",
            verbose=True,
            skip_envs=True,
            org_to_org=False,
        )
        assert config.source_org == "source-org"
        assert config.source_repo == "source-repo"
        assert config.target_org == "target-org"
        assert config.target_repo == "target-repo"
        assert config.source_pat == "source-token"
        assert config.target_pat == "target-token"
        assert config.verbose is True
        assert config.skip_envs is True
        assert config.org_to_org is False
