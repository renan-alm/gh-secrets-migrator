"""Tests for CLI authentication token priority logic."""
import os
import pytest
from unittest.mock import patch, MagicMock
from click.testing import CliRunner
from src.cli.commands import migrate


class TestCLIAuthentication:
    """Test cases for CLI authentication token priority."""

    @pytest.fixture
    def mock_migrator(self):
        """Mock the Migrator class to prevent actual execution."""
        with patch('src.cli.commands.Migrator') as mock:
            mock.return_value.run.return_value = None
            yield mock

    def test_source_pat_priority_over_github_token(self, mock_migrator):
        """Test that SOURCE_PAT takes priority over GITHUB_TOKEN."""
        runner = CliRunner()
        
        with runner.isolated_filesystem():
            env = {
                'SOURCE_ORG': 'test-org',
                'SOURCE_REPO': 'test-repo',
                'TARGET_ORG': 'target-org',
                'TARGET_REPO': 'target-repo',
                'SOURCE_PAT': 'specific-source-pat',
                'GITHUB_TOKEN': 'github-token',
                'TARGET_PAT': 'specific-target-pat'
            }
            
            result = runner.invoke(migrate, [], env=env)
            
            assert result.exit_code == 0
            # Verify the config was created with the specific PATs, not GITHUB_TOKEN
            config_call = mock_migrator.call_args
            assert config_call[0][0].source_pat == 'specific-source-pat'
            assert config_call[0][0].target_pat == 'specific-target-pat'

    def test_target_pat_priority_over_github_token(self, mock_migrator):
        """Test that TARGET_PAT takes priority over GITHUB_TOKEN."""
        runner = CliRunner()
        
        with runner.isolated_filesystem():
            env = {
                'SOURCE_ORG': 'test-org',
                'SOURCE_REPO': 'test-repo',
                'TARGET_ORG': 'target-org',
                'TARGET_REPO': 'target-repo',
                'TARGET_PAT': 'specific-target-pat',
                'GITHUB_TOKEN': 'github-token'
            }
            
            result = runner.invoke(migrate, [], env=env)
            
            assert result.exit_code == 0
            # Source should use GITHUB_TOKEN (no SOURCE_PAT), target should use TARGET_PAT
            config_call = mock_migrator.call_args
            assert config_call[0][0].source_pat == 'github-token'
            assert config_call[0][0].target_pat == 'specific-target-pat'

    def test_github_token_fallback(self, mock_migrator):
        """Test that GITHUB_TOKEN is used when specific PATs are not set."""
        runner = CliRunner()
        
        with runner.isolated_filesystem():
            env = {
                'SOURCE_ORG': 'test-org',
                'SOURCE_REPO': 'test-repo',
                'TARGET_ORG': 'target-org',
                'TARGET_REPO': 'target-repo',
                'GITHUB_TOKEN': 'github-token'
            }
            
            result = runner.invoke(migrate, [], env=env)
            
            assert result.exit_code == 0
            # Both should use GITHUB_TOKEN
            config_call = mock_migrator.call_args
            assert config_call[0][0].source_pat == 'github-token'
            assert config_call[0][0].target_pat == 'github-token'

    def test_specific_pats_only(self, mock_migrator):
        """Test using specific PATs without GITHUB_TOKEN."""
        runner = CliRunner()
        
        with runner.isolated_filesystem():
            env = {
                'SOURCE_ORG': 'test-org',
                'SOURCE_REPO': 'test-repo',
                'TARGET_ORG': 'target-org',
                'TARGET_REPO': 'target-repo',
                'SOURCE_PAT': 'source-pat-only',
                'TARGET_PAT': 'target-pat-only'
            }
            
            result = runner.invoke(migrate, [], env=env)
            
            assert result.exit_code == 0
            config_call = mock_migrator.call_args
            assert config_call[0][0].source_pat == 'source-pat-only'
            assert config_call[0][0].target_pat == 'target-pat-only'

    def test_missing_authentication(self):
        """Test that missing authentication tokens raises an error."""
        runner = CliRunner()
        
        with runner.isolated_filesystem():
            env = {
                'SOURCE_ORG': 'test-org',
                'SOURCE_REPO': 'test-repo',
                'TARGET_ORG': 'target-org',
                'TARGET_REPO': 'target-repo'
            }
            
            result = runner.invoke(migrate, [], env=env)
            
            assert result.exit_code == 1
            assert 'source-pat and target-pat are required' in result.output

    def test_partial_authentication_fails(self):
        """Test that having only one PAT (without GITHUB_TOKEN) fails."""
        runner = CliRunner()
        
        with runner.isolated_filesystem():
            env = {
                'SOURCE_ORG': 'test-org',
                'SOURCE_REPO': 'test-repo',
                'TARGET_ORG': 'target-org',
                'TARGET_REPO': 'target-repo',
                'SOURCE_PAT': 'source-only'
            }
            
            result = runner.invoke(migrate, [], env=env)
            
            assert result.exit_code == 1
            assert 'source-pat and target-pat are required' in result.output

    def test_authentication_logging_github_token(self, mock_migrator, caplog):
        """Test that authentication logging is correct when using GITHUB_TOKEN."""
        runner = CliRunner()
        
        with runner.isolated_filesystem():
            env = {
                'SOURCE_ORG': 'test-org',
                'SOURCE_REPO': 'test-repo',
                'TARGET_ORG': 'target-org',
                'TARGET_REPO': 'target-repo',
                'GITHUB_TOKEN': 'github-token'
            }
            
            result = runner.invoke(migrate, [], env=env)
            
            assert result.exit_code == 0
            assert 'Using GITHUB_TOKEN for both source and target authentication' in result.output

    def test_authentication_logging_mixed(self, mock_migrator):
        """Test that authentication logging is correct when using mixed tokens."""
        runner = CliRunner()
        
        with runner.isolated_filesystem():
            env = {
                'SOURCE_ORG': 'test-org',
                'SOURCE_REPO': 'test-repo',
                'TARGET_ORG': 'target-org',
                'TARGET_REPO': 'target-repo',
                'SOURCE_PAT': 'specific-source',
                'GITHUB_TOKEN': 'github-token'
            }
            
            result = runner.invoke(migrate, [], env=env)
            
            assert result.exit_code == 0
            assert 'Using SOURCE_PAT for source authentication' in result.output
            assert 'Using GITHUB_TOKEN for target authentication' in result.output

    def test_authentication_logging_specific_pats(self, mock_migrator):
        """Test that authentication logging is correct when using specific PATs."""
        runner = CliRunner()
        
        with runner.isolated_filesystem():
            env = {
                'SOURCE_ORG': 'test-org',
                'SOURCE_REPO': 'test-repo',
                'TARGET_ORG': 'target-org',
                'TARGET_REPO': 'target-repo',
                'SOURCE_PAT': 'specific-source',
                'TARGET_PAT': 'specific-target'
            }
            
            result = runner.invoke(migrate, [], env=env)
            
            assert result.exit_code == 0
            assert 'Using SOURCE_PAT for source authentication' in result.output
            assert 'Using TARGET_PAT for target authentication' in result.output

    def test_org_to_org_with_mixed_authentication(self, mock_migrator):
        """Test org-to-org mode with mixed authentication tokens."""
        runner = CliRunner()
        
        with runner.isolated_filesystem():
            env = {
                'SOURCE_ORG': 'test-org',
                'SOURCE_REPO': 'test-repo',
                'TARGET_ORG': 'target-org',
                'TARGET_PAT': 'target-specific',
                'GITHUB_TOKEN': 'github-token',
                'ORG_TO_ORG': 'true'
            }
            
            result = runner.invoke(migrate, ['--org-to-org'], env=env)
            
            assert result.exit_code == 0
            # Should use GITHUB_TOKEN for source and TARGET_PAT for target
            config_call = mock_migrator.call_args
            assert config_call[0][0].source_pat == 'github-token'
            assert config_call[0][0].target_pat == 'target-specific'
            assert config_call[0][0].org_to_org is True
