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
        verbose: bool = False
    ):
        self.source_org = source_org
        self.source_repo = source_repo
        self.target_org = target_org
        self.target_repo = target_repo
        self.source_pat = source_pat
        self.target_pat = target_pat
        self.verbose = verbose


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
            
            # Get workflow runs for the migrate-secrets workflow
            runs = repo.get_workflow("migrate-secrets.yml").get_runs(
                branch=branch_name,
                status="in_progress"
            )
            
            # Get the most recent run
            for run in runs:
                return f"https://github.com/{self.config.source_org}/{self.config.source_repo}/actions/runs/{run.id}"
            
            # If no in_progress run found, try queued
            runs = repo.get_workflow("migrate-secrets.yml").get_runs(
                branch=branch_name,
                status="queued"
            )
            for run in runs:
                return f"https://github.com/{self.config.source_org}/{self.config.source_repo}/actions/runs/{run.id}"
            
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

        branch_name = "migrate-secrets"

        # Step 1: List secrets from source repository
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

        # Step 2: Get default branch and commit SHA
        self.log.debug("Getting default branch...")
        default_branch = self.source_api.get_default_branch(
            self.config.source_org, self.config.source_repo
        )
        self.log.debug(f"Default branch: {default_branch}")

        master_commit_sha = self.source_api.get_commit_sha(
            self.config.source_org, self.config.source_repo, default_branch
        )

        # Step 3: Delete old migration branch if it exists
        self.log.debug(f"Checking if branch {branch_name} exists...")
        self.source_api.delete_branch(
            self.config.source_org, self.config.source_repo, branch_name
        )

        # Step 4: Create target PAT secret in source repo (for workflow to access target)
        self.log.info("Creating SECRETS_MIGRATOR_TARGET_PAT in source repository...")
        self.source_api.create_repo_secret(
            self.config.source_org,
            self.config.source_repo,
            "SECRETS_MIGRATOR_TARGET_PAT",
            self.config.target_pat
        )
        self.log.debug("Successfully created SECRETS_MIGRATOR_TARGET_PAT")

        # Step 4b: Create source PAT secret in source repo (for workflow cleanup only)
        self.log.info("Creating SECRETS_MIGRATOR_SOURCE_PAT in source repository...")
        self.source_api.create_repo_secret(
            self.config.source_org,
            self.config.source_repo,
            "SECRETS_MIGRATOR_SOURCE_PAT",
            self.config.source_pat
        )
        self.log.debug("Successfully created SECRETS_MIGRATOR_SOURCE_PAT")

        # Step 5: Create migration branch
        self.log.debug(f"Creating branch {branch_name}...")
        self.source_api.create_branch(
            self.config.source_org,
            self.config.source_repo,
            branch_name,
            master_commit_sha
        )

        # Step 6: Generate and create workflow file
        workflow = generate_workflow(
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

        # Step 7: Fetch workflow run details
        self.log.debug("Waiting for workflow to be triggered...")
        time.sleep(2)  # Give GitHub a moment to detect the new push and trigger the workflow
        
        workflow_run_url = self._get_workflow_run_url(branch_name)
        if workflow_run_url:
            self.log.success(
                f"Secrets migration workflow triggered!\n"
                f"View progress: {workflow_run_url}"
            )
        else:
            self.log.success(
                f"Secrets migration in progress. Check on status at "
                f"https://github.com/{self.config.source_org}/{self.config.source_repo}/actions"
            )


def generate_workflow(target_org: str, target_repo: str, branch_name: str) -> str:
    """Generate the GitHub Actions workflow for secret migration."""
    workflow = f"""name: move-secrets
on:
  push:
    branches: [ "{branch_name}" ]
permissions:
  contents: write
  repository-projects: write
jobs:
  migrate-secrets:
    runs-on: ubuntu-latest
    steps:
      - name: Populate Secrets
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
          if gh api --method DELETE repos/${{{{ github.repository_owner }}}}/${{{{ github.repository }}}}/git/refs/heads/{branch_name}; then
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
