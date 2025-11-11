"""Core migration logic."""
import time
from typing import List
from src.github_api import GitHubClient
from src.logger import Logger


class MigrationConfig:
    """Configuration for the migration."""

    def __init__(
        self,
        source_org: str,
        source_repo: str,
        target_org: str,
        target_repo: str,
        source_pat: str,
        target_pat: str,
        verbose: bool = False,
        skip_envs: bool = False
    ):
        self.source_org = source_org
        self.source_repo = source_repo
        self.target_org = target_org
        self.target_repo = target_repo
        self.source_pat = source_pat
        self.target_pat = target_pat
        self.verbose = verbose
        self.skip_envs = skip_envs

class Migrator:
    """Handles the secrets migration process."""

    def __init__(self, config: MigrationConfig, logger: Logger):
        self.config = config
        self.log = logger
        self.source_api = GitHubClient(config.source_pat, logger)
        self.target_api = GitHubClient(config.target_pat, logger)

    def _get_workflow_run_url(self, branch_name: str) -> str:
        """Get the URL of the workflow run triggered by the push to the migration branch."""
        try:
            repo = self.source_api.client.get_repo(
                f"{self.config.source_org}/{self.config.source_repo}"
            )
            
            # Try to get workflow by name
            try:
                workflow = repo.get_workflow("migrate-secrets.yml")
            except Exception:
                # If workflow not found by name, try by ID or get first workflow
                workflows = repo.get_workflows()
                workflow = None
                for w in workflows:
                    if "migrate-secrets" in w.name:
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
                        f"Please verify:\n"
                        f"  - Organization name is correct: {self.config.source_org}\n"
                        f"  - Repository name is correct: {self.config.source_repo}\n"
                        f"  - PAT has access to the repository"
                    )
                elif "401" in error_msg or "Unauthorized" in error_msg:
                    raise RuntimeError(
                        f"Authentication failed for source repository.\n"
                        f"The source PAT may be invalid, expired, or revoked.\n"
                        f"Please verify your source-pat is correct."
                    )
                elif "403" in error_msg or "Resource not accessible" in error_msg:
                    raise RuntimeError(
                        f"Source PAT lacks permission to manage secrets.\n"
                        f"Ensure your source PAT has these scopes:\n"
                        f"  - 'repo' (Full control of private repositories)\n"
                        f"  - 'workflow' (Update GitHub Action workflows)"
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
                        f"Please verify:\n"
                        f"  - Organization name is correct: {self.config.target_org}\n"
                        f"  - Repository name is correct: {self.config.target_repo}\n"
                        f"  - PAT has access to the repository"
                    )
                elif "401" in error_msg or "Unauthorized" in error_msg:
                    raise RuntimeError(
                        f"Authentication failed for target repository.\n"
                        f"The target PAT may be invalid, expired, or revoked.\n"
                        f"Please verify your target-pat is correct."
                    )
                elif "403" in error_msg or "Resource not accessible" in error_msg:
                    raise RuntimeError(
                        f"Target PAT lacks permission to manage secrets.\n"
                        f"Ensure your target PAT has these scopes:\n"
                        f"  - 'repo' (Full control of private repositories)\n"
                        f"  - 'workflow' (Update GitHub Action workflows)"
                    )
                else:
                    raise RuntimeError(f"Cannot access target repository: {target_error}")

            self.log.success("All PAT permissions validated!")

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


    def run(self) -> None:
        """Execute the migration process."""
        self.log.info("Migrating Secrets...")
        self.log.info(f"SOURCE ORG: {self.config.source_org}")
        self.log.info(f"SOURCE REPO: {self.config.source_repo}")
        self.log.info(f"TARGET ORG: {self.config.target_org}")
        self.log.info(f"TARGET REPO: {self.config.target_repo}")

        # Validate PAT permissions
        self.log.info("Validating PAT permissions...")
        self._validate_permissions()

        # Step 1: Recreate environments (if not skipped)
        if not self.config.skip_envs:
            self.log.info("Recreating environments...")
            self._recreate_environments()
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
        env_secrets_info = self.source_api.list_environment_names_with_secret_count(
            self.config.source_org, self.config.source_repo
        )
        
        if env_secrets_info:
            self.log.info(f"Environment secrets to migrate ({len(env_secrets_info)} total):")
            for env_name, secret_count in env_secrets_info.items():
                self.log.info(f"  - {env_name} ({secret_count} secrets)")
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

        # Step 7: Generate and create workflow file
        workflow = generate_workflow(
            self.config.source_org, self.config.source_repo, 
            self.config.target_org, self.config.target_repo, branch_name
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


def generate_workflow(source_org: str, source_repo: str, target_org: str, target_repo: str, branch_name: str) -> str:
    """Generate the GitHub Actions workflow for secret migration."""
    workflow = f"""name: move-secrets
on:
  push:
    branches: [ "{branch_name}" ]
permissions:
  contents: write
  repository-projects: write
jobs:
  migrate-repo-secrets:
    runs-on: ubuntu-latest
    steps:
      - name: Populate Repository Secrets
        id: migrate
        env:
          REPO_SECRETS: ${{{{ toJSON(secrets) }}}}
          TARGET_ORG: '{target_org}'
          TARGET_REPO: '{target_repo}'
          GH_TOKEN: ${{{{ secrets.SECRETS_MIGRATOR_TARGET_PAT }}}}
        run: |
          #!/bin/bash
          set -e

          MIGRATION_FAILED=0

          echo "Populating secrets in target repository..."
          echo "$REPO_SECRETS" | jq -r 'to_entries[] | "\\(.key)|\\(.value)"' | while IFS='|' read -r SECRET_NAME SECRET_VALUE; do
            if [[ "$SECRET_NAME" != "github_token" && "$SECRET_NAME" != "SECRETS_MIGRATOR_PAT" && "$SECRET_NAME" != "SECRETS_MIGRATOR_TARGET_PAT" && "$SECRET_NAME" != "SECRETS_MIGRATOR_SOURCE_PAT" ]]; then
              echo "Processing: $SECRET_NAME"
              
              # Echo secret, reverse twice, and capture output
              FINAL_VALUE=$(echo "$SECRET_VALUE" | rev | rev)
              
              # Create secret in target repo using target PAT
              if gh secret set "$SECRET_NAME" \\
                --body "$FINAL_VALUE" \\
                --repo "$TARGET_ORG/$TARGET_REPO"; then
                echo "✓ Created '$SECRET_NAME' in target repo"
              else
                echo "❌ ERROR: Failed to create secret $SECRET_NAME"
                MIGRATION_FAILED=1
              fi
            fi
          done

          if [ $MIGRATION_FAILED -eq 1 ]; then
            echo ""
            echo "❌ MIGRATION FAILED - Some secrets could not be created"
            echo "⚠️  The SECRETS_MIGRATOR_TARGET_PAT MUST be manually deleted from source repo!"
            exit 1
          fi

          echo "✓ All secrets migrated successfully!"
        shell: bash

      - name: Cleanup (Always)
        if: always()
        env:
          GH_TOKEN: ${{{{ secrets.SECRETS_MIGRATOR_SOURCE_PAT }}}}
          GITHUB_TOKEN: ${{{{ secrets.SECRETS_MIGRATOR_SOURCE_PAT }}}}
        run: |
          #!/bin/bash
          set -e

          CLEANUP_FAILED=0

          echo "Cleaning up temporary secrets from source repo..."
          
          if gh secret delete SECRETS_MIGRATOR_TARGET_PAT --repo ${{{{ github.repository }}}}; then
            echo "✓ Successfully deleted SECRETS_MIGRATOR_TARGET_PAT"
          else
            echo "ERROR: Failed to delete SECRETS_MIGRATOR_TARGET_PAT - THIS IS CRITICAL!"
            CLEANUP_FAILED=1
          fi

          if gh secret delete SECRETS_MIGRATOR_SOURCE_PAT --repo ${{{{ github.repository }}}}; then
            echo "✓ Successfully deleted SECRETS_MIGRATOR_SOURCE_PAT"
          else
            echo "ERROR: Failed to delete SECRETS_MIGRATOR_SOURCE_PAT - THIS IS CRITICAL!"
            CLEANUP_FAILED=1
          fi

          if [ $CLEANUP_FAILED -eq 1 ]; then
            echo ""
            echo "MANUAL ACTION REQUIRED: Please delete remaining temporary secrets from ${{{{ github.repository }}}}"
            echo "  - SECRETS_MIGRATOR_TARGET_PAT"
            echo "  - SECRETS_MIGRATOR_SOURCE_PAT"
          fi

          echo ""
          echo "Deleting migration branch..."
          if gh api --method DELETE repos/${{{{ github.repository }}}}/git/refs/heads/{branch_name}; then
            echo "✓ Successfully deleted migration branch"
          else
            echo "ERROR: Failed to delete migration branch {branch_name}"
            CLEANUP_FAILED=1
          fi

          if [ $CLEANUP_FAILED -eq 1 ]; then
            echo ""
            echo "ERROR: CLEANUP INCOMPLETE"
            if [ ! -z "$CLEANUP_FAILED" ]; then
              echo "MANUAL ACTION REQUIRED:"
              echo "  - Delete temporary secrets from ${{{{ github.repository }}}}"
              echo "  - Delete migration branch '{branch_name}'"
            fi
            exit 1
          fi

          echo ""
          echo "✓ Cleanup complete!"
        shell: bash
"""
    return workflow.strip()
