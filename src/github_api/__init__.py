"""GitHub API client wrapper."""
from typing import List
from github import Github
from src.logger import Logger


class GitHubClient:
    """Client for GitHub API operations."""

    def __init__(self, pat: str, logger: Logger):
        """Initialize GitHub client with PAT."""
        self.client = Github(pat)
        self.log = logger

    def get_default_branch(self, org: str, repo: str) -> str:
        """Get the default branch of a repository."""
        try:
            repository = self.client.get_user(org).get_repo(repo)
            return repository.default_branch
        except Exception as e:
            raise RuntimeError(f"Failed to get repository: {e}")

    def get_commit_sha(self, org: str, repo: str, branch: str) -> str:
        """Get the commit SHA for a given branch."""
        try:
            repository = self.client.get_user(org).get_repo(repo)
            ref = repository.get_git_ref(f"heads/{branch}")
            return ref.object.sha
        except Exception as e:
            raise RuntimeError(f"Failed to get commit SHA: {e}")

    def create_branch(self, org: str, repo: str, branch_name: str, sha: str) -> None:
        """Create a new branch in the repository."""
        try:
            repository = self.client.get_user(org).get_repo(repo)
            repository.create_git_ref(f"refs/heads/{branch_name}", sha)
            self.log.debug(f"Created branch {branch_name}")
        except Exception as e:
            raise RuntimeError(f"Failed to create branch: {e}")

    def delete_branch(self, org: str, repo: str, branch_name: str) -> None:
        """Delete a branch from the repository."""
        try:
            repository = self.client.get_user(org).get_repo(repo)
            repository.get_git_ref(f"heads/{branch_name}").delete()
            self.log.debug(f"Deleted branch {branch_name}")
        except Exception as e:
            # It's okay if branch doesn't exist
            self.log.debug(f"Branch {branch_name} does not exist or could not be deleted: {e}")

    def list_repo_secrets(self, org: str, repo: str) -> List[str]:
        """List all secrets in the repository."""
        try:
            repository = self.client.get_user(org).get_repo(repo)
            secrets = repository.get_secrets()
            return [secret.name for secret in secrets]
        except Exception as e:
            raise RuntimeError(f"Failed to list secrets: {e}")

    def create_repo_secret(self, org: str, repo: str, secret_name: str, secret_value: str) -> None:
        """Create or update a secret in the repository."""
        try:
            repository = self.client.get_user(org).get_repo(repo)
            # PyGithub handles encryption automatically!
            repository.create_secret(secret_name, secret_value)
            self.log.debug(f"Created/updated secret {secret_name} in {org}/{repo}")
        except Exception as e:
            self.log.error(f"Failed to create/update secret {secret_name}: {type(e).__name__}: {e}")
            raise RuntimeError(f"Failed to create/update secret {secret_name}: {e}")

    def delete_secret(self, org: str, repo: str, secret_name: str) -> None:
        """Delete a secret from the repository."""
        try:
            repository = self.client.get_user(org).get_repo(repo)
            secret = repository.get_secret(secret_name)
            secret.delete()
            self.log.debug(f"Deleted secret {secret_name}")
        except Exception as e:
            raise RuntimeError(f"Failed to delete secret: {e}")

    def create_file(self, org: str, repo: str, branch: str, path: str, contents: str) -> None:
        """Create or update a file in the repository."""
        try:
            repository = self.client.get_user(org).get_repo(repo)
            repository.create_file(
                path=path,
                message=f"Add {path}",
                content=contents,
                branch=branch
            )
            self.log.debug(f"Created file {path} on branch {branch}")
        except Exception as e:
            raise RuntimeError(f"Failed to create file: {e}")
