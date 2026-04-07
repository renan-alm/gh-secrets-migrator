"""GitHub API client wrapper."""
# flake8: noqa: E501
from base64 import b64encode
from typing import List, Dict, Any
from github import Github, UnknownObjectException
from nacl import encoding, public
from src.utils.logger import Logger


class GitHubClient:
    """Client for GitHub API operations."""

    def __init__(self, pat: str, logger: Logger, base_url: str = "https://api.github.com"):
        """Initialize GitHub client with PAT and optional custom endpoint."""
        self.client = Github(pat, base_url=base_url)
        self.log = logger
        self.base_url = base_url
    @staticmethod
    def _encrypt_secret(public_key: str, secret_value: str) -> str:
        """Encrypt a secret value using LibSodium sealed box.

        Per GitHub API docs, secrets must be encrypted with the repository/org
        public key before being sent to the API.

        See: https://docs.github.com/en/rest/guides/encrypting-secrets-for-the-rest-api
        """
        pk = public.PublicKey(public_key.encode("utf-8"), encoding.Base64Encoder())
        sealed_box = public.SealedBox(pk)
        encrypted = sealed_box.encrypt(secret_value.encode("utf-8"))
        return b64encode(encrypted).decode("utf-8")

    def get_rate_limit_info(self) -> dict:
        """Get current rate limit information.

        Returns a dictionary with:
        - remaining: Number of API calls remaining
        - limit: Total API call limit
        - reset_time: Unix timestamp when rate limit resets
        - reset_in_seconds: Approximate seconds until reset

        This call is free - it reads from response headers of the last API call.
        """
        try:
            import time
            from datetime import datetime
            rate_limit = self.client.get_rate_limit()
            # PyGithub 2.7.0+ returns RateLimitOverview, access via resources.core
            core = rate_limit.resources.core
            reset_dt = core.reset
            # Convert datetime to timestamp if needed
            if isinstance(reset_dt, datetime):
                reset_timestamp = reset_dt.timestamp()
            else:
                reset_timestamp = reset_dt
            reset_in = max(0, reset_timestamp - time.time())
            return {
                'remaining': core.remaining,
                'limit': core.limit,
                'reset_time': reset_timestamp,
                'reset_in_seconds': int(reset_in)
            }
        except Exception as e:
            self.log.debug(f"Failed to get rate limit info: {e}")
            return {
                'remaining': -1,
                'limit': -1,
                'reset_time': -1,
                'reset_in_seconds': -1
            }

    def _log_rate_limit(self, operation: str) -> None:
        """Log current rate limit after an operation."""
        info = self.get_rate_limit_info()
        if info['remaining'] >= 0:
            self.log.debug(
                f"[{operation}] Rate limit: {info['remaining']}/{info['limit']} calls remaining "
                f"(resets in ~{info['reset_in_seconds']}s)"
            )

    def get_default_branch(self, org: str, repo: str) -> str:
        """Get the default branch of a repository."""
        try:
            repository = self.client.get_user(org).get_repo(repo)
            return repository.default_branch
        except Exception:
            raise RuntimeError(f"Failed to get repository: {org}/{repo}")

    def get_commit_sha(self, org: str, repo: str, branch: str) -> str:
        """Get the commit SHA for a given branch."""
        try:
            repository = self.client.get_user(org).get_repo(repo)
            ref = repository.get_git_ref(f"heads/{branch}")
            return ref.object.sha
        except Exception:
            raise RuntimeError(f"Failed to get commit SHA for {org}/{repo}/{branch}")

    def create_branch(self, org: str, repo: str, branch_name: str, sha: str) -> None:
        """Create a new branch in the repository."""
        try:
            repository = self.client.get_user(org).get_repo(repo)
            repository.create_git_ref(f"refs/heads/{branch_name}", sha)
            self.log.debug(f"Created branch {branch_name}")
        except Exception:
            raise RuntimeError(f"Failed to create branch {branch_name} in {org}/{repo}")

    def delete_branch(self, org: str, repo: str, branch_name: str) -> None:
        """Delete a branch from the repository."""
        try:
            repository = self.client.get_user(org).get_repo(repo)
            repository.get_git_ref(f"heads/{branch_name}").delete()
            self.log.debug(f"Deleted branch {branch_name}")
        except Exception:
            # It's okay if branch doesn't exist - we'll create it fresh
            self.log.debug(f"Branch {branch_name} will be created fresh")

    def list_repo_secrets(self, org: str, repo: str) -> List[str]:
        """List all repository-level secrets (excludes organization secrets).
        
        Uses the raw GitHub API directly instead of PyGithub's Secret objects
        to avoid IncompletableObject errors that occur when the API response
        doesn't include a URL field (common with repository-level secrets).
        
        Organization secrets are filtered out by checking for the 'visibility'
        field in the raw API response.
        """
        try:
            repository = self.client.get_repo(f"{org}/{repo}")
            
            result = []
            page = 0
            while True:
                headers, data = repository._requester.requestJsonAndCheck(
                    "GET",
                    f"/repos/{org}/{repo}/actions/secrets",
                    parameters={"per_page": 100, "page": page + 1},
                )
                secrets = data.get("secrets", [])
                if not secrets:
                    break
                
                for secret in secrets:
                    # Org secrets have a 'visibility' field; repo secrets don't
                    if 'visibility' in secret:
                        self.log.debug(f"Skipping organization secret: {secret['name']}")
                        continue
                    result.append(secret['name'])
                
                # Stop if we got fewer than a full page
                if len(secrets) < 100:
                    break
                page += 1
            
            self._log_rate_limit(f"list_repo_secrets({org}/{repo})")
            return result
        except Exception as e:
            self.log.error(f"Failed to list secrets in {org}/{repo}: {type(e).__name__}: {e}")
            raise RuntimeError(f"Failed to list secrets in {org}/{repo}: {e}")

    def create_repo_secret(self, org: str, repo: str, secret_name: str, secret_value: str) -> None:
        """Create or update a secret in the repository.

        Follows the GitHub REST API docs:
        1. GET /repos/{owner}/{repo}/actions/secrets/public-key
        2. Encrypt the value with LibSodium using the public key
        3. PUT /repos/{owner}/{repo}/actions/secrets/{secret_name}

        See: https://docs.github.com/en/rest/actions/secrets#create-or-update-a-repository-secret
        """
        try:
            repository = self.client.get_repo(f"{org}/{repo}")

            # Step 1: Get the repository public key
            _, key_data = repository._requester.requestJsonAndCheck(
                "GET", f"/repos/{org}/{repo}/actions/secrets/public-key"
            )
            public_key = key_data["key"]
            key_id = key_data["key_id"]

            # Step 2: Encrypt the secret value
            encrypted_value = self._encrypt_secret(public_key, secret_value)

            # Step 3: Create or update the secret
            repository._requester.requestJsonAndCheck(
                "PUT",
                f"/repos/{org}/{repo}/actions/secrets/{secret_name}",
                input={"encrypted_value": encrypted_value, "key_id": key_id},
            )

            self._log_rate_limit(f"create_repo_secret({org}/{repo}/{secret_name})")
            self.log.debug(f"Created/updated secret {secret_name} in {org}/{repo}")
        except Exception as e:
            self.log.error(f"Failed to create/update secret {secret_name}: {type(e).__name__}: {e}")
            raise RuntimeError(f"Failed to create/update secret {secret_name}: {e}")

    def delete_secret(self, org: str, repo: str, secret_name: str) -> None:
        """Delete a secret from the repository."""
        try:
            repository = self.client.get_repo(f"{org}/{repo}")
            secret = repository.get_secret(secret_name)
            secret.delete()
            self.log.debug(f"Deleted secret {secret_name}")
        except Exception as e:
            raise RuntimeError(f"Failed to delete secret {secret_name} from {org}/{repo}: {e}")

    def create_file(self, org: str, repo: str, branch: str, path: str, contents: str) -> None:
        """Create or update a file in the repository.

        If the file already exists on the branch, it is updated with the
        required SHA so the API does not return a 422 error.
        """
        try:
            repository = self.client.get_repo(f"{org}/{repo}")
            try:
                existing = repository.get_contents(path, ref=branch)
                repository.update_file(
                    path=path,
                    message=f"Update {path}",
                    content=contents,
                    sha=existing.sha,
                    branch=branch,
                )
                self.log.debug(f"Updated existing file {path} on branch {branch}")
            except UnknownObjectException:
                repository.create_file(
                    path=path,
                    message=f"Add {path}",
                    content=contents,
                    branch=branch,
                )
                self.log.debug(f"Created file {path} on branch {branch}")
        except Exception as e:
            raise RuntimeError(f"Failed to create file {path} in {org}/{repo} on branch {branch}: {e}")

    def list_environments(self, org: str, repo: str) -> List[str]:
        """List all environments in the repository."""
        try:
            repository = self.client.get_repo(f"{org}/{repo}")
            environments = []
            for env in repository.get_environments():
                environments.append(env.name)
            self._log_rate_limit(f"list_environments({org}/{repo})")
            return environments
        except Exception:
            self.log.debug(f"Failed to list environments in {org}/{repo}")
            return []

    def create_environment(self, org: str, repo: str, environment_name: str) -> bool:
        """Create an environment in the repository. Gracefully handles if already exists.

        Args:
            org: Organization name
            repo: Repository name
            environment_name: Name of the environment to create

        Returns:
            True if environment was created, False if it already existed
        """
        try:
            repository = self.client.get_repo(f"{org}/{repo}")

            # Check if environment already exists
            try:
                repository.get_environment(environment_name)
                self.log.debug(f"Environment '{environment_name}' already exists in {org}/{repo}, skipping creation")
                return False
            except UnknownObjectException:
                # Environment doesn't exist, proceed with creation
                pass

            # Create the environment
            repository.create_environment(environment_name)
            self._log_rate_limit(f"create_environment({org}/{repo}/{environment_name})")
            self.log.debug(f"Created environment '{environment_name}' in {org}/{repo}")
            return True
        except Exception as e:
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
                except Exception:
                    self.log.debug(f"Could not fetch secret count for environment '{env.name}'")

                env_info[env.name] = secret_count

            return env_info
        except Exception:
            self.log.debug("Failed to list environments with secret count")
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
        except Exception:
            self.log.debug(f"Could not fetch secrets for environment '{environment_name}' in {org}/{repo}")
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
                except Exception:
                    self.log.debug(f"Could not fetch secrets for environment '{env.name}'")

                env_info[env.name] = secret_names

            self._log_rate_limit(f"list_all_environments_with_secrets({org}/{repo})")
            return env_info
        except Exception:
            self.log.debug("Failed to list environments with secrets")
            return {}

    def list_org_secrets(self, org: str) -> List[str]:
        """List all secrets in the organization.

        Args:
            org: Organization name

        Returns:
            List of secret names in the organization
        """
        try:
            organization = self.client.get_organization(org)
            secrets = organization.get_secrets()
            secret_names = [secret.name for secret in secrets]
            self._log_rate_limit(f"list_org_secrets({org})")
            self.log.debug(f"Found {len(secret_names)} organization secrets in {org}")
            return secret_names
        except Exception:
            self.log.debug(f"Failed to list organization secrets in {org}")
            raise RuntimeError(f"Failed to list organization secrets in {org}")

    def create_org_secret(self, org: str, secret_name: str, secret_value: str, visibility: str = "all") -> None:
        """Create or update a secret in the organization.

        Follows the GitHub REST API docs:
        1. GET /orgs/{org}/actions/secrets/public-key
        2. Encrypt the value with LibSodium using the public key
        3. PUT /orgs/{org}/actions/secrets/{secret_name}

        Args:
            org: Organization name
            secret_name: Name of the secret
            secret_value: Value of the secret
            visibility: Secret visibility ('all', 'private', or 'selected')

        See: https://docs.github.com/en/rest/actions/secrets#create-or-update-an-organization-secret
        """
        try:
            organization = self.client.get_organization(org)

            # Step 1: Get the organization public key
            _, key_data = organization._requester.requestJsonAndCheck(
                "GET", f"/orgs/{org}/actions/secrets/public-key"
            )
            public_key = key_data["key"]
            key_id = key_data["key_id"]

            # Step 2: Encrypt the secret value
            encrypted_value = self._encrypt_secret(public_key, secret_value)

            # Step 3: Create or update the secret
            organization._requester.requestJsonAndCheck(
                "PUT",
                f"/orgs/{org}/actions/secrets/{secret_name}",
                input={
                    "encrypted_value": encrypted_value,
                    "key_id": key_id,
                    "visibility": visibility,
                },
            )

            self._log_rate_limit(f"create_org_secret({org}/{secret_name})")
            self.log.debug(f"Created/updated organization secret {secret_name} in {org}")
        except Exception as e:
            self.log.error(f"Failed to create/update organization secret {secret_name}: {type(e).__name__}: {e}")
            raise RuntimeError(f"Failed to create/update organization secret {secret_name}: {e}")

    def delete_org_secret(self, org: str, secret_name: str) -> None:
        """Delete a secret from the organization.

        Args:
            org: Organization name
            secret_name: Name of the secret to delete
        """
        try:
            organization = self.client.get_organization(org)
            secret = organization.get_secret(secret_name)
            secret.delete()
            self.log.debug(f"Deleted organization secret {secret_name} from {org}")
        except Exception as e:
            self.log.error(f"Failed to delete organization secret {secret_name}: {type(e).__name__}: {e}")
            raise RuntimeError(f"Failed to delete organization secret {secret_name}: {e}")

    def get_org_secret_scope(self, org: str, secret_name: str) -> Dict[str, Any]:
        """Get the visibility and selected repositories for an organization secret.

        Args:
            org: Organization name
            secret_name: Name of the secret

        Returns:
            Dictionary with:
            - visibility: "all", "private", or "selected"
            - selected_repositories: List of repository names (only if visibility is "selected")
        """
        try:
            organization = self.client.get_organization(org)
            secret = organization.get_secret(secret_name)

            result = {
                'visibility': secret.visibility,
                'selected_repositories': []
            }

            # Only fetch selected repositories if visibility is "selected"
            if secret.visibility == "selected":
                try:
                    repos = secret.selected_repositories
                    result['selected_repositories'] = [repo.name for repo in repos]
                    self.log.debug(f"Secret {secret_name} has {len(result['selected_repositories'])} selected repositories")
                except Exception as e:
                    self.log.debug(f"Failed to fetch selected repositories for {secret_name}: {e}")

            self._log_rate_limit(f"get_org_secret_scope({org}/{secret_name})")
            return result
        except Exception as e:
            self.log.error(f"Failed to get scope for organization secret {secret_name}: {type(e).__name__}: {e}")
            raise RuntimeError(f"Failed to get scope for organization secret {secret_name}: {e}")

    def get_org_secrets_with_scope(self, org: str) -> Dict[str, Dict[str, Any]]:
        """Get all organization secrets with their scope information.

        Args:
            org: Organization name

        Returns:
            Dictionary mapping secret names to their scope information:
            {
                'SECRET_NAME': {
                    'visibility': 'selected',
                    'selected_repositories': ['repo1', 'repo2']
                },
                ...
            }
        """
        try:
            organization = self.client.get_organization(org)
            secrets = organization.get_secrets()

            secrets_info = {}
            for secret in secrets:
                scope_info = {
                    'visibility': secret.visibility,
                    'selected_repositories': []
                }

                # Only fetch selected repositories if visibility is "selected"
                if secret.visibility == "selected":
                    try:
                        repos = secret.selected_repositories
                        scope_info['selected_repositories'] = [
                            repo.name for repo in repos
                        ]
                    except Exception as e:
                        self.log.debug(
                            f"Failed to fetch selected repositories "
                            f"for {secret.name}: {e}"
                        )

                secrets_info[secret.name] = scope_info

            self._log_rate_limit(f"get_org_secrets_with_scope({org})")
            self.log.debug(
                f"Retrieved scope information for {len(secrets_info)} "
                f"organization secrets in {org}"
            )
            return secrets_info
        except Exception as e:
            self.log.error(
                f"Failed to get organization secrets with scope: "
                f"{type(e).__name__}: {e}"
            )
            raise RuntimeError(
                f"Failed to get organization secrets with scope: {e}"
            )

    def check_repo_exists(self, org: str, repo_name: str) -> bool:
        """Check if a repository exists in the organization.

        Args:
            org: Organization name
            repo_name: Repository name to check

        Returns:
            True if repository exists, False otherwise
        """
        try:
            organization = self.client.get_organization(org)
            organization.get_repo(repo_name)
            return True
        except UnknownObjectException:
            return False
        except Exception as e:
            self.log.debug(f"Error checking if repo {repo_name} exists in {org}: {e}")
            return False

    def get_matching_repos(self, org: str, repo_names: List[str]) -> List[str]:
        """Get list of repositories that exist in the organization from a given list.

        Args:
            org: Organization name
            repo_names: List of repository names to check

        Returns:
            List of repository names that exist in the organization
        """
        matching_repos = []
        for repo_name in repo_names:
            if self.check_repo_exists(org, repo_name):
                matching_repos.append(repo_name)
                self.log.debug(f"Repository {repo_name} exists in {org}")
            else:
                self.log.debug(f"Repository {repo_name} does not exist in {org}")

        self._log_rate_limit(f"get_matching_repos({org})")
        return matching_repos
