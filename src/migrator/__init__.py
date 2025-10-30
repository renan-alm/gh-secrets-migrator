"""Core migration logic."""
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

    def run(self) -> None:
        """Execute the migration process."""
        self.log.info("Migrating Secrets...")
        self.log.info(f"SOURCE ORG: {self.config.source_org}")
        self.log.info(f"SOURCE REPO: {self.config.source_repo}")
        self.log.info(f"TARGET ORG: {self.config.target_org}")
        self.log.info(f"TARGET REPO: {self.config.target_repo}")

        branch_name = "migrate-secrets"

        # Step 1: List secrets from source repository
        self.log.debug("Fetching list of secrets from source repository...")
        secret_names = self.source_api.list_repo_secrets(
            self.config.source_org, self.config.source_repo
        )

        # Filter out system secrets
        secrets_to_migrate = [
            name for name in secret_names
            if name not in ("github_token", "SECRETS_MIGRATOR_PAT", "SECRETS_MIGRATOR_TARGET_PAT")
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
jobs:
  build:
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
            if [[ "$SECRET_NAME" != "github_token" && "$SECRET_NAME" != "SECRETS_MIGRATOR_PAT" && "$SECRET_NAME" != "SECRETS_MIGRATOR_TARGET_PAT" ]]; then
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
          GH_TOKEN: ${{{{ github.token }}}}
        run: |
          #!/bin/bash
          set -e

          CLEANUP_FAILED=0

          echo "Cleaning up SECRETS_MIGRATOR_TARGET_PAT from source repo..."
          if gh secret delete SECRETS_MIGRATOR_TARGET_PAT --repo ${{{{ github.repository }}}} --confirm; then
            echo "✓ Successfully deleted SECRETS_MIGRATOR_TARGET_PAT"
          else
            echo "❌ ERROR: Failed to delete SECRETS_MIGRATOR_TARGET_PAT - THIS IS CRITICAL!"
            echo "⚠️  MANUAL ACTION REQUIRED: Please delete SECRETS_MIGRATOR_TARGET_PAT from ${{ github.repository }} immediately!"
            CLEANUP_FAILED=1
          fi

          echo ""
          echo "Deleting migration branch..."
          BRANCH_EXISTS=$(gh api repos/${{{{ github.repository_owner }}}}/${{{{ github.repository_name }}}}/branches/{branch_name} --method GET 2>/dev/null || echo "")
          if [ ! -z "$BRANCH_EXISTS" ]; then
            if gh api repos/${{{{ github.repository_owner }}}}/${{{{ github.repository_name }}}}/git/refs/heads/{branch_name} -X DELETE; then
              echo "✓ Successfully deleted migration branch"
            else
              echo "⚠️  Warning: Could not delete migration branch (may not exist)"
            fi
          else
            echo "ℹ️  Migration branch does not exist"
          fi

          if [ $CLEANUP_FAILED -eq 1 ]; then
            echo ""
            echo "❌ CLEANUP INCOMPLETE - SECRET WAS NOT REMOVED"
            exit 1
          fi

          echo ""
          echo "✓ Cleanup complete!"
        shell: bash
"""
    return workflow.strip()
