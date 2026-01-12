"""Tests for workflow generation module."""
from src.core.workflow_generator import (
    generate_environment_secret_steps,
    generate_org_secret_steps,
    generate_workflow,
)


class TestWorkflowGenerator:
    """Test cases for workflow generation."""

    def test_generate_environment_secret_steps_single(self):
        """Test generating workflow steps for a single environment secret."""
        env_secrets = {"production": ["DB_PASSWORD"]}
        steps = generate_environment_secret_steps(
            env_secrets, "source-org", "source-repo", "target-org", "target-repo"
        )
        assert "DB_PASSWORD" in steps
        assert "production" in steps
        assert "target-org" in steps
        assert "target-repo" in steps

    def test_generate_environment_secret_steps_multiple_envs(self):
        """Test generating workflow steps for multiple environments."""
        env_secrets = {
            "production": ["DB_PASSWORD", "API_KEY"],
            "staging": ["DB_PASSWORD"],
        }
        steps = generate_environment_secret_steps(
            env_secrets, "source-org", "source-repo", "target-org", "target-repo"
        )
        assert "production" in steps
        assert "staging" in steps
        assert steps.count("Migrate") == 3  # 3 secrets total

    def test_generate_environment_secret_steps_empty(self):
        """Test generating workflow steps with no environment secrets."""
        env_secrets = {}
        steps = generate_environment_secret_steps(
            env_secrets, "source-org", "source-repo", "target-org", "target-repo"
        )
        assert steps == ""

    def test_generate_org_secret_steps_single(self):
        """Test generating org secret workflow steps."""
        org_secrets = ["DB_PASSWORD"]
        steps = generate_org_secret_steps(org_secrets, "target-org")
        assert "DB_PASSWORD" in steps
        assert "target-org" in steps
        assert "organization secret" in steps.lower()

    def test_generate_org_secret_steps_multiple(self):
        """Test generating multiple org secret workflow steps."""
        org_secrets = ["DB_PASSWORD", "API_KEY", "DEPLOY_TOKEN"]
        steps = generate_org_secret_steps(org_secrets, "target-org")
        assert "DB_PASSWORD" in steps
        assert "API_KEY" in steps
        assert "DEPLOY_TOKEN" in steps
        assert steps.count("Migrate Org Secret") == 3

    def test_generate_workflow_repo_to_repo(self):
        """Test generating a complete repo-to-repo workflow."""
        workflow = generate_workflow(
            "source-org",
            "source-repo",
            "target-org",
            "target-repo",
            "migrate-secrets",
        )
        assert "name: move-secrets" in workflow
        assert "migrate-repo-secrets" in workflow
        assert "migrate-secrets" in workflow
        assert "ubuntu-latest" in workflow

    def test_generate_workflow_with_env_secrets(self):
        """Test generating workflow with environment secrets."""
        env_secrets = {"production": ["DB_PASSWORD"]}
        workflow = generate_workflow(
            "source-org",
            "source-repo",
            "target-org",
            "target-repo",
            "migrate-secrets",
            env_secrets=env_secrets,
        )
        assert "production" in workflow
        assert "DB_PASSWORD" in workflow

    def test_generate_workflow_with_org_secrets(self):
        """Test generating workflow with organization secrets."""
        org_secrets = ["ORG_SECRET"]
        workflow = generate_workflow(
            "source-org",
            "source-repo",
            "target-org",
            "target-repo",
            "migrate-secrets",
            org_secrets=org_secrets,
        )
        assert "ORG_SECRET" in workflow
        assert "organization" in workflow.lower()

    def test_generate_workflow_cleanup_section(self):
        """Test that generated workflow includes cleanup section."""
        workflow = generate_workflow(
            "source-org",
            "source-repo",
            "target-org",
            "target-repo",
            "migrate-secrets",
        )
        assert "Cleanup" in workflow
        assert "SECRETS_MIGRATOR_TARGET_PAT" in workflow
        assert "SECRETS_MIGRATOR_SOURCE_PAT" in workflow
        assert "always()" in workflow

    def test_generate_org_secret_steps_with_visibility_all(self):
        """Test generating org secret steps with 'all' visibility."""
        org_secrets = ["SECRET1"]
        visibility_map = {
            "SECRET1": {"visibility": "all", "repos": []}
        }
        steps = generate_org_secret_steps(org_secrets, "target-org", visibility_map)
        assert "SECRET1" in steps
        assert "VISIBILITY: 'all'" in steps
        assert "--visibility" in steps

    def test_generate_org_secret_steps_with_visibility_private(self):
        """Test generating org secret steps with 'private' visibility."""
        org_secrets = ["SECRET1"]
        visibility_map = {
            "SECRET1": {"visibility": "private", "repos": []}
        }
        steps = generate_org_secret_steps(org_secrets, "target-org", visibility_map)
        assert "SECRET1" in steps
        assert "VISIBILITY: 'private'" in steps

    def test_generate_org_secret_steps_with_visibility_selected(self):
        """Test generating org secret steps with 'selected' visibility."""
        org_secrets = ["SECRET1"]
        visibility_map = {
            "SECRET1": {"visibility": "selected", "repos": ["repo1", "repo2"]}
        }
        steps = generate_org_secret_steps(org_secrets, "target-org", visibility_map)
        assert "SECRET1" in steps
        assert "selected repos" in steps.lower()
        assert "repo1" in steps
        assert "repo2" in steps
        assert "SELECTED_REPOS" in steps

    def test_generate_org_secret_steps_mixed_visibility(self):
        """Test generating org secret steps with mixed visibility settings."""
        org_secrets = ["SECRET1", "SECRET2", "SECRET3"]
        visibility_map = {
            "SECRET1": {"visibility": "all", "repos": []},
            "SECRET2": {"visibility": "selected", "repos": ["repo1"]},
            "SECRET3": {"visibility": "private", "repos": []}
        }
        steps = generate_org_secret_steps(org_secrets, "target-org", visibility_map)
        assert "SECRET1" in steps
        assert "SECRET2" in steps
        assert "SECRET3" in steps
        assert steps.count("Migrate Org Secret") == 3
        # Check that SECRET2 has selected repos handling
        assert "selected repos" in steps.lower()
        assert "repo1" in steps

    def test_generate_workflow_with_org_secret_visibility(self):
        """Test generating complete workflow with org secret visibility."""
        org_secrets = ["SECRET1", "SECRET2"]
        visibility_map = {
            "SECRET1": {"visibility": "all", "repos": []},
            "SECRET2": {"visibility": "selected", "repos": ["repo1", "repo2"]}
        }
        workflow = generate_workflow(
            "source-org",
            "source-repo",
            "target-org",
            "target-repo",
            "migrate-org-secrets",
            org_secrets=org_secrets,
            org_secret_visibility=visibility_map
        )
        assert "SECRET1" in workflow
        assert "SECRET2" in workflow
        assert "VISIBILITY: 'all'" in workflow
        assert "selected repos" in workflow.lower()
        assert "repo1" in workflow
        assert "repo2" in workflow

    def test_generate_org_secret_steps_no_visibility_map(self):
        """Test generating org secret steps without visibility map (backwards compatibility)."""
        org_secrets = ["SECRET1", "SECRET2"]
        steps = generate_org_secret_steps(org_secrets, "target-org", None)
        assert "SECRET1" in steps
        assert "SECRET2" in steps
        # Should default to 'all' visibility
        assert "VISIBILITY: 'all'" in steps
