"""Tests for organization secret filtering during repo-to-repo migration."""
from datetime import datetime, timezone
from unittest.mock import Mock, patch
from src.clients.github import GitHubClient
from src.core.workflow_generator import generate_workflow
from src.utils.logger import Logger


def _make_secret_dict(name: str, is_org_secret: bool = False) -> dict:
    """Create a raw API secret dict as returned by GitHub REST API."""
    secret = {"name": name, "created_at": "2024-01-01T00:00:00Z", "updated_at": "2024-01-01T00:00:00Z"}
    if is_org_secret:
        secret["visibility"] = "selected"
    return secret


def _mock_raw_api(mock_repo, secrets: list[dict]) -> None:
    """Configure mock_repo._requester.requestJsonAndCheck to return secrets."""
    mock_requester = Mock()
    mock_requester.requestJsonAndCheck.return_value = ({}, {"secrets": secrets})
    mock_repo._requester = mock_requester


class TestOrgSecretFiltering:
    """Test that organization secrets are filtered out during repo-to-repo migration."""
    
    @patch('src.clients.github.Github')
    def test_list_repo_secrets_filters_org_secrets(self, mock_github_class):
        """Test that list_repo_secrets filters out organization secrets."""
        logger = Logger(verbose=False)
        
        mock_repo = Mock()
        _mock_raw_api(mock_repo, [
            _make_secret_dict("REPO_SECRET_1"),
            _make_secret_dict("ORG_SECRET_1", is_org_secret=True),
            _make_secret_dict("REPO_SECRET_2"),
            _make_secret_dict("ORG_SECRET_2", is_org_secret=True),
            _make_secret_dict("REPO_SECRET_3"),
        ])
        
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
        assert "ORG_SECRET_1" not in result
        assert "ORG_SECRET_2" not in result
    
    @patch('src.clients.github.Github')
    def test_list_repo_secrets_all_repo_secrets(self, mock_github_class):
        """Test that all secrets are returned when none are org secrets."""
        logger = Logger(verbose=False)
        
        mock_repo = Mock()
        _mock_raw_api(mock_repo, [
            _make_secret_dict("REPO_SECRET_1"),
            _make_secret_dict("REPO_SECRET_2"),
            _make_secret_dict("REPO_SECRET_3"),
        ])
        
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
        _mock_raw_api(mock_repo, [
            _make_secret_dict("ORG_SECRET_1", is_org_secret=True),
            _make_secret_dict("ORG_SECRET_2", is_org_secret=True),
        ])
        
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
        _mock_raw_api(mock_repo, [])
        
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
        _mock_raw_api(mock_repo, [
            _make_secret_dict("ORG_SECRET", is_org_secret=True),
            _make_secret_dict("REPO_ONLY"),
        ])
        
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
        _mock_raw_api(mock_repo, [
            _make_secret_dict("SECRET_WITH_UNDERSCORES"),
            _make_secret_dict("SECRET-WITH-DASHES"),
            _make_secret_dict("SECRET123"),
        ])
        
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


class TestIncompletableObjectHandling:
    """Regression tests for PyGithub IncompletableObject error.

    PyGithub 2.9.0's Secret class extends CompletableGithubObject. When the
    GitHub API response for repository secrets doesn't include a URL field,
    accessing properties like .name or .raw_data triggers lazy-loading which
    raises IncompletableObject(400).

    The fix uses raw API calls (requestJsonAndCheck) instead of PyGithub's
    Secret objects, completely bypassing the lazy-loading mechanism.

    These tests verify the fix works for the error reported in:
    https://github.com/renan-alm/gh-secrets-migrator/issues (IncompleteObject error)
    """

    @patch('src.clients.github.Github')
    def test_list_repo_secrets_succeeds_with_raw_api(self, mock_github_class):
        """Test that list_repo_secrets works by using raw API calls.

        The raw API approach avoids PyGithub's Secret objects entirely,
        preventing IncompletableObject errors.
        """
        logger = Logger(verbose=False)

        mock_repo = Mock()
        _mock_raw_api(mock_repo, [
            _make_secret_dict("SECRET_1"),
            _make_secret_dict("SECRET_2"),
        ])

        mock_github_instance = Mock()
        mock_github_instance.get_repo.return_value = mock_repo
        reset = datetime.fromtimestamp(datetime.now(timezone.utc).timestamp() + 3600, tz=timezone.utc)
        mock_github_instance.get_rate_limit.return_value = Mock(resources=Mock(core=Mock(remaining=5000, limit=5000, reset=reset)))
        mock_github_class.return_value = mock_github_instance

        client = GitHubClient("fake-token", logger)
        result = client.list_repo_secrets("Test-migration-repos", "test-mg-4")

        assert len(result) == 2
        assert "SECRET_1" in result
        assert "SECRET_2" in result

    @patch('src.clients.github.Github')
    def test_list_repo_secrets_filters_org_secrets_with_raw_api(self, mock_github_class):
        """Test that org secret filtering works correctly with raw API.

        Verifies that the raw API approach still correctly filters out
        organization secrets based on the 'visibility' field.
        """
        logger = Logger(verbose=False)

        mock_repo = Mock()
        _mock_raw_api(mock_repo, [
            _make_secret_dict("GOOD_SECRET_1"),
            _make_secret_dict("ORG_SECRET", is_org_secret=True),
            _make_secret_dict("GOOD_SECRET_2"),
        ])

        mock_github_instance = Mock()
        mock_github_instance.get_repo.return_value = mock_repo
        reset = datetime.fromtimestamp(datetime.now(timezone.utc).timestamp() + 3600, tz=timezone.utc)
        mock_github_instance.get_rate_limit.return_value = Mock(resources=Mock(core=Mock(remaining=5000, limit=5000, reset=reset)))
        mock_github_class.return_value = mock_github_instance

        client = GitHubClient("fake-token", logger)
        result = client.list_repo_secrets("Test-migration-repos", "test-mg-4")

        assert len(result) == 2
        assert "GOOD_SECRET_1" in result
        assert "GOOD_SECRET_2" in result
        assert "ORG_SECRET" not in result
