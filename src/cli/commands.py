"""Command-line interface for GitHub Secrets Migrator."""
import os
import click
from src.utils.logger import Logger
from src.core.migrator import Migrator
from src.core.config import MigrationConfig


@click.command()
@click.option(
    "--source-org",
    required=True,
    help="Source organization name"
)
@click.option(
    "--source-repo",
    required=False,
    default="",
    help="Source repository name (required for repo-to-repo migration)"
)
@click.option(
    "--target-org",
    required=True,
    help="Target organization name"
)
@click.option(
    "--target-repo",
    required=False,
    default="",
    help="Target repository name (required for repo-to-repo migration)"
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
@click.option(
    "--org-to-org",
    is_flag=True,
    help="Migrate organization secrets only (ignores repo and environment secrets)"
)
def migrate(source_org, source_repo, target_org, target_repo, source_pat, target_pat, verbose, skip_envs, org_to_org):
    """Migrate GitHub secrets from one organization/repository to another.
    
    Two modes of operation:
    - Repository to Repository: Migrates repo and environment secrets
    - Organization to Organization: Migrates only organization-level secrets (use --org-to-org flag)
    """
    logger = Logger(verbose=verbose)

    # Validate modes
    if org_to_org:
        if source_repo or target_repo:
            logger.warn("--org-to-org flag is set; repository names will be ignored")
    else:
        if not source_repo or not target_repo:
            logger.error("source-repo and target-repo are required for repo-to-repo migration")
            logger.error("(or use --org-to-org flag for organization-to-organization migration)")
            raise SystemExit(1)

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
            skip_envs=skip_envs,
            org_to_org=org_to_org
        )

        migrator = Migrator(config, logger)
        migrator.run()

    except RuntimeError as e:
        logger.error(str(e))
        raise SystemExit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {type(e).__name__}: {e}")
        raise SystemExit(1)

