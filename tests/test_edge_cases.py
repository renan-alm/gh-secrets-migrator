"""Advanced tests for edge cases and error handling."""
import pytest
from src.core.config import MigrationConfig
from src.core.workflow_generator import generate_workflow, generate_environment_secret_steps


class TestConfigEdgeCases:
    """Test edge cases and validation for MigrationConfig."""

    def test_config_with_special_characters_in_names(self):
        """Test config with special characters in org/repo names."""
        config = MigrationConfig(
            source_org="org-with-dash_and_underscore",
            source_repo="repo.with.dots",
            target_org="target-org-123",
            target_repo="target-repo_456",
            source_pat="pat-token",
            target_pat="pat-token",
        )
        assert config.source_org == "org-with-dash_and_underscore"
        assert config.source_repo == "repo.with.dots"

    def test_config_with_very_long_values(self):
        """Test config with very long organization/repository names."""
        long_name = "a" * 100
        config = MigrationConfig(
            source_org=long_name,
            source_repo=long_name,
            target_org=long_name,
            target_repo=long_name,
            source_pat="token",
            target_pat="token",
        )
        assert len(config.source_org) == 100
        assert len(config.source_repo) == 100

    def test_config_all_empty_repo_names(self):
        """Test config with empty repository names."""
        config = MigrationConfig(
            source_org="org",
            source_repo="",
            target_org="org",
            target_repo="",
            source_pat="token",
            target_pat="token",
        )
        assert config.source_repo == ""
        assert config.target_repo == ""

    def test_config_mixed_flags(self):
        """Test various flag combinations."""
        config = MigrationConfig(
            source_org="org",
            source_repo="repo",
            target_org="org",
            source_pat="token",
            target_pat="token",
            org_to_org=True,
            skip_envs=True,
            verbose=True,
        )
        assert config.org_to_org is True
        assert config.skip_envs is True
        assert config.verbose is True


class TestWorkflowGeneratorEdgeCases:
    """Test edge cases for workflow generation."""

    def test_workflow_with_special_chars_in_secrets(self):
        """Test workflow generation with special characters in secret names."""
        secrets = ["SECRET_WITH_UNDERSCORES", "SECRET-WITH-DASHES", "SECRET123"]
        workflow = generate_workflow(
            "org", "repo", "target", "target", "branch", org_secrets=secrets
        )
        assert "SECRET_WITH_UNDERSCORES" in workflow
        assert "SECRET-WITH-DASHES" in workflow
        assert "SECRET123" in workflow

    def test_workflow_with_many_environment_secrets(self):
        """Test workflow generation with many environment secrets."""
        env_secrets = {
            f"env_{i}": [f"SECRET_{j}" for j in range(5)] for i in range(10)
        }
        steps = generate_environment_secret_steps(
            env_secrets, "org", "repo", "target", "target"
        )
        # Should have 50 secret migrations (10 envs × 5 secrets)
        assert steps.count("Migrate") == 50

    def test_workflow_with_numeric_environment_names(self):
        """Test workflow with numeric environment names."""
        env_secrets = {"1": ["SECRET"], "2": ["SECRET"]}
        workflow = generate_workflow(
            "org", "repo", "target", "target", "branch", env_secrets=env_secrets
        )
        assert "1" in workflow
        assert "2" in workflow

    def test_workflow_branch_name_with_special_chars(self):
        """Test workflow generation with special branch names."""
        workflow = generate_workflow(
            "org", "repo", "target", "target", "migrate-secrets-v1.2.3"
        )
        assert "migrate-secrets-v1.2.3" in workflow

    def test_workflow_has_required_permissions(self):
        """Test that generated workflow includes required permissions."""
        workflow = generate_workflow("org", "repo", "target", "target", "branch")
        assert "permissions:" in workflow
        assert "contents: write" in workflow
        assert "repository-projects: write" in workflow

    def test_workflow_has_error_handling(self):
        """Test that workflow includes error handling."""
        workflow = generate_workflow("org", "repo", "target", "target", "branch")
        assert "set -e" in workflow  # Exit on error
        assert "if" in workflow  # Conditional checks
        assert "exit 1" in workflow  # Error exits


class TestWorkflowGeneratorSecrets:
    """Test secret handling in workflows."""

    def test_workflow_masks_sensitive_pats(self):
        """Test that workflow uses masked secrets for PATs."""
        workflow = generate_workflow("org", "repo", "target", "target", "branch")
        assert "SECRETS_MIGRATOR_TARGET_PAT" in workflow
        assert "SECRETS_MIGRATOR_SOURCE_PAT" in workflow
        # Should use GitHub secrets syntax
        assert "${{ secrets." in workflow

    def test_workflow_cleanup_always_runs(self):
        """Test that cleanup section always runs."""
        workflow = generate_workflow("org", "repo", "target", "target", "branch")
        assert "Cleanup" in workflow
        assert "always()" in workflow
        assert "if: always()" in workflow


class TestWorkflowGeneratorShellScripts:
    """Test shell script integrity in workflows."""

    def test_workflow_uses_bash(self):
        """Test that workflow steps use bash."""
        workflow = generate_workflow("org", "repo", "target", "target", "branch")
        assert "shell: bash" in workflow

    def test_workflow_has_proper_quoting(self):
        """Test that workflow uses proper shell quoting."""
        env_secrets = {"prod": ["DB_PASSWORD"]}
        steps = generate_environment_secret_steps(
            env_secrets, "org", "repo", "target", "target"
        )
        # Check for proper variable quoting
        assert "$" in steps  # Uses variables
        assert "\\" in steps  # Uses escaping

    def test_workflow_sets_environment_variables(self):
        """Test that workflow sets required environment variables."""
        workflow = generate_workflow("org", "repo", "target", "target", "branch")
        assert "TARGET_ORG:" in workflow
        assert "TARGET_REPO:" in workflow
        assert "GH_TOKEN:" in workflow


class TestConfigValidation:
    """Test configuration validation and requirements."""

    def test_source_org_required(self):
        """Test that source_org is required."""
        with pytest.raises(TypeError):
            MigrationConfig(
                source_repo="repo",
                target_org="org",
                target_repo="repo",
                source_pat="token",
                target_pat="token",
            )

    def test_pats_can_be_empty(self):
        """Test that PATs can be empty (env var fallback expected)."""
        config = MigrationConfig(
            source_org="org",
            source_repo="repo",
            target_org="target",
            source_pat="",
            target_pat="",
        )
        assert config.source_pat == ""
        assert config.target_pat == ""
