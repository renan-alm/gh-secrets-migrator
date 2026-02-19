"""Tests for organization secret scoping functionality."""
from datetime import datetime, timezone
from unittest.mock import Mock, patch
from src.clients.github import GitHubClient
from src.core.workflow_generator import generate_org_secret_steps, generate_workflow
from src.utils.logger import Logger


class MockSecret:
    """Mock GitHub Secret object."""
    
    def __init__(self, name: str, visibility: str = 'all', selected_repos: list = None):
        self.name = name
        self.visibility = visibility
        self._selected_repos = selected_repos or []
    
    @property
    def selected_repositories(self):
        """Mock selected repositories."""
        return [MockRepo(repo_name) for repo_name in self._selected_repos]


class MockRepo:
    """Mock GitHub Repository object."""
    
    def __init__(self, name: str):
        self.name = name
        self.id = hash(name) % 10000  # Generate a simple ID


class MockOrganization:
    """Mock GitHub Organization object."""
    
    def __init__(self, secrets):
        self._secrets = secrets
    
    def get_secrets(self):
        """Return list of mock secrets."""
        return self._secrets
    
    def get_secret(self, name):
        """Get a specific secret by name."""
        for secret in self._secrets:
            if secret.name == name:
                return secret
        raise Exception(f"Secret {name} not found")
    
    def get_repo(self, name):
        """Get a repository by name."""
        # This will be mocked per test
        pass


class TestGetOrgSecretScope:
    """Test getting organization secret scope information."""
    
    @patch('src.clients.github.Github')
    def test_get_org_secret_scope_all_visibility(self, mock_github_class):
        """Test getting scope for a secret with 'all' visibility."""
        logger = Logger(verbose=False)
        
        # Create mock secret with 'all' visibility
        mock_secret = MockSecret("TEST_SECRET", visibility="all")
        mock_org = Mock()
        mock_org.get_secret.return_value = mock_secret
        
        mock_github_instance = Mock()
        mock_github_instance.get_organization.return_value = mock_org
        reset = datetime.fromtimestamp(datetime.now(timezone.utc).timestamp() + 3600, tz=timezone.utc)
        mock_github_instance.get_rate_limit.return_value = Mock(
            resources=Mock(core=Mock(remaining=5000, limit=5000, reset=reset))
        )
        mock_github_class.return_value = mock_github_instance
        
        client = GitHubClient("fake-token", logger)
        result = client.get_org_secret_scope("test-org", "TEST_SECRET")
        
        assert result['visibility'] == 'all'
        assert result['selected_repositories'] == []
    
    @patch('src.clients.github.Github')
    def test_get_org_secret_scope_selected_visibility(self, mock_github_class):
        """Test getting scope for a secret with 'selected' visibility."""
        logger = Logger(verbose=False)
        
        # Create mock secret with 'selected' visibility and repos
        mock_secret = MockSecret("TEST_SECRET", visibility="selected", selected_repos=["repo1", "repo2"])
        mock_org = Mock()
        mock_org.get_secret.return_value = mock_secret
        
        mock_github_instance = Mock()
        mock_github_instance.get_organization.return_value = mock_org
        reset = datetime.fromtimestamp(datetime.now(timezone.utc).timestamp() + 3600, tz=timezone.utc)
        mock_github_instance.get_rate_limit.return_value = Mock(
            resources=Mock(core=Mock(remaining=5000, limit=5000, reset=reset))
        )
        mock_github_class.return_value = mock_github_instance
        
        client = GitHubClient("fake-token", logger)
        result = client.get_org_secret_scope("test-org", "TEST_SECRET")
        
        assert result['visibility'] == 'selected'
        assert len(result['selected_repositories']) == 2
        assert 'repo1' in result['selected_repositories']
        assert 'repo2' in result['selected_repositories']
    
    @patch('src.clients.github.Github')
    def test_get_org_secrets_with_scope(self, mock_github_class):
        """Test getting all org secrets with their scope information."""
        logger = Logger(verbose=False)
        
        # Create mock secrets with different visibility settings
        mock_secrets = [
            MockSecret("SECRET_ALL", visibility="all"),
            MockSecret("SECRET_PRIVATE", visibility="private"),
            MockSecret("SECRET_SELECTED", visibility="selected", selected_repos=["repo1", "repo2"])
        ]
        mock_org = Mock()
        mock_org.get_secrets.return_value = mock_secrets
        
        mock_github_instance = Mock()
        mock_github_instance.get_organization.return_value = mock_org
        reset = datetime.fromtimestamp(datetime.now(timezone.utc).timestamp() + 3600, tz=timezone.utc)
        mock_github_instance.get_rate_limit.return_value = Mock(
            resources=Mock(core=Mock(remaining=5000, limit=5000, reset=reset))
        )
        mock_github_class.return_value = mock_github_instance
        
        client = GitHubClient("fake-token", logger)
        result = client.get_org_secrets_with_scope("test-org")
        
        assert len(result) == 3
        assert result['SECRET_ALL']['visibility'] == 'all'
        assert result['SECRET_PRIVATE']['visibility'] == 'private'
        assert result['SECRET_SELECTED']['visibility'] == 'selected'
        assert len(result['SECRET_SELECTED']['selected_repositories']) == 2


class TestCheckRepoExists:
    """Test checking if repositories exist in target org."""
    
    @patch('src.clients.github.Github')
    def test_check_repo_exists_returns_true(self, mock_github_class):
        """Test that check_repo_exists returns True when repo exists."""
        logger = Logger(verbose=False)
        
        mock_repo = Mock()
        mock_org = Mock()
        mock_org.get_repo.return_value = mock_repo
        
        mock_github_instance = Mock()
        mock_github_instance.get_organization.return_value = mock_org
        reset = datetime.fromtimestamp(datetime.now(timezone.utc).timestamp() + 3600, tz=timezone.utc)
        mock_github_instance.get_rate_limit.return_value = Mock(
            resources=Mock(core=Mock(remaining=5000, limit=5000, reset=reset))
        )
        mock_github_class.return_value = mock_github_instance
        
        client = GitHubClient("fake-token", logger)
        result = client.check_repo_exists("test-org", "existing-repo")
        
        assert result is True
    
    @patch('src.clients.github.Github')
    def test_check_repo_exists_returns_false(self, mock_github_class):
        """Test that check_repo_exists returns False when repo doesn't exist."""
        from github import UnknownObjectException
        
        logger = Logger(verbose=False)
        
        mock_org = Mock()
        mock_org.get_repo.side_effect = UnknownObjectException(404, {}, {})
        
        mock_github_instance = Mock()
        mock_github_instance.get_organization.return_value = mock_org
        reset = datetime.fromtimestamp(datetime.now(timezone.utc).timestamp() + 3600, tz=timezone.utc)
        mock_github_instance.get_rate_limit.return_value = Mock(
            resources=Mock(core=Mock(remaining=5000, limit=5000, reset=reset))
        )
        mock_github_class.return_value = mock_github_instance
        
        client = GitHubClient("fake-token", logger)
        result = client.check_repo_exists("test-org", "non-existing-repo")
        
        assert result is False
    
    @patch('src.clients.github.Github')
    def test_get_matching_repos(self, mock_github_class):
        """Test getting list of matching repositories."""
        from github import UnknownObjectException
        
        logger = Logger(verbose=False)
        
        # Mock org where repo1 and repo3 exist, but repo2 doesn't
        mock_org = Mock()
        
        def get_repo_side_effect(name):
            if name in ["repo1", "repo3"]:
                return Mock()
            raise UnknownObjectException(404, {}, {})
        
        mock_org.get_repo.side_effect = get_repo_side_effect
        
        mock_github_instance = Mock()
        mock_github_instance.get_organization.return_value = mock_org
        reset = datetime.fromtimestamp(datetime.now(timezone.utc).timestamp() + 3600, tz=timezone.utc)
        mock_github_instance.get_rate_limit.return_value = Mock(
            resources=Mock(core=Mock(remaining=5000, limit=5000, reset=reset))
        )
        mock_github_class.return_value = mock_github_instance
        
        client = GitHubClient("fake-token", logger)
        result = client.get_matching_repos("test-org", ["repo1", "repo2", "repo3"])
        
        assert len(result) == 2
        assert "repo1" in result
        assert "repo3" in result
        assert "repo2" not in result


class TestWorkflowGenerationWithScoping:
    """Test workflow generation with organization secret scoping."""
    
    def test_generate_org_secret_steps_with_all_visibility(self):
        """Test workflow generation for org secret with 'all' visibility."""
        org_secrets = ["SECRET_ALL"]
        org_secrets_scope = {
            "SECRET_ALL": {
                "visibility": "all",
                "selected_repositories": []
            }
        }
        
        workflow = generate_org_secret_steps(org_secrets, "target-org", org_secrets_scope)
        
        assert "Migrate Org Secret - SECRET_ALL" in workflow
        assert "SECRET_ALL" in workflow
        assert "visibility selected" not in workflow  # Should not have selected visibility
    
    def test_generate_org_secret_steps_with_selected_visibility(self):
        """Test workflow generation for org secret with 'selected' visibility."""
        org_secrets = ["SECRET_SELECTED"]
        org_secrets_scope = {
            "SECRET_SELECTED": {
                "visibility": "selected",
                "selected_repositories": ["repo1", "repo2"]
            }
        }
        
        workflow = generate_org_secret_steps(org_secrets, "target-org", org_secrets_scope)

        assert "Migrate Org Secret - SECRET_SELECTED" in workflow
        assert "SECRET_SELECTED" in workflow
        assert "--visibility selected" in workflow
        assert "Adding repositories to secret scope" in workflow
        assert "repo1 repo2" in workflow
    
    def test_generate_org_secret_steps_with_selected_no_repos(self):
        """Test workflow generation for org secret with selected visibility but no repos."""
        org_secrets = ["SECRET_SELECTED_EMPTY"]
        org_secrets_scope = {
            "SECRET_SELECTED_EMPTY": {
                "visibility": "selected",
                "selected_repositories": []
            }
        }
        
        workflow = generate_org_secret_steps(org_secrets, "target-org", org_secrets_scope)
        
        assert "Migrate Org Secret - SECRET_SELECTED_EMPTY" in workflow
        assert "--visibility selected" in workflow
        assert "selected visibility, no repositories" in workflow
    
    def test_generate_workflow_with_org_secrets_scope(self):
        """Test full workflow generation with org secret scoping."""
        org_secrets = ["SECRET1", "SECRET2"]
        org_secrets_scope = {
            "SECRET1": {
                "visibility": "all",
                "selected_repositories": []
            },
            "SECRET2": {
                "visibility": "selected",
                "selected_repositories": ["repo1"]
            }
        }
        
        workflow = generate_workflow(
            "source-org",
            "source-repo",
            "target-org",
            "target-repo",
            "migrate-org-secrets",
            org_secrets=org_secrets,
            org_secrets_scope=org_secrets_scope
        )
        
        assert "Migrate Org Secret - SECRET1" in workflow
        assert "Migrate Org Secret - SECRET2" in workflow
        assert "--visibility selected" in workflow  # For SECRET2
        assert "name: move-secrets" in workflow
        assert "Cleanup (Always)" in workflow
    
    def test_generate_org_secret_steps_backward_compatibility(self):
        """Test that workflow generation works without scope information (backward compatibility)."""
        org_secrets = ["SECRET_NO_SCOPE"]
        
        workflow = generate_org_secret_steps(org_secrets, "target-org")
        
        assert "Migrate Org Secret - SECRET_NO_SCOPE" in workflow
        assert "SECRET_NO_SCOPE" in workflow
        # Should use default behavior (all visibility)
    
    def test_generate_org_secret_steps_with_private_visibility(self):
        """Test workflow generation for org secret with 'private' visibility."""
        org_secrets = ["SECRET_PRIVATE"]
        org_secrets_scope = {
            "SECRET_PRIVATE": {
                "visibility": "private",
                "selected_repositories": []
            }
        }
        
        workflow = generate_org_secret_steps(org_secrets, "target-org", org_secrets_scope)
        
        assert "Migrate Org Secret - SECRET_PRIVATE" in workflow
        assert "SECRET_PRIVATE" in workflow
        assert "--visibility private" in workflow


class TestOrgSecretScopingEdgeCases:
    """Test edge cases for organization secret scoping."""
    
    def test_empty_selected_repositories_list(self):
        """Test handling of empty selected repositories list."""
        org_secrets = ["SECRET"]
        org_secrets_scope = {
            "SECRET": {
                "visibility": "selected",
                "selected_repositories": []
            }
        }
        
        workflow = generate_org_secret_steps(org_secrets, "target-org", org_secrets_scope)
        
        assert "SECRET" in workflow
        assert "--visibility selected" in workflow
    
    def test_many_selected_repositories(self):
        """Test handling of many selected repositories."""
        org_secrets = ["SECRET"]
        many_repos = [f"repo{i}" for i in range(50)]
        org_secrets_scope = {
            "SECRET": {
                "visibility": "selected",
                "selected_repositories": many_repos
            }
        }
        
        workflow = generate_org_secret_steps(org_secrets, "target-org", org_secrets_scope)

        assert "SECRET" in workflow
        assert "--visibility selected" in workflow
        # Check that all repos are in the list
        for repo in many_repos[:5]:  # Check first few
            assert repo in workflow
    
    def test_special_characters_in_repo_names(self):
        """Test handling of special characters in repository names."""
        org_secrets = ["SECRET"]
        org_secrets_scope = {
            "SECRET": {
                "visibility": "selected",
                "selected_repositories": ["repo-with-dash", "repo_with_underscore", "repo.with.dot"]
            }
        }
        
        workflow = generate_org_secret_steps(org_secrets, "target-org", org_secrets_scope)

        assert "SECRET" in workflow
        assert "repo-with-dash" in workflow
        assert "repo_with_underscore" in workflow
        assert "repo.with.dot" in workflow
