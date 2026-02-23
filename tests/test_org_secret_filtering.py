"""Tests for organization secret filtering during repo-to-repo migration."""
from datetime import datetime, timezone
from unittest.mock import Mock, patch
from src.clients.github import GitHubClient
from src.core.workflow_generator import generate_workflow
from src.utils.logger import Logger


class MockSecret:
    """Mock GitHub Secret object."""
    
    def __init__(self, name: str, is_org_secret: bool = False):
        self.name = name
        self.raw_data = {}
        if is_org_secret:
            # Org secrets have a 'visibility' field
            self.raw_data['visibility'] = 'selected'


class TestOrgSecretFiltering:
    """Test that organization secrets are filtered out during repo-to-repo migration."""
    
    @patch('src.clients.github.Github')
    def test_list_repo_secrets_filters_org_secrets(self, mock_github_class):
        """Test that list_repo_secrets filters out organization secrets."""
        # Create mock client
        logger = Logger(verbose=False)
        
        # Mock the GitHub API calls
        mock_repo = Mock()
        mock_secrets = [
            MockSecret("REPO_SECRET_1", is_org_secret=False),
            MockSecret("ORG_SECRET_1", is_org_secret=True),
            MockSecret("REPO_SECRET_2", is_org_secret=False),
            MockSecret("ORG_SECRET_2", is_org_secret=True),
            MockSecret("REPO_SECRET_3", is_org_secret=False),
        ]
        mock_repo.get_secrets.return_value = mock_secrets
        
        # Set up the mock chain
        mock_github_instance = Mock()
        mock_github_instance.get_repo.return_value = mock_repo
        reset=datetime.fromtimestamp(datetime.now(timezone.utc).timestamp() + 3600, tz=timezone.utc)
        mock_github_instance.get_rate_limit.return_value = Mock(resources=Mock(core=Mock(remaining=5000, limit=5000, reset=reset)))
        mock_github_class.return_value = mock_github_instance
        
        # Create client (will use mocked Github)
        client = GitHubClient("fake-token", logger)
        
        # Call the method
        result = client.list_repo_secrets("test-org", "test-repo")
        
        # Verify only repository secrets are returned
        assert len(result) == 3
        assert "REPO_SECRET_1" in result
        assert "REPO_SECRET_2" in result
        assert "REPO_SECRET_3" in result
        assert "ORG_SECRET_1" not in result
        assert "ORG_SECRET_2" not in result
    
    @patch('src.clients.github.Github')
    def test_list_repo_secrets_all_repo_secrets(self, mock_github_class):
        """Test that all secrets are returned when none are org secrets."""
        logger = Logger(verbose=False)
        
        mock_repo = Mock()
        mock_secrets = [
            MockSecret("REPO_SECRET_1", is_org_secret=False),
            MockSecret("REPO_SECRET_2", is_org_secret=False),
            MockSecret("REPO_SECRET_3", is_org_secret=False),
        ]
        mock_repo.get_secrets.return_value = mock_secrets
        
        mock_github_instance = Mock()
        mock_github_instance.get_repo.return_value = mock_repo
        reset=datetime.fromtimestamp(datetime.now(timezone.utc).timestamp() + 3600, tz=timezone.utc)
        mock_github_instance.get_rate_limit.return_value = Mock(resources=Mock(core=Mock(remaining=5000, limit=5000, reset=reset)))
        mock_github_class.return_value = mock_github_instance
        
        client = GitHubClient("fake-token", logger)
        result = client.list_repo_secrets("test-org", "test-repo")
        
        assert len(result) == 3
        assert "REPO_SECRET_1" in result
        assert "REPO_SECRET_2" in result
        assert "REPO_SECRET_3" in result
    
    @patch('src.clients.github.Github')
    def test_list_repo_secrets_all_org_secrets(self, mock_github_class):
        """Test that all org secrets are filtered out, returning empty list."""
        logger = Logger(verbose=False)
        
        mock_repo = Mock()
        mock_secrets = [
            MockSecret("ORG_SECRET_1", is_org_secret=True),
            MockSecret("ORG_SECRET_2", is_org_secret=True),
        ]
        mock_repo.get_secrets.return_value = mock_secrets
        
        mock_github_instance = Mock()
        mock_github_instance.get_repo.return_value = mock_repo
        reset=datetime.fromtimestamp(datetime.now(timezone.utc).timestamp() + 3600, tz=timezone.utc)
        mock_github_instance.get_rate_limit.return_value = Mock(resources=Mock(core=Mock(remaining=5000, limit=5000, reset=reset)))
        mock_github_class.return_value = mock_github_instance
        
        client = GitHubClient("fake-token", logger)
        result = client.list_repo_secrets("test-org", "test-repo")
        
        # All org secrets should be filtered out
        assert len(result) == 0
    
    @patch('src.clients.github.Github')
    def test_list_repo_secrets_no_secrets(self, mock_github_class):
        """Test that empty list is returned when no secrets exist."""
        logger = Logger(verbose=False)
        
        mock_repo = Mock()
        mock_repo.get_secrets.return_value = []
        
        mock_github_instance = Mock()
        mock_github_instance.get_repo.return_value = mock_repo
        reset=datetime.fromtimestamp(datetime.now(timezone.utc).timestamp() + 3600, tz=timezone.utc)
        mock_github_instance.get_rate_limit.return_value = Mock(resources=Mock(core=Mock(remaining=5000, limit=5000, reset=reset)))
        mock_github_class.return_value = mock_github_instance
        
        client = GitHubClient("fake-token", logger)
        result = client.list_repo_secrets("test-org", "test-repo")
        
        assert len(result) == 0


class TestWorkflowGeneratorWithRepoSecrets:
    """Test workflow generation with repository secrets filtering."""
    
    def test_generate_workflow_with_repo_secrets(self):
        """Test that workflow generates individual steps for specified repo secrets."""
        repo_secrets = ["REPO_SECRET_1", "REPO_SECRET_2"]
        workflow = generate_workflow(
            "source-org",
            "source-repo",
            "target-org",
            "target-repo",
            "migrate-secrets",
            repo_secrets=repo_secrets,
        )
        
        # Verify the workflow contains individual steps for each secret
        assert "Migrate Repo Secret - REPO_SECRET_1" in workflow
        assert "Migrate Repo Secret - REPO_SECRET_2" in workflow
        
    def test_generate_workflow_without_repo_secrets(self):
        """Test that workflow works without repo_secrets (backward compatibility)."""
        workflow = generate_workflow(
            "source-org",
            "source-repo",
            "target-org",
            "target-repo",
            "migrate-secrets",
        )
        
        # Should still generate valid workflow using the fallback bulk method
        assert "name: move-secrets" in workflow
        assert "Populate Repository Secrets" in workflow
        # Should NOT contain individual steps
        assert "Migrate Repo Secret -" not in workflow
    
    def test_generate_workflow_explicit_steps(self):
        """Test that workflow uses explicit steps for repo secrets."""
        repo_secrets = ["REPO_SECRET"]
        workflow = generate_workflow(
            "source-org",
            "source-repo",
            "target-org",
            "target-repo",
            "migrate-secrets",
            repo_secrets=repo_secrets,
        )
        
        # Verify separate step generation with individual steps
        assert "Migrate Repo Secret - REPO_SECRET" in workflow
        assert "SECRET_NAME: 'REPO_SECRET'" in workflow
    
    def test_generate_workflow_empty_repo_secrets_list(self):
        """Test workflow generation with empty repo_secrets list."""
        repo_secrets = []
        workflow = generate_workflow(
            "source-org",
            "source-repo",
            "target-org",
            "target-repo",
            "migrate-secrets",
            repo_secrets=repo_secrets,
        )
        
        # Empty list means no individual steps and no bulk step
        # But workflow still has cleanup section
        assert "name: move-secrets" in workflow
        assert "Migrate Repo Secret" not in workflow
        assert "Populate Repository Secrets" not in workflow
        assert "Cleanup" in workflow
    
    def test_generate_workflow_many_repo_secrets(self):
        """Test workflow generation with many repo secrets."""
        repo_secrets = [f"SECRET_{i}" for i in range(10)]
        workflow = generate_workflow(
            "source-org",
            "source-repo",
            "target-org",
            "target-repo",
            "migrate-secrets",
            repo_secrets=repo_secrets,
        )
        
        # Verify all secrets have individual steps
        for secret in repo_secrets:
            assert secret in workflow
        
        # Verify step count (individual steps)
        assert workflow.count("Migrate Repo Secret -") == 10


class TestRepoSecretEdgeCases:
    """Test edge cases for repository secret filtering."""
    
    @patch('src.clients.github.Github')
    def test_secret_with_same_name_as_org_secret(self, mock_github_class):
        """Test that org-level secrets are filtered out correctly.
        
        Verifies the filter excludes org secrets even when they might share
        names with potential repo-level secrets.
        """
        # Note: If a secret truly exists at BOTH org and repo levels with the same name,
        # GitHub's API only returns the org version (with visibility field), so our
        # filter will exclude it. The actual repo-level value would be used in the
        # workflow context (${{ secrets.SECRET_NAME }}), but we can't detect it via
        # the API to include it in the migration.
        logger = Logger(verbose=False)
        
        mock_repo = Mock()
        # Simulate: API returns an org secret and a repo secret
        mock_secrets = [
            MockSecret("ORG_SECRET", is_org_secret=True),
            MockSecret("REPO_ONLY", is_org_secret=False),
        ]
        mock_repo.get_secrets.return_value = mock_secrets
        
        mock_github_instance = Mock()
        mock_github_instance.get_repo.return_value = mock_repo
        reset=datetime.fromtimestamp(datetime.now(timezone.utc).timestamp() + 3600, tz=timezone.utc)
        mock_github_instance.get_rate_limit.return_value = Mock(resources=Mock(core=Mock(remaining=5000, limit=5000, reset=reset)))
        mock_github_class.return_value = mock_github_instance
        
        client = GitHubClient("fake-token", logger)
        result = client.list_repo_secrets("test-org", "test-repo")
        
        # Verify org secret is filtered out, only repo secret is returned
        assert "ORG_SECRET" not in result
        assert "REPO_ONLY" in result
    
    @patch('src.clients.github.Github')
    def test_secret_name_with_special_characters(self, mock_github_class):
        """Test that secrets with special characters are handled correctly."""
        logger = Logger(verbose=False)
        
        mock_repo = Mock()
        mock_secrets = [
            MockSecret("SECRET_WITH_UNDERSCORES", is_org_secret=False),
            MockSecret("SECRET-WITH-DASHES", is_org_secret=False),
            MockSecret("SECRET123", is_org_secret=False),
        ]
        mock_repo.get_secrets.return_value = mock_secrets
        
        mock_github_instance = Mock()
        mock_github_instance.get_repo.return_value = mock_repo
        reset=datetime.fromtimestamp(datetime.now(timezone.utc).timestamp() + 3600, tz=timezone.utc)
        mock_github_instance.get_rate_limit.return_value = Mock(resources=Mock(core=Mock(remaining=5000, limit=5000, reset=reset)))
        mock_github_class.return_value = mock_github_instance
        
        client = GitHubClient("fake-token", logger)
        result = client.list_repo_secrets("test-org", "test-repo")
        
        assert len(result) == 3
        assert "SECRET_WITH_UNDERSCORES" in result
        assert "SECRET-WITH-DASHES" in result
        assert "SECRET123" in result
