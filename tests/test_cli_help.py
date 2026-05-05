"""Tests for CLI help output and friendly no-args behavior."""
from click.testing import CliRunner
from src.cli.commands import migrate


class TestCLIHelp:
    """Test cases for CLI help display and no-args behavior."""

    def test_no_args_shows_help_and_exits_zero(self):
        """When invoked with no args and no env vars, show full help and exit 0."""
        runner = CliRunner()
        env = {k: "" for k in ("SOURCE_ORG", "TARGET_ORG", "SOURCE_REPO")}
        result = runner.invoke(migrate, [], env=env)

        assert result.exit_code == 0
        assert "Usage:" in result.output
        assert "Required:" in result.output
        assert "Examples:" in result.output

    def test_help_flag_shows_help_and_exits_zero(self):
        """--help flag shows full help and exits 0."""
        runner = CliRunner()
        result = runner.invoke(migrate, ["--help"])

        assert result.exit_code == 0
        assert "Usage:" in result.output
        assert "Required:" in result.output
        assert "Examples:" in result.output

    def test_short_help_flag_shows_help_and_exits_zero(self):
        """-h flag shows full help and exits 0."""
        runner = CliRunner()
        result = runner.invoke(migrate, ["-h"])

        assert result.exit_code == 0
        assert "Usage:" in result.output
        assert "Required:" in result.output

    def test_help_contains_grouped_sections(self):
        """Help output contains all option group headers."""
        runner = CliRunner()
        result = runner.invoke(migrate, ["--help"])

        assert "Required:" in result.output
        assert "Repository:" in result.output
        assert "Authentication:" in result.output
        assert "Endpoints:" in result.output
        assert "Behavior:" in result.output
        assert "Other:" in result.output

    def test_help_contains_env_var_hints(self):
        """Help output mentions environment variable names."""
        runner = CliRunner()
        result = runner.invoke(migrate, ["--help"])

        assert "SOURCE_ORG" in result.output
        assert "TARGET_ORG" in result.output
        assert "SOURCE_PAT" in result.output
        assert "TARGET_PAT" in result.output
        assert "GITHUB_TOKEN" in result.output
        assert "SOURCE_ENDPOINT" in result.output
        assert "TARGET_ENDPOINT" in result.output

    def test_help_contains_examples(self):
        """Help output contains usage examples."""
        runner = CliRunner()
        result = runner.invoke(migrate, ["--help"])

        assert "Repo-to-repo migration:" in result.output
        assert "Org-to-org migration" in result.output
        assert "Using environment variables:" in result.output
        assert "Using a single GITHUB_TOKEN" in result.output
        assert "Migrating from GitHub Enterprise Server:" in result.output

    def test_partial_args_reports_all_missing_options(self):
        """When some required options are missing, report ALL of them at once."""
        runner = CliRunner()
        result = runner.invoke(migrate, ["--source-org", "contoso"])

        assert result.exit_code == 1
        assert "--source-repo" in result.output
        assert "--target-org" in result.output
        assert "--help" in result.output

    def test_partial_args_does_not_report_provided_options(self):
        """Options that were provided should not appear in the missing list."""
        runner = CliRunner()
        result = runner.invoke(migrate, ["--source-org", "contoso"])

        # --source-org was provided, should not be in error output
        assert "Missing required option '--source-org'" not in result.output

    def test_no_args_with_env_vars_does_not_show_help(self):
        """When env vars satisfy required options, don't auto-show help."""
        runner = CliRunner()
        env = {
            "SOURCE_ORG": "contoso",
            "SOURCE_REPO": "app",
            "TARGET_ORG": "fabrikam",
            "TARGET_REPO": "app",
            "SOURCE_PAT": "ghp_xxx",
            "TARGET_PAT": "ghp_yyy",
        }
        # This should NOT show help — it should attempt to run (and fail on network)
        # We just verify it doesn't exit 0 with help text
        result = runner.invoke(migrate, [], env=env)

        # Should not show help page
        assert "Examples:" not in result.output
