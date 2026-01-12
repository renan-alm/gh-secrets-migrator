"""Configuration for migration."""
from typing import Optional


class MigrationConfig:
    """Configuration for the migration."""

    def __init__(
        self,
        source_org: str,
        target_org: str,
        source_pat: str,
        target_pat: str,
        source_repo: str = "",
        target_repo: str = "",
        verbose: bool = False,
        skip_envs: bool = False,
        org_to_org: bool = False,
        repo_list_file: Optional[str] = None
    ):
        self.source_org = source_org
        self.source_repo = source_repo
        self.target_org = target_org
        self.target_repo = target_repo
        self.source_pat = source_pat
        self.target_pat = target_pat
        self.verbose = verbose
        self.skip_envs = skip_envs
        self.org_to_org = org_to_org
        self.repo_list_file = repo_list_file
