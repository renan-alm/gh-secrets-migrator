"""Tests for CLI fail-fast input sanity validation."""
from click.testing import CliRunner
from unittest.mock import patch

from src.cli.commands import migrate


class TestCLIValidation:
    """Validate org/repo input sanitization and format checks."""

    @patch('src.cli.commands.Migrator')
    def test_invalid_source_org_rejected(self, mock_migrator):
        """source-org with invalid characters should fail fast."""
        mock_migrator.return_value.run.return_value = None
        runner = CliRunner()

        env = {
            'SOURCE_ORG': 'bad@org',
            'SOURCE_REPO': 'source-repo',
            'TARGET_ORG': 'target-org',
            'TARGET_REPO': 'target-repo',
            'SOURCE_PAT': 'source-pat',
            'TARGET_PAT': 'target-pat',
        }

        result = runner.invoke(migrate, [], env=env)

        assert result.exit_code == 1
        assert "Invalid source-org" in result.output
        mock_migrator.assert_not_called()

    @patch('src.cli.commands.Migrator')
    def test_target_repo_whitespace_rejected_in_repo_mode(self, mock_migrator):
        """Whitespace target-repo should be treated as missing in repo mode."""
        mock_migrator.return_value.run.return_value = None
        runner = CliRunner()

        env = {
            'SOURCE_ORG': 'source-org',
            'SOURCE_REPO': 'source-repo',
            'TARGET_ORG': 'target-org',
            'TARGET_REPO': '   ',
            'SOURCE_PAT': 'source-pat',
            'TARGET_PAT': 'target-pat',
        }

        result = runner.invoke(migrate, [], env=env)

        assert result.exit_code == 1
        assert "target-repo is required for repo-to-repo migration" in result.output
        mock_migrator.assert_not_called()

    @patch('src.cli.commands.Migrator')
    def test_source_repo_with_spaces_rejected(self, mock_migrator):
        """source-repo containing spaces should fail validation."""
        mock_migrator.return_value.run.return_value = None
        runner = CliRunner()

        env = {
            'SOURCE_ORG': 'source-org',
            'SOURCE_REPO': 'invalid repo',
            'TARGET_ORG': 'target-org',
            'TARGET_REPO': 'target-repo',
            'SOURCE_PAT': 'source-pat',
            'TARGET_PAT': 'target-pat',
        }

        result = runner.invoke(migrate, [], env=env)

        assert result.exit_code == 1
        assert "Invalid source-repo" in result.output
        mock_migrator.assert_not_called()

    @patch('src.cli.commands.Migrator')
    def test_whitespace_source_pat_is_missing(self, mock_migrator):
        """Whitespace source PAT should produce source-specific missing token error."""
        mock_migrator.return_value.run.return_value = None
        runner = CliRunner()

        env = {
            'SOURCE_ORG': 'source-org',
            'SOURCE_REPO': 'source-repo',
            'TARGET_ORG': 'target-org',
            'TARGET_REPO': 'target-repo',
            'SOURCE_PAT': '   ',
            'TARGET_PAT': 'target-pat',
        }

        result = runner.invoke(migrate, [], env=env)

        assert result.exit_code == 1
        assert "Missing source authentication token" in result.output
        mock_migrator.assert_not_called()

    @patch('src.cli.commands.Migrator')
    def test_org_to_org_allows_empty_target_repo(self, mock_migrator):
        """org-to-org mode should continue when target-repo is omitted."""
        mock_migrator.return_value.run.return_value = None
        runner = CliRunner()

        env = {
            'SOURCE_ORG': 'source-org',
            'SOURCE_REPO': 'source-repo',
            'TARGET_ORG': 'target-org',
            'SOURCE_PAT': 'source-pat',
            'TARGET_PAT': 'target-pat',
            'ORG_TO_ORG': 'true',
        }

        result = runner.invoke(migrate, ['--org-to-org'], env=env)

        assert result.exit_code == 0
        mock_migrator.assert_called_once()
