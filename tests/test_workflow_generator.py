"""Tests for workflow generation module."""
from src.core.workflow_generator import (
    generate_environment_secret_steps,
    generate_environment_secret_jobs,
    generate_org_secret_steps,
    generate_repo_secret_steps,
    generate_workflow,
    sanitize_job_id,
)


class TestSanitizeJobId:
    """Test cases for sanitize_job_id."""

    def test_simple_name(self):
        assert sanitize_job_id("production") == "production"

    def test_name_with_spaces(self):
        assert sanitize_job_id("prod env") == "prod-env"

    def test_name_with_special_chars(self):
        assert sanitize_job_id("my.env/test") == "my-env-test"

    def test_numeric_start(self):
        result = sanitize_job_id("123")
        assert result[0].isalpha() or result[0] == '_'

    def test_already_valid(self):
        assert sanitize_job_id("my-env_1") == "my-env_1"


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

    def test_generate_environment_secret_jobs_single(self):
        """Test generating a single environment job."""
        env_secrets = {"production": ["DB_PASSWORD"]}
        jobs_yaml, last_ids = generate_environment_secret_jobs(
            env_secrets, "source-org", "source-repo", "target-org", "target-repo"
        )
        assert "environment: production" in jobs_yaml
        assert "needs: [migrate-repo-secrets]" in jobs_yaml
        assert "DB_PASSWORD" in jobs_yaml
        assert "migrate-env-production" in jobs_yaml
        assert last_ids == ["migrate-env-production"]

    def test_generate_environment_secret_jobs_multiple_envs(self):
        """Test generating separate jobs for multiple environments."""
        env_secrets = {
            "production": ["DB_PASSWORD"],
            "staging": ["API_KEY"],
        }
        jobs_yaml, last_ids = generate_environment_secret_jobs(
            env_secrets, "source-org", "source-repo", "target-org", "target-repo"
        )
        assert "environment: production" in jobs_yaml
        assert "environment: staging" in jobs_yaml
        assert "migrate-env-production" in jobs_yaml
        assert "migrate-env-staging" in jobs_yaml
        # Both in same batch (< 5), so both need migrate-repo-secrets
        assert jobs_yaml.count("needs: [migrate-repo-secrets]") == 2

    def test_generate_environment_secret_jobs_empty(self):
        """Test generating jobs with no environment secrets."""
        jobs_yaml, last_ids = generate_environment_secret_jobs(
            {}, "source-org", "source-repo", "target-org", "target-repo"
        )
        assert jobs_yaml == ""
        assert last_ids == []

    def test_generate_environment_secret_jobs_envs_with_no_secrets(self):
        """Test that environments with empty secret lists produce no jobs."""
        env_secrets = {"production": [], "staging": []}
        jobs_yaml, last_ids = generate_environment_secret_jobs(
            env_secrets, "source-org", "source-repo", "target-org", "target-repo"
        )
        assert jobs_yaml == ""
        assert last_ids == []

    def test_generate_environment_secret_jobs_mixed_empty_and_populated(self):
        """Test that only environments with secrets get jobs."""
        env_secrets = {"production": ["DB_PASSWORD"], "staging": []}
        jobs_yaml, last_ids = generate_environment_secret_jobs(
            env_secrets, "source-org", "source-repo", "target-org", "target-repo"
        )
        assert "environment: production" in jobs_yaml
        assert "staging" not in jobs_yaml
        assert last_ids == ["migrate-env-production"]

    def test_generate_environment_secret_jobs_batched(self):
        """Test that >5 environments are batched into groups of 5."""
        env_secrets = {f"env-{i}": [f"SECRET_{i}"] for i in range(7)}
        jobs_yaml, last_ids = generate_environment_secret_jobs(
            env_secrets, "org", "repo", "target-org", "target-repo"
        )
        # First 5 envs should need migrate-repo-secrets
        assert jobs_yaml.count("needs: [migrate-repo-secrets]") == 5
        # Last 2 envs should need all 5 from batch 1
        assert len(last_ids) == 2
        # Batch 2 jobs should NOT need migrate-repo-secrets directly
        for job_id in last_ids:
            job_start = jobs_yaml.index(f"  {job_id}:")
            job_section = jobs_yaml[job_start:job_start + 500]
            assert "migrate-repo-secrets" not in job_section

    def test_generate_environment_secret_jobs_exact_batch_size(self):
        """Test exactly 5 environments (single full batch)."""
        env_secrets = {f"env-{i}": [f"SECRET_{i}"] for i in range(5)}
        jobs_yaml, last_ids = generate_environment_secret_jobs(
            env_secrets, "org", "repo", "target-org", "target-repo"
        )
        assert len(last_ids) == 5
        assert jobs_yaml.count("needs: [migrate-repo-secrets]") == 5

    def test_generate_environment_secret_jobs_custom_batch_size(self):
        """Test custom batch size."""
        env_secrets = {f"env-{i}": [f"SECRET_{i}"] for i in range(4)}
        jobs_yaml, last_ids = generate_environment_secret_jobs(
            env_secrets, "org", "repo", "target-org", "target-repo",
            batch_size=2
        )
        # Batch 1: env-0, env-1 (need migrate-repo-secrets)
        assert jobs_yaml.count("needs: [migrate-repo-secrets]") == 2
        # Batch 2: env-2, env-3 (need batch 1 IDs)
        assert len(last_ids) == 2

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

    def test_generate_repo_secret_steps_skip_overwrite_enabled(self):
        """Test repo secret steps include existence check when skip_overwrite is enabled."""
        steps = generate_repo_secret_steps(
            ["DB_PASSWORD"],
            "target-org",
            "target-repo",
            skip_overwrite=True,
        )
        assert "repos/$TARGET_ORG/$TARGET_REPO/actions/secrets/$SECRET_NAME" in steps
        assert "Skipping 'D B _ P A S S W O R D' because it already exists in target repo" in steps

    def test_generate_repo_secret_steps_skip_overwrite_disabled(self):
        """Test repo secret steps do not include existence check when skip_overwrite is disabled."""
        steps = generate_repo_secret_steps(
            ["DB_PASSWORD"],
            "target-org",
            "target-repo",
        )
        assert "if false && gh api \"repos/$TARGET_ORG/$TARGET_REPO/actions/secrets/$SECRET_NAME\"" in steps

    def test_generate_org_secret_steps_skip_overwrite_enabled(self):
        """Test org secret steps include existence check when skip_overwrite is enabled."""
        steps = generate_org_secret_steps(
            ["ORG_SECRET"],
            "target-org",
            skip_overwrite=True,
        )
        assert "orgs/$TARGET_ORG/actions/secrets/$SECRET_NAME" in steps
        assert "already exists in target organization" in steps

    def test_generate_environment_secret_steps_skip_overwrite_enabled(self):
        """Test environment secret steps include existence check when skip_overwrite is enabled."""
        env_secrets = {"production": ["DB_PASSWORD"]}
        steps = generate_environment_secret_steps(
            env_secrets,
            "source-org",
            "source-repo",
            "target-org",
            "target-repo",
            skip_overwrite=True,
        )
        assert "environments/$ENVIRONMENT/secrets/$SECRET_NAME" in steps
        assert "already exists" in steps

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
        """Test generating workflow with environment secrets as separate jobs."""
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
        # Environment should be a job-level key
        assert "environment: production" in workflow
        # Should be a separate job
        assert "migrate-env-production" in workflow

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
        """Test that generated workflow includes cleanup as a separate job."""
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

    def test_generate_workflow_bulk_repo_mode_skip_overwrite_enabled(self):
        """Test bulk repo migration includes skip overwrite check when enabled."""
        workflow = generate_workflow(
            "source-org",
            "source-repo",
            "target-org",
            "target-repo",
            "migrate-secrets",
            repo_secrets=None,
            skip_overwrite=True,
        )
        assert "if true && gh api \"repos/$TARGET_ORG/$TARGET_REPO/actions/secrets/$SECRET_NAME\"" in workflow

    def test_generate_workflow_cleanup_needs_env_jobs(self):
        """Test that cleanup job needs all env secret jobs."""
        env_secrets = {
            "production": ["DB_PASSWORD"],
            "staging": ["API_KEY"],
        }
        workflow = generate_workflow(
            "org", "repo", "target", "target", "branch",
            env_secrets=env_secrets,
        )
        assert "cleanup:" in workflow
        assert "migrate-env-production" in workflow
        assert "migrate-env-staging" in workflow

    def test_generate_workflow_no_env_secrets(self):
        """Test that workflow without env secrets has cleanup needing repo secrets job."""
        workflow = generate_workflow(
            "org", "repo", "target", "target", "branch",
        )
        assert "cleanup:" in workflow
        assert "needs: [migrate-repo-secrets]" in workflow
