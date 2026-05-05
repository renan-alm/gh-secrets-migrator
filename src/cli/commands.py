"""Command-line interface for GitHub Secrets Migrator."""
import os
import click
from src.utils.logger import Logger
from src.core.migrator import Migrator
from src.core.config import MigrationConfig
from src.core.workflow_generator import normalize_endpoint


EPILOG = """\b
Examples:
  Repo-to-repo migration:
    gh secrets-migrator --source-org contoso --source-repo app \\
                        --target-org fabrikam --target-repo app \\
                        --source-pat <PAT> --target-pat <PAT>

  Org-to-org migration (org secrets only):
    gh secrets-migrator --source-org contoso --source-repo app \\
                        --target-org fabrikam --org-to-org \\
                        --source-pat <PAT> --target-pat <PAT>

  Using environment variables:
    export SOURCE_PAT=ghp_xxxxxxxxxxxx
    export TARGET_PAT=ghp_yyyyyyyyyyyy
    gh secrets-migrator --source-org contoso --source-repo app \\
                        --target-org fabrikam --target-repo app

  Using a single GITHUB_TOKEN for both source and target:
    export GITHUB_TOKEN=ghp_xxxxxxxxxxxx
    gh secrets-migrator --source-org contoso --source-repo app \\
                        --target-org fabrikam --target-repo app

  Migrating from GitHub Enterprise Server:
    gh secrets-migrator --source-org contoso --source-repo app \\
                        --target-org fabrikam --target-repo app \\
                        --source-endpoint https://ghes.contoso.com/api/v3 \\
                        --source-pat <PAT> --target-pat <PAT>
"""


# --- Option metadata (grouped) ---
OPTION_GROUPS = [
    ("Required", [
        ("--source-org", "--source-org <source-org>"),
        ("--source-repo", "--source-repo <source-repo>"),
        ("--target-org", "--target-org <target-org>"),
    ]),
    ("Repository", [
        ("--target-repo", "--target-repo <target-repo>"),
    ]),
    ("Authentication", [
        ("--source-pat", "--source-pat <source-pat>"),
        ("--target-pat", "--target-pat <target-pat>"),
    ]),
    ("Endpoints", [
        ("--source-endpoint", "--source-endpoint <source-endpoint>"),
        ("--target-endpoint", "--target-endpoint <target-endpoint>"),
    ]),
    ("Behavior", [
        ("--org-to-org", "--org-to-org"),
        ("--skip-envs", "--skip-envs"),
        ("--skip-overwrite", "--skip-overwrite"),
        ("--verbose", "--verbose"),
    ]),
]


class FriendlyCommand(click.Command):
    """Custom Click command that shows full help when invoked without arguments."""

    def parse_args(self, ctx, args):
        # Show help when no CLI args and no env vars provide the required options
        if not args:
            has_env = any(os.environ.get(v) for v in ("SOURCE_ORG", "TARGET_ORG", "SOURCE_REPO"))
            if not has_env:
                click.echo(ctx.get_help())
                ctx.exit(0)
        return super().parse_args(ctx, args)

    def format_help(self, ctx, formatter):
        """Override help formatting to group options into logical sections."""
        # Write usage
        self.format_usage(ctx, formatter)
        formatter.write("\n")

        # Write description
        if self.help:
            formatter.write_paragraph()
            with formatter.indentation():
                formatter.write(self.help)
            formatter.write("\n")

        # Build a map of option names to their help records
        opts_map = {}
        for param in self.get_params(ctx):
            if isinstance(param, click.Option):
                # Get the option declaration (e.g., --source-org)
                for opt_name in param.opts + param.secondary_opts:
                    record = param.get_help_record(ctx)
                    if record:
                        opts_map[opt_name] = record

        # Write grouped options
        for group_name, group_opts in OPTION_GROUPS:
            formatter.write("\n")
            formatter.write(f"{group_name}:\n")
            records = []
            for opt_key, _ in group_opts:
                if opt_key in opts_map:
                    records.append(opts_map[opt_key])
            if records:
                formatter.write_dl(records)

        # Write help option separately
        formatter.write("\n")
        formatter.write("Other:\n")
        help_record = None
        for param in self.get_params(ctx):
            if isinstance(param, click.Option) and "--help" in param.opts:
                help_record = param.get_help_record(ctx)
                break
        if help_record:
            formatter.write_dl([help_record])

        # Write epilog (examples)
        if self.epilog:
            formatter.write("\n")
            formatter.write(self.epilog)
            formatter.write("\n")


@click.command(
    cls=FriendlyCommand,
    epilog=EPILOG,
    context_settings={"help_option_names": ["-h", "--help"]},
)
@click.option(
    "--source-org",
    required=False,
    envvar="SOURCE_ORG",
    help="Source organization name. Uses SOURCE_ORG env variable. (REQUIRED)"
)
@click.option(
    "--source-repo",
    required=False,
    envvar="SOURCE_REPO",
    help="Source repository name. Uses SOURCE_REPO env variable. (REQUIRED)"
)
@click.option(
    "--target-org",
    required=False,
    envvar="TARGET_ORG",
    help="Target organization name. Uses TARGET_ORG env variable. (REQUIRED)"
)
@click.option(
    "--target-repo",
    required=False,
    default="",
    envvar="TARGET_REPO",
    help=(
        "Target repository name. Uses TARGET_REPO env variable. "
        "Required for repo-to-repo, optional for --org-to-org."
    )
)
@click.option(
    "--source-pat",
    default="",
    envvar="SOURCE_PAT",
    help=(
        "Uses SOURCE_PAT env variable or --source-pat option. "
        "Will fall back to GITHUB_TOKEN if not set."
    )
)
@click.option(
    "--target-pat",
    default="",
    envvar="TARGET_PAT",
    help=(
        "Uses TARGET_PAT env variable or --target-pat option. "
        "Will fall back to GITHUB_TOKEN if not set."
    )
)
@click.option(
    "--verbose",
    is_flag=True,
    envvar="VERBOSE",
    help="Enable verbose logging"
)
@click.option(
    "--skip-envs",
    is_flag=True,
    envvar="SKIP_ENVS",
    help="Skip environment recreation (by default environments are recreated)"
)
@click.option(
    "--skip-overwrite",
    is_flag=True,
    envvar="SKIP_OVERWRITE",
    help="Skip writing secrets that already exist in the target"
)
@click.option(
    "--org-to-org",
    is_flag=True,
    envvar="ORG_TO_ORG",
    help="Migrate organization secrets only (ignores repo and environment secrets)"
)
@click.option(
    "--source-endpoint",
    default="https://api.github.com",
    envvar="SOURCE_ENDPOINT",
    help=(
        "GitHub API endpoint for source. Uses SOURCE_ENDPOINT env variable. "
        "For example: https://ghes.contoso.com/api/v3"
    )
)
@click.option(
    "--target-endpoint",
    default="https://api.github.com",
    envvar="TARGET_ENDPOINT",
    help=(
        "GitHub API endpoint for target. Uses TARGET_ENDPOINT env variable. "
        "Defaults to https://api.github.com"
    )
)
def migrate(
    source_org,
    source_repo,
    target_org,
    target_repo,
    source_pat,
    target_pat,
    verbose,
    skip_envs,
    skip_overwrite,
    org_to_org,
    source_endpoint,
    target_endpoint,
):
    """Migrate GitHub secrets from one organization/repository to another.

    Two modes of operation:
    - Repository to Repository: Migrates repo and environment secrets
    - Organization to Organization: Migrates only org secrets (--org-to-org flag)
    """
    logger = Logger(verbose=verbose)

    # Validate all required options and report ALL missing ones at once
    missing = []
    if not source_org:
        missing.append("--source-org")
    if not source_repo:
        missing.append("--source-repo")
    if not target_org:
        missing.append("--target-org")

    if missing:
        for opt in missing:
            click.echo(f"Error: Missing required option '{opt}'.", err=True)
        click.echo("", err=True)
        click.echo("Try 'gh secrets-migrator --help' for help.", err=True)
        raise SystemExit(1)

    # Validate modes
    if org_to_org:
        # For org-to-org: source-repo required, target-repo optional (defaults to source-repo name)
        logger.info("Organization-to-Organization mode: org secrets only")
        logger.info(f"Source repository (for workflow): {source_repo}")
        logger.info(f"Target repository: {target_repo if target_repo else source_repo}")
    else:
        # For repo-to-repo: both repos required
        if not target_repo:
            logger.error("target-repo is required for repo-to-repo migration")
            logger.error("(or use --org-to-org flag for organization-to-organization migration)")
            raise SystemExit(1)
        logger.info("Repository-to-Repository mode")
        logger.info(f"Source: {source_org}/{source_repo}")
        logger.info(f"Target: {target_org}/{target_repo}")

    # Check for authentication tokens (prioritize specific PATs over GITHUB_TOKEN)
    github_token = os.getenv("GITHUB_TOKEN")

    # Determine source PAT (SOURCE_PAT takes precedence over GITHUB_TOKEN)
    if source_pat:
        source_pat_value = source_pat
        source_token_source = "SOURCE_PAT"
    elif github_token:
        source_pat_value = github_token
        source_token_source = "GITHUB_TOKEN"
    else:
        source_pat_value = ""
        source_token_source = None

    # Determine target PAT (TARGET_PAT takes precedence over GITHUB_TOKEN)
    if target_pat:
        target_pat_value = target_pat
        target_token_source = "TARGET_PAT"
    elif github_token:
        target_pat_value = github_token
        target_token_source = "GITHUB_TOKEN"
    else:
        target_pat_value = ""
        target_token_source = None

    # Log authentication configuration
    if source_token_source and target_token_source:
        if source_token_source == target_token_source == "GITHUB_TOKEN":
            logger.info("Using GITHUB_TOKEN for both source and target authentication")
        else:
            logger.info(f"Using {source_token_source} for source authentication")
            logger.info(f"Using {target_token_source} for target authentication")

    # Validate we have PATs for both
    if not source_pat_value or not target_pat_value:
        logger.error(
            "source-pat and target-pat are required "
            "(or set SOURCE_PAT/TARGET_PAT or GITHUB_TOKEN environment variables)"
        )
        raise SystemExit(1)

    # Normalize endpoints to handle trailing slashes and ensure consistency
    source_endpoint = normalize_endpoint(source_endpoint)
    target_endpoint = normalize_endpoint(target_endpoint)

    # Log endpoint configuration if non-default
    if source_endpoint != "https://api.github.com":
        logger.info(f"Using custom source endpoint: {source_endpoint}")
    if target_endpoint != "https://api.github.com":
        logger.info(f"Using custom target endpoint: {target_endpoint}")

    try:
        config = MigrationConfig(
            source_org=source_org,
            source_repo=source_repo,
            target_org=target_org,
            target_repo=target_repo,
            source_pat=source_pat_value,
            target_pat=target_pat_value,
            verbose=verbose,
            skip_envs=skip_envs,
            skip_overwrite=skip_overwrite,
            org_to_org=org_to_org,
            source_endpoint=source_endpoint,
            target_endpoint=target_endpoint
        )

        migrator = Migrator(config, logger)
        migrator.run()

    except RuntimeError as e:
        logger.error(str(e))
        raise SystemExit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {type(e).__name__}: {e}")
        raise SystemExit(1)
