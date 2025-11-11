"""GitHub API client wrapper."""
from typing import List
from github import Github
from src.utils.logger import Logger


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
            # It's okay if branch doesn't exist - we'll create it fresh
            self.log.debug(f"Branch {branch_name} will be created fresh")

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

    def list_environments(self, org: str, repo: str) -> List[str]:
        """List all environments in the repository."""
        try:
            repository = self.client.get_repo(f"{org}/{repo}")
            environments = []
            for env in repository.get_environments():
                environments.append(env.name)
            return environments
        except Exception as e:
            self.log.debug(f"Failed to list environments: {e}")
            return []

    def create_environment(self, org: str, repo: str, environment_name: str) -> None:
        """Create an environment in the repository. Gracefully handles if already exists."""
        try:
            repository = self.client.get_repo(f"{org}/{repo}")
            repository.create_environment(environment_name)
            self.log.debug(f"Created environment '{environment_name}' in {org}/{repo}")
        except Exception as e:
            error_str = str(e)
            # Handle 409 Conflict (environment already exists)
            if "409" in error_str or "already exists" in error_str.lower():
                self.log.debug(f"Environment '{environment_name}' already exists, skipping")
            else:
                self.log.error(f"Failed to create environment '{environment_name}': {type(e).__name__}: {e}")
                raise RuntimeError(f"Failed to create environment '{environment_name}': {e}")

    def list_environment_names_with_secret_count(self, org: str, repo: str) -> dict:
        """List all environments with their secret counts.
        
        Returns a dictionary mapping environment names to secret counts.
        Useful for user-friendly display.
        """
        try:
            repository = self.client.get_repo(f"{org}/{repo}")
            env_info = {}
            
            for env in repository.get_environments():
                secret_count = 0
                try:
                    env_obj = repository.get_environment(env.name)
                    env_secrets_obj = env_obj.get_secrets()
                    secret_count = len(list(env_secrets_obj))
                except Exception as e:
                    self.log.debug(f"Could not fetch secret count for environment '{env.name}': {e}")
                
                env_info[env.name] = secret_count
            
            return env_info
        except Exception as e:
            self.log.debug(f"Failed to list environments with secret count: {e}")
            return {}

    def list_environment_secrets(self, org: str, repo: str, environment_name: str) -> List[str]:
        """List all secret names in a specific environment.
        
        Args:
            org: Organization name
            repo: Repository name
            environment_name: Environment name
            
        Returns:
            List of secret names in the environment
        """
        try:
            repository = self.client.get_repo(f"{org}/{repo}")
            env_obj = repository.get_environment(environment_name)
            env_secrets_obj = env_obj.get_secrets()
            secret_names = [secret.name for secret in env_secrets_obj]
            return secret_names
        except Exception as e:
            self.log.debug(f"Could not fetch secrets for environment '{environment_name}': {e}")
            return []

    def list_all_environments_with_secrets(self, org: str, repo: str) -> dict:
        """List all environments with their secret names.
        
        Returns a dictionary mapping environment names to lists of secret names.
        Example: {'production': ['DB_PASSWORD', 'API_KEY'], 'staging': ['DB_PASSWORD']}
        """
        try:
            repository = self.client.get_repo(f"{org}/{repo}")
            env_info = {}
            
            for env in repository.get_environments():
                secret_names = []
                try:
                    env_obj = repository.get_environment(env.name)
                    env_secrets_obj = env_obj.get_secrets()
                    secret_names = [secret.name for secret in env_secrets_obj]
                except Exception as e:
                    self.log.debug(f"Could not fetch secrets for environment '{env.name}': {e}")
                
                env_info[env.name] = secret_names
            
            return env_info
        except Exception as e:
            self.log.debug(f"Failed to list environments with secrets: {e}")
            return {}
