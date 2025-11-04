"""Command-line interface for GitHub Secrets Migrator."""
import os
import click
from src.logger import Logger
from src.migrator import Migrator, MigrationConfig


@click.command()
@click.option(
    "--source-org",
    required=True,
    help="Source organization name"
)
@click.option(
    "--source-repo",
    required=True,
    help="Source repository name"
)
@click.option(
    "--target-org",
    required=True,
    help="Target organization name"
)
@click.option(
    "--target-repo",
    required=True,
    help="Target repository name"
)
@click.option(
    "--source-pat",
    default="",
    help="Personal Access Token for source repository (optional if GITHUB_TOKEN is set)"
)
@click.option(
    "--target-pat",
    default="",
    help="Personal Access Token for target repository (optional if GITHUB_TOKEN is set)"
)
@click.option(
    "--verbose",
    is_flag=True,
    help="Enable verbose logging"
)
@click.option(
    "--skip-envs",
    is_flag=True,
    help="Skip environment recreation (by default environments are recreated)"
)
def migrate(source_org, source_repo, target_org, target_repo, source_pat, target_pat, verbose, skip_envs):
    """Migrate GitHub secrets from one repository to another."""
    logger = Logger(verbose=verbose)

    # Check for GITHUB_TOKEN environment variable
    github_token = os.getenv("GITHUB_TOKEN")
    if github_token:
        logger.info("GITHUB_TOKEN environment variable detected, using it for both source and target authentication")
        source_pat_value = github_token
        target_pat_value = github_token
    else:
        source_pat_value = source_pat
        target_pat_value = target_pat

    # Validate we have PATs for both
    if not source_pat_value or not target_pat_value:
        logger.error("source-pat and target-pat are required (or set GITHUB_TOKEN environment variable)")
        raise SystemExit(1)

    try:
        config = MigrationConfig(
            source_org=source_org,
            source_repo=source_repo,
            target_org=target_org,
            target_repo=target_repo,
            source_pat=source_pat_value,
            target_pat=target_pat_value,
            verbose=verbose,
            skip_envs=skip_envs
        )

        migrator = Migrator(config, logger)
        migrator.run()

    except RuntimeError as e:
        logger.error(str(e))
        raise SystemExit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {type(e).__name__}: {e}")
        raise SystemExit(1)
