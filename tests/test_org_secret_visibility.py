"""Tests for organization secret visibility and repository selection."""
import pytest
from unittest.mock import Mock, MagicMock, patch
from src.clients.github import GitHubClient
from src.core.workflow_generator import generate_org_secret_steps
from src.utils.logger import Logger


class MockOrganizationSecret:
    """Mock GitHub OrganizationSecret object."""
    
    def __init__(self, name: str, visibility: str = 'all', selected_repos: list = None):
        self.name = name
        self.visibility = visibility
        self._selected_repos = selected_repos or []
        
    @property
    def selected_repositories(self):
        """Mock selected_repositories property that returns a list of mock repos."""
        return [MockRepo(repo_name) for repo_name in self._selected_repos]


class MockRepo:
    """Mock GitHub Repository object."""
    
    def __init__(self, name: str):
        self.name = name


class TestOrgSecretVisibility:
    """Test organization secret visibility handling."""
    
    @patch('src.clients.github.Github')
    def test_get_org_secret_details_all_visibility(self, mock_github_class):
        """Test getting details for org secret with 'all' visibility."""
        logger = Logger(verbose=False)
        
        # Mock organization and secret
        mock_org = Mock()
        mock_secret = MockOrganizationSecret("TEST_SECRET", visibility='all')
        mock_org.get_secret.return_value = mock_secret
        
        # Set up the mock chain
        mock_github_instance = Mock()
        mock_github_instance.get_organization.return_value = mock_org
        mock_github_instance.get_rate_limit.return_value = Mock(
            core=Mock(remaining=5000, limit=5000, reset=1234567890)
        )
        mock_github_class.return_value = mock_github_instance
        
        # Create client and test
        client = GitHubClient("fake-token", logger)
        result = client.get_org_secret_details("test-org", "TEST_SECRET")
        
        assert result['name'] == "TEST_SECRET"
        assert result['visibility'] == 'all'
        assert result['selected_repository_names'] == []
    
    @patch('src.clients.github.Github')
    def test_get_org_secret_details_selected_visibility(self, mock_github_class):
        """Test getting details for org secret with 'selected' visibility."""
        logger = Logger(verbose=False)
        
        # Mock organization and secret with selected repositories
        mock_org = Mock()
        mock_secret = MockOrganizationSecret(
            "TEST_SECRET", 
            visibility='selected',
            selected_repos=['repo1', 'repo2', 'repo3']
        )
        mock_org.get_secret.return_value = mock_secret
        
        # Set up the mock chain
        mock_github_instance = Mock()
        mock_github_instance.get_organization.return_value = mock_org
        mock_github_instance.get_rate_limit.return_value = Mock(
            core=Mock(remaining=5000, limit=5000, reset=1234567890)
        )
        mock_github_class.return_value = mock_github_instance
        
        # Create client and test
        client = GitHubClient("fake-token", logger)
        result = client.get_org_secret_details("test-org", "TEST_SECRET")
        
        assert result['name'] == "TEST_SECRET"
        assert result['visibility'] == 'selected'
        assert len(result['selected_repository_names']) == 3
        assert 'repo1' in result['selected_repository_names']
        assert 'repo2' in result['selected_repository_names']
        assert 'repo3' in result['selected_repository_names']
    
    @patch('src.clients.github.Github')
    def test_list_org_secrets_with_details(self, mock_github_class):
        """Test listing all org secrets with their visibility details."""
        logger = Logger(verbose=False)
        
        # Mock organization with multiple secrets
        mock_org = Mock()
        mock_secrets = [
            MockOrganizationSecret("SECRET_ALL", visibility='all'),
            MockOrganizationSecret("SECRET_PRIVATE", visibility='private'),
            MockOrganizationSecret("SECRET_SELECTED", visibility='selected', selected_repos=['repo1', 'repo2']),
        ]
        mock_org.get_secrets.return_value = mock_secrets
        
        # Set up the mock chain
        mock_github_instance = Mock()
        mock_github_instance.get_organization.return_value = mock_org
        mock_github_instance.get_rate_limit.return_value = Mock(
            core=Mock(remaining=5000, limit=5000, reset=1234567890)
        )
        mock_github_class.return_value = mock_github_instance
        
        # Create client and test
        client = GitHubClient("fake-token", logger)
        result = client.list_org_secrets_with_details("test-org")
        
        assert len(result) == 3
        
        # Check 'all' visibility secret
        secret_all = next(s for s in result if s['name'] == 'SECRET_ALL')
        assert secret_all['visibility'] == 'all'
        assert secret_all['selected_repository_names'] == []
        
        # Check 'private' visibility secret
        secret_private = next(s for s in result if s['name'] == 'SECRET_PRIVATE')
        assert secret_private['visibility'] == 'private'
        assert secret_private['selected_repository_names'] == []
        
        # Check 'selected' visibility secret
        secret_selected = next(s for s in result if s['name'] == 'SECRET_SELECTED')
        assert secret_selected['visibility'] == 'selected'
        assert len(secret_selected['selected_repository_names']) == 2
        assert 'repo1' in secret_selected['selected_repository_names']
        assert 'repo2' in secret_selected['selected_repository_names']
    
    @patch('src.clients.github.Github')
    def test_get_org_repository_names(self, mock_github_class):
        """Test getting list of repositories in an organization."""
        logger = Logger(verbose=False)
        
        # Mock organization with multiple repositories
        mock_org = Mock()
        mock_repos = [
            MockRepo('repo1'),
            MockRepo('repo2'),
            MockRepo('repo3'),
            MockRepo('repo4'),
        ]
        mock_org.get_repos.return_value = mock_repos
        
        # Set up the mock chain
        mock_github_instance = Mock()
        mock_github_instance.get_organization.return_value = mock_org
        mock_github_instance.get_rate_limit.return_value = Mock(
            core=Mock(remaining=5000, limit=5000, reset=1234567890)
        )
        mock_github_class.return_value = mock_github_instance
        
        # Create client and test
        client = GitHubClient("fake-token", logger)
        result = client.get_org_repository_names("test-org")
        
        assert len(result) == 4
        assert 'repo1' in result
        assert 'repo2' in result
        assert 'repo3' in result
        assert 'repo4' in result


class TestWorkflowGeneratorWithVisibility:
    """Test workflow generation with org secret visibility settings."""

    def test_generate_org_secret_steps_all_visibility(self):
        """Test workflow generation for secret with 'all' visibility."""
        org_secrets = [
            {"name": "SECRET_ALL", "visibility": "all", "selected_repository_names": []}
        ]
        result = generate_org_secret_steps(org_secrets, "target-org")

        assert "Migrate Org Secret - SECRET_ALL" in result
        assert "VISIBILITY: 'all'" in result
        # Check that it uses the $VISIBILITY variable in the else branch
        assert '--visibility "$VISIBILITY"' in result

    def test_generate_org_secret_steps_private_visibility(self):
        """Test workflow generation for secret with 'private' visibility."""
        org_secrets = [
            {
                "name": "SECRET_PRIVATE",
                "visibility": "private",
                "selected_repository_names": [],
            }
        ]
        result = generate_org_secret_steps(org_secrets, "target-org")

        assert "Migrate Org Secret - SECRET_PRIVATE" in result
        assert "VISIBILITY: 'private'" in result
        assert '--visibility "$VISIBILITY"' in result

    def test_generate_org_secret_steps_selected_visibility_with_repos(self):
        """Test workflow generation for secret with 'selected' visibility and repositories."""
        org_secrets = [
            {
                "name": "SECRET_SELECTED",
                "visibility": "selected",
                "selected_repository_names": ["repo1", "repo2"],
            }
        ]
        result = generate_org_secret_steps(org_secrets, "target-org")

        assert "Migrate Org Secret - SECRET_SELECTED" in result
        assert "VISIBILITY: 'selected'" in result
        assert '--repos "$REPOS_LIST"' in result
        assert "REPOS_LIST: 'repo1,repo2'" in result

    def test_generate_org_secret_steps_selected_visibility_no_repos(self):
        """Test workflow generation for secret with 'selected' visibility but no repositories."""
        org_secrets = [
            {
                "name": "SECRET_SELECTED_EMPTY",
                "visibility": "selected",
                "selected_repository_names": [],
            }
        ]
        result = generate_org_secret_steps(org_secrets, "target-org")

        assert "Migrate Org Secret - SECRET_SELECTED_EMPTY" in result
        assert "VISIBILITY: 'selected'" in result
        # Check that it handles empty REPOS_LIST correctly
        assert "REPOS_LIST: ''" in result
        # This should use the elif branch (no --repos flag)
        assert 'elif [ "$VISIBILITY" = "selected" ]; then' in result

    def test_generate_org_secret_steps_legacy_format(self):
        """Test workflow generation with legacy format (list of strings)."""
        org_secrets = ["SECRET1", "SECRET2", "SECRET3"]
        result = generate_org_secret_steps(org_secrets, "target-org")

        # Should default to 'all' visibility for legacy format
        assert "Migrate Org Secret - SECRET1" in result
        assert "Migrate Org Secret - SECRET2" in result
        assert "Migrate Org Secret - SECRET3" in result
        assert "VISIBILITY: 'all'" in result
        assert '--visibility "$VISIBILITY"' in result

    def test_generate_org_secret_steps_mixed_visibility(self):
        """Test workflow generation with multiple secrets of different visibility."""
        org_secrets = [
            {"name": "SECRET_ALL", "visibility": "all", "selected_repository_names": []},
            {
                "name": "SECRET_PRIVATE",
                "visibility": "private",
                "selected_repository_names": [],
            },
            {
                "name": "SECRET_SELECTED",
                "visibility": "selected",
                "selected_repository_names": ["repo1", "repo2", "repo3"],
            },
        ]
        result = generate_org_secret_steps(org_secrets, "target-org")

        # Check all secrets are present
        assert "Migrate Org Secret - SECRET_ALL" in result
        assert "Migrate Org Secret - SECRET_PRIVATE" in result
        assert "Migrate Org Secret - SECRET_SELECTED" in result

        # Check visibility settings
        assert "VISIBILITY: 'all'" in result
        assert "VISIBILITY: 'private'" in result
        assert "VISIBILITY: 'selected'" in result

        # Check repository selection
        assert "REPOS_LIST: 'repo1,repo2,repo3'" in result


class TestRepositoryMatching:
    """Test repository matching logic between source and target orgs."""
    
    def test_repository_matching_all_exist(self):
        """Test when all selected repositories exist in target org."""
        source_repos = ['repo1', 'repo2', 'repo3']
        target_repos = ['repo1', 'repo2', 'repo3', 'repo4', 'repo5']
        target_repo_set = set(target_repos)
        
        matching = [repo for repo in source_repos if repo in target_repo_set]
        missing = [repo for repo in source_repos if repo not in target_repo_set]
        
        assert len(matching) == 3
        assert len(missing) == 0
    
    def test_repository_matching_partial_exist(self):
        """Test when only some selected repositories exist in target org."""
        source_repos = ['repo1', 'repo2', 'repo3']
        target_repos = ['repo1', 'repo3', 'repo4', 'repo5']
        target_repo_set = set(target_repos)
        
        matching = [repo for repo in source_repos if repo in target_repo_set]
        missing = [repo for repo in source_repos if repo not in target_repo_set]
        
        assert len(matching) == 2
        assert 'repo1' in matching
        assert 'repo3' in matching
        assert len(missing) == 1
        assert 'repo2' in missing
    
    def test_repository_matching_none_exist(self):
        """Test when no selected repositories exist in target org."""
        source_repos = ['repo1', 'repo2', 'repo3']
        target_repos = ['repo4', 'repo5', 'repo6']
        target_repo_set = set(target_repos)
        
        matching = [repo for repo in source_repos if repo in target_repo_set]
        missing = [repo for repo in source_repos if repo not in target_repo_set]
        
        assert len(matching) == 0
        assert len(missing) == 3
