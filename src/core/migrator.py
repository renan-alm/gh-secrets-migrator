"""Core migration logic."""
# flake8: noqa: E501
import time
from src.clients.github import GitHubClient
from src.utils.logger import Logger
from src.core.config import MigrationConfig
from src.core.workflow_generator import generate_workflow


class Migrator:
    """Handles the secrets migration process."""

    def __init__(self, config: MigrationConfig, logger: Logger):
        self.config = config
        self.log = logger
        self.source_api = GitHubClient(config.source_pat, logger)
        self.target_api = GitHubClient(config.target_pat, logger)
    
    def _check_rate_limits(self, checkpoint: str) -> bool:
        """Check rate limits and warn if low.
        
        Args:
            checkpoint: Name of the current checkpoint for logging
            
        Returns:
            True if both APIs have sufficient rate limit (>30 calls), False otherwise
        """
        source_info = self.source_api.get_rate_limit_info()
        target_info = self.target_api.get_rate_limit_info()
        
        source_ok = source_info['remaining'] >= 0
        target_ok = target_info['remaining'] >= 0
        
        if source_ok:
            self.log.debug(
                f"[{checkpoint}] Source: {source_info['remaining']}/{source_info['limit']} calls remaining"
            )
            if source_info['remaining'] < 50:
                self.log.warn(
                    f"⚠ Source API rate limit low: {source_info['remaining']} calls remaining! "
                    f"(Resets in ~{source_info['reset_in_seconds']}s)"
                )
        
        if target_ok:
            self.log.debug(
                f"[{checkpoint}] Target: {target_info['remaining']}/{target_info['limit']} calls remaining"
            )
            if target_info['remaining'] < 50:
                self.log.warn(
                    f"⚠ Target API rate limit low: {target_info['remaining']} calls remaining! "
                    f"(Resets in ~{target_info['reset_in_seconds']}s)"
                )
        
        # Return False if either API has critically low rate limit
        return (source_info['remaining'] > 30 if source_ok else True) and \
               (target_info['remaining'] > 30 if target_ok else True)
    
    def _wait_for_rate_limit_reset(self) -> None:
        """Wait until rate limit resets if critically low (< 100 calls remaining).
        
        This prevents workflow creation when API calls are critically low,
        which would result in workflow failures. Uses x-ratelimit-reset header
        to determine exact reset time.
        """
        source_info = self.source_api.get_rate_limit_info()
        target_info = self.target_api.get_rate_limit_info()
        
        critical_threshold = 100
        wait_needed = False
        reset_in_seconds = 0
        apis_to_wait = []
        api_names = ""
        
        # Check if either API is critically low
        if source_info['remaining'] >= 0 and source_info['remaining'] < critical_threshold:
            self.log.warn(
                f"⚠️ CRITICAL: Source API has only {source_info['remaining']} calls remaining! "
                f"Waiting for rate limit reset..."
            )
            wait_needed = True
            apis_to_wait.append(("Source", source_info['reset_in_seconds']))
        
        if target_info['remaining'] >= 0 and target_info['remaining'] < critical_threshold:
            self.log.warn(
                f"⚠️ CRITICAL: Target API has only {target_info['remaining']} calls remaining! "
                f"Waiting for rate limit reset..."
            )
            wait_needed = True
            apis_to_wait.append(("Target", target_info['reset_in_seconds']))
        
        # Use the maximum reset time among all APIs that need to wait
        if wait_needed and apis_to_wait:
            reset_in_seconds = max(reset_time for _, reset_time in apis_to_wait)
            api_names = ", ".join(name for name, _ in apis_to_wait)
        
        if wait_needed and reset_in_seconds > 0:
            # Add 2 second buffer to ensure reset is complete
            total_wait = reset_in_seconds + 2
            self.log.info(
                f"{api_names} rate limit will reset in ~{reset_in_seconds}s. "
                f"Waiting to ensure stable operation...\n"
                f"This should take approximately {total_wait} seconds."
            )
            
            # Sleep in chunks and show progress
            elapsed = 0
            while elapsed < total_wait:
                remaining_wait = total_wait - elapsed
                sleep_time = min(10, remaining_wait)
                self.log.debug(
                    f"Waiting for rate limit reset... "
                    f"({remaining_wait}s remaining)"
                )
                time.sleep(sleep_time)
                elapsed += sleep_time
            
            # Final check - make sure we're past the reset time
            time.sleep(1)
            
            # Log new rate limits after reset
            source_info = self.source_api.get_rate_limit_info()
            target_info = self.target_api.get_rate_limit_info()
            
            if source_info['remaining'] >= 0:
                self.log.success(
                    f"✓ Source API rate limit reset: {source_info['remaining']}/{source_info['limit']} calls available"
                )
            if target_info['remaining'] >= 0:
                self.log.success(
                    f"✓ Target API rate limit reset: {target_info['remaining']}/{target_info['limit']} calls available"
                )
            
            self.log.success("Resuming migration...")

    def _get_workflow_run_url(self, branch_name: str, workflow_name: str = "migrate-secrets.yml") -> str:
        """Get the URL of the workflow run triggered by the push to the migration branch.
        
        Args:
            branch_name: The branch that triggered the workflow
            workflow_name: The workflow file name (default: migrate-secrets.yml)
        """
        try:
            repo = self.source_api.client.get_repo(
                f"{self.config.source_org}/{self.config.source_repo}"
            )
            
            # Try to get workflow by name
            try:
                workflow = repo.get_workflow(workflow_name)
            except Exception:
                # If workflow not found by name, try by searching in all workflows
                workflows = repo.get_workflows()
                workflow = None
                for w in workflows:
                    if workflow_name.replace(".yml", "") in w.name:
                        workflow = w
                        break
                if not workflow:
                    return ""
            
            # Try multiple statuses: in_progress, queued, completed, failure
            for status in ["in_progress", "queued", "completed", "failure"]:
                try:
                    runs = workflow.get_runs(branch=branch_name, status=status)
                    for run in runs:
                        self.log.debug(f"Found workflow run {run.id} with status {status}")
                        return f"https://github.com/{self.config.source_org}/{self.config.source_repo}/actions/runs/{run.id}"
                except Exception as status_error:
                    self.log.debug(f"No {status} runs found: {status_error}")
                    continue
            
            return ""
        except Exception as e:
            self.log.debug(f"Could not fetch workflow run details: {e}")
            return ""

    def _validate_permissions(self) -> None:
        """Validate that both PATs have necessary permissions."""
        try:
            # Check source PAT permissions
            self.log.debug("Checking source PAT permissions...")
            source_repo_path = f"{self.config.source_org}/{self.config.source_repo}"
            
            try:
                source_repo = self.source_api.client.get_repo(source_repo_path)
                self.log.debug(f"✓ Source PAT has access to {source_repo_path}")
                
                # Try to list secrets to verify permission
                secrets = source_repo.get_secrets()
                _ = list(secrets)  # Force evaluation
                self.log.debug("✓ Source PAT has permission to manage secrets")
            except Exception as source_error:
                error_msg = str(source_error)
                if "404" in error_msg or "Not Found" in error_msg:
                    raise RuntimeError(
                        f"Source repository '{source_repo_path}' not found.\n"
                        "Please verify:\n"
                        f"  - Organization name is correct: {self.config.source_org}\n"
                        f"  - Repository name is correct: {self.config.source_repo}\n"
                        "  - PAT has access to the repository"
                    )
                elif "401" in error_msg or "Unauthorized" in error_msg:
                    raise RuntimeError(
                        "Authentication failed for source repository.\n"
                        "The source PAT may be invalid, expired, or revoked.\n"
                        "Please verify your source-pat is correct."
                    )
                elif "403" in error_msg or "Resource not accessible" in error_msg:
                    raise RuntimeError(
                        "Source PAT lacks permission to manage secrets.\n"
                        "Ensure your source PAT has these scopes:\n"
                        "  - 'repo' (Full control of private repositories)\n"
                        "  - 'workflow' (Update GitHub Action workflows)"
                    )
                else:
                    raise RuntimeError(f"Cannot access source repository: {source_error}")

            # Check target PAT permissions
            self.log.debug("Checking target PAT permissions...")
            target_repo_path = f"{self.config.target_org}/{self.config.target_repo}"
            
            try:
                target_repo = self.target_api.client.get_repo(target_repo_path)
                self.log.debug(f"✓ Target PAT has access to {target_repo_path}")
                
                # Try to list secrets to verify permission
                secrets = target_repo.get_secrets()
                _ = list(secrets)  # Force evaluation
                self.log.debug("✓ Target PAT has permission to manage secrets")
            except Exception as target_error:
                error_msg = str(target_error)
                if "404" in error_msg or "Not Found" in error_msg:
                    raise RuntimeError(
                        f"Target repository '{target_repo_path}' not found.\n"
                        "Please verify:\n"
                        f"  - Organization name is correct: {self.config.target_org}\n"
                        f"  - Repository name is correct: {self.config.target_repo}\n"
                        "  - PAT has access to the repository"
                    )
                elif "401" in error_msg or "Unauthorized" in error_msg:
                    raise RuntimeError(
                        "Authentication failed for target repository.\n"
                        "The target PAT may be invalid, expired, or revoked.\n"
                        "Please verify your target-pat is correct."
                    )
                elif "403" in error_msg or "Resource not accessible" in error_msg:
                    raise RuntimeError(
                        "Target PAT lacks permission to manage secrets.\n"
                        "Ensure your target PAT has these scopes:\n"
                        "  - 'repo' (Full control of private repositories)\n"
                        "  - 'workflow' (Update GitHub Action workflows)"
                    )
                else:
                    raise RuntimeError(f"Cannot access target repository: {target_error}")

            self.log.success("All PAT permissions validated!")
            
            # Log initial rate limits
            source_info = self.source_api.get_rate_limit_info()
            target_info = self.target_api.get_rate_limit_info()
            if source_info['remaining'] >= 0:
                self.log.info(
                    f"Source API rate limit: {source_info['remaining']}/{source_info['limit']} calls remaining"
                )
            if target_info['remaining'] >= 0:
                self.log.info(
                    f"Target API rate limit: {target_info['remaining']}/{target_info['limit']} calls remaining"
                )

        except RuntimeError:
            # Re-raise our custom RuntimeErrors as-is
            raise
        except Exception as e:
            self.log.error(f"Unexpected validation error: {type(e).__name__}: {e}")
            raise RuntimeError(
                f"Unexpected error during PAT validation: {type(e).__name__}\n"
                f"Details: {e}"
            )

    def _recreate_environments(self) -> None:
        """List environments from source and recreate in target repository."""
        try:
            # List environments from source repository
            self.log.debug("Fetching list of environments from source repository...")
            environments = self.source_api.list_environments(
                self.config.source_org, self.config.source_repo
            )

            if not environments:
                self.log.info("No environments to recreate")
                return

            self.log.info(f"Environments to recreate ({len(environments)} total):")
            for env_name in environments:
                self.log.info(f"  - {env_name}")

            # Create environments in target repository
            self.log.debug("Creating environments in target repository...")
            for env_name in environments:
                try:
                    self.target_api.create_environment(
                        self.config.target_org,
                        self.config.target_repo,
                        env_name
                    )
                    self.log.debug(f"Successfully created/verified environment '{env_name}'")
                except RuntimeError as e:
                    # Only log as warning - don't fail the entire migration
                    self.log.warn(f"Environment '{env_name}' error: {e}")

            self.log.success("Environment recreation completed!")

        except Exception as e:
            self.log.error(f"Unexpected error during environment recreation: {type(e).__name__}: {e}")
            raise RuntimeError(f"Failed to recreate environments: {e}")

    def _validate_org_permissions(self) -> None:
        """Validate that both PATs have necessary permissions for organization access."""
        try:
            # Check source PAT permissions
            self.log.debug("Checking source PAT permissions for organization access...")
            try:
                source_org = self.source_api.client.get_organization(self.config.source_org)
                self.log.debug(f"✓ Source PAT has access to organization '{self.config.source_org}'")
                
                # Try to list org secrets to verify permission
                secrets = source_org.get_secrets()
                _ = list(secrets)  # Force evaluation
                self.log.debug("✓ Source PAT has permission to access organization secrets")
            except Exception as source_error:
                error_msg = str(source_error)
                if "404" in error_msg or "Not Found" in error_msg:
                    raise RuntimeError(
                        f"Source organization '{self.config.source_org}' not found.\n"
                        f"Please verify the organization name is correct."
                    )
                elif "401" in error_msg or "Unauthorized" in error_msg:
                    raise RuntimeError(
                        f"Source PAT does not have access to organization '{self.config.source_org}'.\n"
                        f"Please verify your source PAT has the necessary permissions."
                    )
                else:
                    raise RuntimeError(f"Failed to access source organization: {source_error}")

            # Check target PAT permissions
            self.log.debug("Checking target PAT permissions for organization access...")
            try:
                target_org = self.target_api.client.get_organization(self.config.target_org)
                self.log.debug(f"✓ Target PAT has access to organization '{self.config.target_org}'")
                
                # Try to list org secrets to verify permission
                secrets = target_org.get_secrets()
                _ = list(secrets)  # Force evaluation
                self.log.debug("✓ Target PAT has permission to access organization secrets")
            except Exception as target_error:
                error_msg = str(target_error)
                if "404" in error_msg or "Not Found" in error_msg:
                    raise RuntimeError(
                        f"Target organization '{self.config.target_org}' not found.\n"
                        f"Please verify the organization name is correct."
                    )
                elif "401" in error_msg or "Unauthorized" in error_msg:
                    raise RuntimeError(
                        f"Target PAT does not have access to organization '{self.config.target_org}'.\n"
                        f"Please verify your target PAT has the necessary permissions."
                    )
                else:
                    raise RuntimeError(f"Failed to access target organization: {target_error}")

            self.log.success("✓ Both PATs have necessary organization permissions")

        except RuntimeError:
            raise
        except Exception as e:
            self.log.error(f"Unexpected error during permission validation: {type(e).__name__}: {e}")
            raise RuntimeError(f"Failed to validate organization permissions: {e}")

    def _migrate_org_secrets_workflow(self) -> None:
        """Migrate organization secrets using GitHub Actions workflow.
        
        Org-to-org migration requires a source repository to host the workflow.
        If target repo is not provided, uses the same name as source repo.
        """
        self.log.info("Fetching organization secrets from source...")
        
        try:
            # Use source repo for workflow hosting, target repo defaults to source if not provided
            source_repo = self.config.source_repo
            target_repo = self.config.target_repo or self.config.source_repo
            
            # Get list of org secrets from source
            org_secret_names = self.source_api.list_org_secrets(self.config.source_org)
            
            # Filter out system secrets
            secrets_to_migrate = [
                name for name in org_secret_names
                if name not in ("SECRETS_MIGRATOR_PAT", "SECRETS_MIGRATOR_TARGET_PAT", "SECRETS_MIGRATOR_SOURCE_PAT")
            ]
            
            if not secrets_to_migrate:
                self.log.info("No organization secrets to migrate (found only system secrets)")
                return
            
            self.log.info(f"Organization secrets to migrate ({len(secrets_to_migrate)} total):")
            for name in secrets_to_migrate:
                self.log.info(f"  - {name}")
            
            branch_name = "migrate-org-secrets"
            
            # Step 1: Create temporary secrets in source repo
            self.log.info("Creating temporary secrets in source repository...")
            self.source_api.create_repo_secret(
                self.config.source_org, source_repo,
                "SECRETS_MIGRATOR_TARGET_PAT", self.config.target_pat
            )
            self.source_api.create_repo_secret(
                self.config.source_org, source_repo,
                "SECRETS_MIGRATOR_SOURCE_PAT", self.config.source_pat
            )
            
            # Step 2: Generate workflow with org secrets
            self.log.info("Generating workflow for organization secret migration...")
            workflow_content = generate_workflow(
                self.config.source_org, source_repo,
                self.config.target_org, target_repo,
                branch_name,
                env_secrets=None,
                org_secrets=secrets_to_migrate
            )
            
            # Step 3: Create migration branch and push workflow
            self.log.info(f"Creating migration branch '{branch_name}'...")
            source_repo_obj = self.source_api.client.get_repo(f"{self.config.source_org}/{source_repo}")
            
            # Get default branch
            default_branch = source_repo_obj.default_branch
            base_ref = source_repo_obj.get_git_ref(f"heads/{default_branch}")
            
            # Create new branch
            source_repo_obj.create_git_ref(f"refs/heads/{branch_name}", base_ref.object.sha)
            self.log.debug(f"✓ Created migration branch '{branch_name}'")
            
            # Create workflow file
            workflow_path = ".github/workflows/migrate-org-secrets.yml"
            self.log.debug(f"Creating workflow file at {workflow_path}...")
            
            source_repo_obj.create_file(
                workflow_path,
                "chore: add organization secrets migration workflow",
                workflow_content,
                branch=branch_name
            )
            self.log.info(f"✓ Workflow pushed to branch '{branch_name}'")
            
            # Step 4: Workflow is now running asynchronously - provide URL for monitoring
            self.log.success("✓ Workflow triggered successfully!")
            
            workflow_url = f"https://github.com/{self.config.source_org}/{self.config.source_repo}/actions/workflows/migrate-org-secrets.yml"
            self.log.success("✓ Organization secret migration started! Check the link below to monitor progress.")
            self.log.info(f"Monitor workflow progress here: {workflow_url}")
            
        except RuntimeError:
            raise
        except Exception as e:
            self.log.error(f"Error during organization secret migration: {type(e).__name__}: {e}")
            raise RuntimeError(f"Failed to migrate organization secrets: {e}")

    def run(self) -> None:
        """Execute the migration process."""
        self.log.info("Migrating Secrets...")
        
        # Handle org-to-org migration
        if self.config.org_to_org:
            self.log.info(f"SOURCE ORG: {self.config.source_org}")
            self.log.info(f"TARGET ORG: {self.config.target_org}")
            self.log.info("Mode: Organization-to-Organization (org secrets only)")
            
            # Validate PAT permissions for org access
            self.log.info("Validating PAT permissions...")
            self._validate_org_permissions()
            
            # Check if rate limit is critically low before proceeding
            self._wait_for_rate_limit_reset()
            
            # Attempt org-only migration
            self._migrate_org_secrets_workflow()
            return
        
        # Handle repo-to-repo migration (original flow)
        self.log.info(f"SOURCE ORG: {self.config.source_org}")
        self.log.info(f"SOURCE REPO: {self.config.source_repo}")
        self.log.info(f"TARGET ORG: {self.config.target_org}")
        self.log.info(f"TARGET REPO: {self.config.target_repo}")
        self.log.info("Mode: Repository-to-Repository")

        # Validate PAT permissions
        self.log.info("Validating PAT permissions...")
        self._validate_permissions()
        
        # Check if rate limit is critically low before proceeding
        self._wait_for_rate_limit_reset()

        # Step 1: Recreate environments (if not skipped)
        if not self.config.skip_envs:
            self.log.info("Recreating environments...")
            self._recreate_environments()
            self._check_rate_limits("after_env_recreation")
        else:
            self.log.info("Skipping environment recreation (--skip-envs flag set)")

        branch_name = "migrate-secrets"

        # Step 2: List secrets from source repository
        self.log.debug("Fetching list of secrets from source repository...")
        secret_names = self.source_api.list_repo_secrets(
            self.config.source_org, self.config.source_repo
        )

        # Filter out system secrets
        secrets_to_migrate = [
            name for name in secret_names
            if name not in ("github_token", "SECRETS_MIGRATOR_PAT", "SECRETS_MIGRATOR_TARGET_PAT", "SECRETS_MIGRATOR_SOURCE_PAT")
        ]

        if not secrets_to_migrate:
            self.log.info("No secrets to migrate (found only system secrets)")
            return

        self.log.info(f"Secrets to migrate ({len(secrets_to_migrate)} total):")
        for name in secrets_to_migrate:
            self.log.info(f"  - {name}")

        # Step 2b: List environment secrets from source repository (for informational purposes)
        self.log.debug("Fetching environment secrets from source repository...")
        env_secrets_info = self.source_api.list_all_environments_with_secrets(
            self.config.source_org, self.config.source_repo
        )
        
        self._check_rate_limits("after_listing_secrets")
        
        if env_secrets_info:
            self.log.info(f"Environment secrets to migrate ({len(env_secrets_info)} total):")
            for env_name, secret_names in env_secrets_info.items():
                if secret_names:
                    secret_list = ", ".join(secret_names)
                    self.log.info(f"  - {env_name}: {secret_list}")
                else:
                    self.log.info(f"  - {env_name}: (no secrets)")
        else:
            self.log.debug("No environment secrets found in source repository")

        # Step 3: Get default branch and commit SHA
        self.log.debug("Getting default branch...")
        default_branch = self.source_api.get_default_branch(
            self.config.source_org, self.config.source_repo
        )
        self.log.debug(f"Default branch: {default_branch}")

        master_commit_sha = self.source_api.get_commit_sha(
            self.config.source_org, self.config.source_repo, default_branch
        )

        # Step 4: Delete old migration branch if it exists
        self.log.debug(f"Checking if branch {branch_name} exists...")
        self.source_api.delete_branch(
            self.config.source_org, self.config.source_repo, branch_name
        )

        # Step 5: Create target PAT secret in source repo (for workflow to access target)
        self.log.info("Creating SECRETS_MIGRATOR_TARGET_PAT in source repository...")
        self.source_api.create_repo_secret(
            self.config.source_org,
            self.config.source_repo,
            "SECRETS_MIGRATOR_TARGET_PAT",
            self.config.target_pat
        )
        self.log.debug("Successfully created SECRETS_MIGRATOR_TARGET_PAT")

        # Step 5b: Create source PAT secret in source repo (for workflow cleanup only)
        self.log.info("Creating SECRETS_MIGRATOR_SOURCE_PAT in source repository...")
        self.source_api.create_repo_secret(
            self.config.source_org,
            self.config.source_repo,
            "SECRETS_MIGRATOR_SOURCE_PAT",
            self.config.source_pat
        )
        self.log.debug("Successfully created SECRETS_MIGRATOR_SOURCE_PAT")

        # Step 6: Create migration branch
        self.log.debug(f"Creating branch {branch_name}...")
        self.source_api.create_branch(
            self.config.source_org,
            self.config.source_repo,
            branch_name,
            master_commit_sha
        )
        
        self._check_rate_limits("after_branch_creation")

        # Step 7: Final rate limit check before workflow creation (most critical operation)
        self._wait_for_rate_limit_reset()

        # Step 7: Generate and create workflow file
        workflow = generate_workflow(
            self.config.source_org, self.config.source_repo,
            self.config.target_org, self.config.target_repo, branch_name,
            env_secrets_info
        )
        self.log.debug("Creating workflow file...")
        self.source_api.create_file(
            self.config.source_org,
            self.config.source_repo,
            branch_name,
            ".github/workflows/migrate-secrets.yml",
            workflow
        )

        # Step 7: Fetch workflow run details with retries
        self.log.debug("Waiting for workflow to be triggered...")
        
        workflow_run_url = ""
        max_retries = 6
        for attempt in range(max_retries):
            time.sleep(2 if attempt == 0 else 3)  # Initial 2s, then 3s between retries
            workflow_run_url = self._get_workflow_run_url(branch_name)
            if workflow_run_url:
                self.log.debug(f"Found workflow run URL on attempt {attempt + 1}")
                break
            if attempt < max_retries - 1:
                self.log.debug(f"Workflow run not yet found, retrying... (attempt {attempt + 1}/{max_retries})")
        
        if workflow_run_url:
            self.log.success(
                f"Secrets migration workflow triggered!\n"
                f"View progress: {workflow_run_url}"
            )
        else:
            # Fallback to generic actions page if we can't get the specific run
            self.log.debug("Could not find specific workflow run, using generic actions URL")
            self.log.success(
                f"Secrets migration workflow triggered!\n"
                f"View progress: https://github.com/{self.config.source_org}/{self.config.source_repo}/actions?query=branch%3Amigrate-secrets"
            )
        
        self._check_rate_limits("migration_complete")
