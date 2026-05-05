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

    def test_skip_overwrite_env_var(self, mock_migrator):
        """Test that SKIP_OVERWRITE env var is parsed and stored in config."""
        runner = CliRunner()

        with runner.isolated_filesystem():
            env = {
                'SOURCE_ORG': 'test-org',
                'SOURCE_REPO': 'test-repo',
                'TARGET_ORG': 'target-org',
                'TARGET_REPO': 'target-repo',
                'GITHUB_TOKEN': 'github-token',
                'SKIP_OVERWRITE': 'true'
            }

            result = runner.invoke(migrate, [], env=env)

            assert result.exit_code == 0
            config_call = mock_migrator.call_args
            assert config_call[0][0].skip_overwrite is True


class TestGhGeiCompatibleAuthentication:
    """Test cases for gh-gei compatible authentication (GH_SOURCE_PAT, GH_PAT)."""

    @pytest.fixture
    def mock_migrator(self):
        """Mock the Migrator class to prevent actual execution."""
        with patch('src.cli.commands.Migrator') as mock:
            mock.return_value.run.return_value = None
            yield mock

    def test_gh_source_pat_sets_source(self, mock_migrator):
        """Test that GH_SOURCE_PAT is used for source when SOURCE_PAT is not set."""
        runner = CliRunner()

        with runner.isolated_filesystem():
            env = {
                'SOURCE_ORG': 'test-org',
                'SOURCE_REPO': 'test-repo',
                'TARGET_ORG': 'target-org',
                'TARGET_REPO': 'target-repo',
                'GH_SOURCE_PAT': 'gh-source-pat-value',
                'GH_PAT': 'gh-pat-value',
            }

            result = runner.invoke(migrate, [], env=env)

            assert result.exit_code == 0
            config_call = mock_migrator.call_args
            assert config_call[0][0].source_pat == 'gh-source-pat-value'
            assert config_call[0][0].target_pat == 'gh-pat-value'

    def test_gh_pat_sets_target(self, mock_migrator):
        """Test that GH_PAT is used for target when TARGET_PAT is not set."""
        runner = CliRunner()

        with runner.isolated_filesystem():
            env = {
                'SOURCE_ORG': 'test-org',
                'SOURCE_REPO': 'test-repo',
                'TARGET_ORG': 'target-org',
                'TARGET_REPO': 'target-repo',
                'SOURCE_PAT': 'source-pat-value',
                'GH_PAT': 'gh-pat-value',
            }

            result = runner.invoke(migrate, [], env=env)

            assert result.exit_code == 0
            config_call = mock_migrator.call_args
            assert config_call[0][0].source_pat == 'source-pat-value'
            assert config_call[0][0].target_pat == 'gh-pat-value'

    def test_gh_pat_fallback_for_source(self, mock_migrator):
        """Test GH_PAT is used as source fallback when no SOURCE_PAT or GH_SOURCE_PAT."""
        runner = CliRunner()

        with runner.isolated_filesystem():
            env = {
                'SOURCE_ORG': 'test-org',
                'SOURCE_REPO': 'test-repo',
                'TARGET_ORG': 'target-org',
                'TARGET_REPO': 'target-repo',
                'GH_PAT': 'gh-pat-value',
            }

            result = runner.invoke(migrate, [], env=env)

            assert result.exit_code == 0
            config_call = mock_migrator.call_args
            assert config_call[0][0].source_pat == 'gh-pat-value'
            assert config_call[0][0].target_pat == 'gh-pat-value'

    def test_source_pat_priority_over_gh_source_pat(self, mock_migrator):
        """Test that SOURCE_PAT takes priority over GH_SOURCE_PAT."""
        runner = CliRunner()

        with runner.isolated_filesystem():
            env = {
                'SOURCE_ORG': 'test-org',
                'SOURCE_REPO': 'test-repo',
                'TARGET_ORG': 'target-org',
                'TARGET_REPO': 'target-repo',
                'SOURCE_PAT': 'source-pat-wins',
                'GH_SOURCE_PAT': 'gh-source-pat-loses',
                'GH_PAT': 'gh-pat-value',
            }

            result = runner.invoke(migrate, [], env=env)

            assert result.exit_code == 0
            config_call = mock_migrator.call_args
            assert config_call[0][0].source_pat == 'source-pat-wins'

    def test_target_pat_priority_over_gh_pat(self, mock_migrator):
        """Test that TARGET_PAT takes priority over GH_PAT."""
        runner = CliRunner()

        with runner.isolated_filesystem():
            env = {
                'SOURCE_ORG': 'test-org',
                'SOURCE_REPO': 'test-repo',
                'TARGET_ORG': 'target-org',
                'TARGET_REPO': 'target-repo',
                'TARGET_PAT': 'target-pat-wins',
                'GH_PAT': 'gh-pat-loses',
                'SOURCE_PAT': 'source-pat-value',
            }

            result = runner.invoke(migrate, [], env=env)

            assert result.exit_code == 0
            config_call = mock_migrator.call_args
            assert config_call[0][0].target_pat == 'target-pat-wins'

    def test_gh_source_pat_priority_over_gh_pat_for_source(self, mock_migrator):
        """Test that GH_SOURCE_PAT takes priority over GH_PAT for source."""
        runner = CliRunner()

        with runner.isolated_filesystem():
            env = {
                'SOURCE_ORG': 'test-org',
                'SOURCE_REPO': 'test-repo',
                'TARGET_ORG': 'target-org',
                'TARGET_REPO': 'target-repo',
                'GH_SOURCE_PAT': 'gh-source-wins',
                'GH_PAT': 'gh-pat-loses-for-source',
            }

            result = runner.invoke(migrate, [], env=env)

            assert result.exit_code == 0
            config_call = mock_migrator.call_args
            assert config_call[0][0].source_pat == 'gh-source-wins'
            assert config_call[0][0].target_pat == 'gh-pat-loses-for-source'

    def test_github_source_pat_cli_arg(self, mock_migrator):
        """Test --github-source-pat CLI argument works."""
        runner = CliRunner()

        with runner.isolated_filesystem():
            env = {
                'SOURCE_ORG': 'test-org',
                'SOURCE_REPO': 'test-repo',
                'TARGET_ORG': 'target-org',
                'TARGET_REPO': 'target-repo',
            }

            result = runner.invoke(
                migrate,
                ['--github-source-pat', 'cli-gh-source', '--github-target-pat', 'cli-gh-target'],
                env=env,
            )

            assert result.exit_code == 0
            config_call = mock_migrator.call_args
            assert config_call[0][0].source_pat == 'cli-gh-source'
            assert config_call[0][0].target_pat == 'cli-gh-target'

    def test_github_target_pat_cli_arg(self, mock_migrator):
        """Test --github-target-pat CLI argument works as source fallback too."""
        runner = CliRunner()

        with runner.isolated_filesystem():
            env = {
                'SOURCE_ORG': 'test-org',
                'SOURCE_REPO': 'test-repo',
                'TARGET_ORG': 'target-org',
                'TARGET_REPO': 'target-repo',
            }

            result = runner.invoke(
                migrate,
                ['--github-target-pat', 'single-pat'],
                env=env,
            )

            assert result.exit_code == 0
            config_call = mock_migrator.call_args
            assert config_call[0][0].source_pat == 'single-pat'
            assert config_call[0][0].target_pat == 'single-pat'

    def test_logging_gh_source_pat(self, mock_migrator):
        """Test that authentication logging reports GH_SOURCE_PAT correctly."""
        runner = CliRunner()

        with runner.isolated_filesystem():
            env = {
                'SOURCE_ORG': 'test-org',
                'SOURCE_REPO': 'test-repo',
                'TARGET_ORG': 'target-org',
                'TARGET_REPO': 'target-repo',
                'GH_SOURCE_PAT': 'gh-source-value',
                'GH_PAT': 'gh-pat-value',
            }

            result = runner.invoke(migrate, [], env=env)

            assert result.exit_code == 0
            assert 'Using GH_SOURCE_PAT for source authentication' in result.output
            assert 'Using GH_PAT for target authentication' in result.output

    def test_logging_gh_pat_for_both(self, mock_migrator):
        """Test that logging is correct when GH_PAT is used for both source and target."""
        runner = CliRunner()

        with runner.isolated_filesystem():
            env = {
                'SOURCE_ORG': 'test-org',
                'SOURCE_REPO': 'test-repo',
                'TARGET_ORG': 'target-org',
                'TARGET_REPO': 'target-repo',
                'GH_PAT': 'gh-pat-value',
            }

            result = runner.invoke(migrate, [], env=env)

            assert result.exit_code == 0
            assert 'Using GH_PAT for source authentication' in result.output
            assert 'Using GH_PAT for target authentication' in result.output

    def test_gh_pat_overridden_by_github_token_not(self, mock_migrator):
        """Test that GH_PAT takes priority over GITHUB_TOKEN."""
        runner = CliRunner()

        with runner.isolated_filesystem():
            env = {
                'SOURCE_ORG': 'test-org',
                'SOURCE_REPO': 'test-repo',
                'TARGET_ORG': 'target-org',
                'TARGET_REPO': 'target-repo',
                'GH_PAT': 'gh-pat-wins',
                'GITHUB_TOKEN': 'github-token-loses',
            }

            result = runner.invoke(migrate, [], env=env)

            assert result.exit_code == 0
            config_call = mock_migrator.call_args
            assert config_call[0][0].source_pat == 'gh-pat-wins'
            assert config_call[0][0].target_pat == 'gh-pat-wins'

    def test_full_priority_chain_source(self, mock_migrator):
        """Test full priority chain: SOURCE_PAT > GH_SOURCE_PAT > GH_PAT > GITHUB_TOKEN."""
        runner = CliRunner()

        with runner.isolated_filesystem():
            env = {
                'SOURCE_ORG': 'test-org',
                'SOURCE_REPO': 'test-repo',
                'TARGET_ORG': 'target-org',
                'TARGET_REPO': 'target-repo',
                'SOURCE_PAT': 'highest-priority',
                'GH_SOURCE_PAT': 'second-priority',
                'GH_PAT': 'third-priority',
                'GITHUB_TOKEN': 'lowest-priority',
            }

            result = runner.invoke(migrate, [], env=env)

            assert result.exit_code == 0
            config_call = mock_migrator.call_args
            assert config_call[0][0].source_pat == 'highest-priority'
            assert config_call[0][0].target_pat == 'third-priority'
