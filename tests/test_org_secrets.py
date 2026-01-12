"""Tests for organization secrets migration."""
import pytest
from src.core.workflow_generator import generate_org_secret_steps, generate_workflow


class TestOrgSecretsMigration:
    """Test cases for organization secrets migration functionality."""

    def test_org_secret_workflow_uses_org_flag(self):
        """Verify that org secret workflow uses --org flag, not --repo flag."""
        org_secrets = ["ORG_DB_PASSWORD", "ORG_API_KEY"]
        workflow_steps = generate_org_secret_steps(org_secrets, "target-org")
        
        # Verify that --org flag is used (not --repo)
        assert "--org" in workflow_steps
        # The workflow uses --org "$TARGET_ORG" where TARGET_ORG env var contains the org name
        assert '--org "$TARGET_ORG"' in workflow_steps
        
        # Verify that --repo flag is NOT used for org secrets
        assert "--repo" not in workflow_steps
        
        # Verify correct secret names are present
        assert "ORG_DB_PASSWORD" in workflow_steps
        assert "ORG_API_KEY" in workflow_steps

    def test_org_secret_workflow_creates_at_org_level(self):
        """Verify workflow creates secrets at organization level, not repository level."""
        org_secrets = ["DEPLOY_TOKEN"]
        workflow_steps = generate_org_secret_steps(org_secrets, "my-target-org")
        
        # The gh CLI command should be: gh secret set <name> --body <value> --org <org>
        # This creates an ORGANIZATION secret, not a repository secret
        assert "gh secret set" in workflow_steps
        assert "--org" in workflow_steps
        assert "my-target-org" in workflow_steps
        
        # Should NOT have --repo flag which would create a repo secret
        assert "--repo" not in workflow_steps

    def test_org_secret_reads_from_workflow_secrets_context(self):
        """Verify that org secrets are read from workflow secrets context.
        
        Note: This requires the org secrets to be shared with the repository
        running the workflow. If not shared, the workflow will receive empty values.
        """
        org_secrets = ["SHARED_SECRET"]
        workflow_steps = generate_org_secret_steps(org_secrets, "target-org")
        
        # Verify workflow tries to read from secrets context
        assert "secrets.SHARED_SECRET" in workflow_steps
        assert "SECRET_VALUE:" in workflow_steps

    def test_full_org_to_org_workflow_structure(self):
        """Test complete org-to-org workflow structure."""
        org_secrets = ["ORG_SECRET_1", "ORG_SECRET_2"]
        workflow = generate_workflow(
            "source-org",
            "source-repo",
            "target-org",
            "target-repo",
            "migrate-org-secrets",
            env_secrets=None,
            org_secrets=org_secrets,
        )
        
        # Verify workflow contains org secret migration steps
        assert "ORG_SECRET_1" in workflow
        assert "ORG_SECRET_2" in workflow
        
        # Verify --org flag is used
        assert "--org" in workflow
        assert "target-org" in workflow
        
        # Verify cleanup section exists
        assert "Cleanup" in workflow
        assert "SECRETS_MIGRATOR_TARGET_PAT" in workflow
        assert "SECRETS_MIGRATOR_SOURCE_PAT" in workflow

    def test_org_secrets_not_mixed_with_repo_secrets(self):
        """Verify org secrets workflow doesn't include repository secret steps."""
        org_secrets = ["ORG_SECRET"]
        workflow = generate_workflow(
            "source-org",
            "source-repo",
            "target-org",
            "target-repo",
            "migrate-org-secrets",
            env_secrets=None,
            org_secrets=org_secrets,
        )
        
        # Should not contain "Populate Repository Secrets" step
        assert "Populate Repository Secrets" not in workflow
        
        # Should contain org-specific language
        assert "organization secret" in workflow.lower() or "org secret" in workflow.lower()

    def test_org_secret_gh_cli_command_syntax(self):
        """Verify the exact gh CLI command syntax for creating org secrets."""
        org_secrets = ["TEST_SECRET"]
        workflow_steps = generate_org_secret_steps(org_secrets, "my-org")
        
        # The command should follow this pattern:
        # gh secret set "$SECRET_NAME" --body "$SECRET_VALUE" --org "$TARGET_ORG"
        
        # Check each component exists
        assert 'gh secret set "$SECRET_NAME"' in workflow_steps
        assert '--body "$SECRET_VALUE"' in workflow_steps
        assert '--org "$TARGET_ORG"' in workflow_steps
        
        # Verify the order is correct (set, then --body, then --org)
        set_pos = workflow_steps.find("gh secret set")
        body_pos = workflow_steps.find("--body")
        org_pos = workflow_steps.find("--org")
        
        assert set_pos < body_pos < org_pos, "Command components should be in correct order"

    def test_org_secrets_require_sharing_with_repo(self):
        """Document the requirement that org secrets must be shared with the source repo.
        
        This is a documentation test to clarify the behavior:
        - Org secrets can only be accessed in workflows if they're shared with the repo
        - If not shared, the workflow will receive empty values
        - This is GitHub's security model, not a bug in our code
        """
        org_secrets = ["UNSHARED_SECRET"]
        workflow_steps = generate_org_secret_steps(org_secrets, "target-org")
        
        # The workflow WILL try to read the secret
        assert "secrets.UNSHARED_SECRET" in workflow_steps
        
        # But if the secret isn't shared with the repo, it will be empty
        # This is expected GitHub behavior
        # Users must ensure org secrets are shared with the source repository
        
        # The workflow should still attempt to create it in target org
        assert "--org" in workflow_steps
        assert "target-org" in workflow_steps

    def test_multiple_org_secrets_each_get_own_step(self):
        """Verify each org secret gets its own migration step."""
        org_secrets = ["SECRET_1", "SECRET_2", "SECRET_3"]
        workflow_steps = generate_org_secret_steps(org_secrets, "target-org")
        
        # Should have 3 separate steps
        assert workflow_steps.count("- name: Migrate Org Secret") == 3
        
        # Each secret should be named in a step
        assert "SECRET_1" in workflow_steps
        assert "SECRET_2" in workflow_steps
        assert "SECRET_3" in workflow_steps
        
        # Each step should set the secret
        assert workflow_steps.count("gh secret set") == 3
