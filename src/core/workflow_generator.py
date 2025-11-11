"""Workflow generation for secrets migration."""


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

      - name: Migrate Environment Secrets
        env:
          SOURCE_ORG: '{source_org}'
          SOURCE_REPO: '{source_repo}'
          TARGET_ORG: '{target_org}'
          TARGET_REPO: '{target_repo}'
          SOURCE_PAT: ${{{{ secrets.SECRETS_MIGRATOR_SOURCE_PAT }}}}
          GH_TOKEN: ${{{{ secrets.SECRETS_MIGRATOR_TARGET_PAT }}}}
        run: |
          #!/bin/bash
          set -e

          echo "Collecting environments from source repository..."
          
          # Get list of environments and convert directly to JSON array
          JSON_ENVS=$(GH_TOKEN=$SOURCE_PAT gh api repos/$SOURCE_ORG/$SOURCE_REPO/environments 2>/dev/null | jq -c '[.environments[].name]' || echo "[]")
          
          echo "Found environments: $JSON_ENVS"
          
          # Parse JSON array and iterate through environments
          if [ "$JSON_ENVS" = "[]" ]; then
            echo "ℹ️  No environments to process"
            exit 0
          fi
          
          echo "$JSON_ENVS" | jq -r '.[]' | while read -r ENVIRONMENT; do
            echo ""
            echo "=========================================="
            echo "Processing environment: $ENVIRONMENT"
            echo "=========================================="
            
            # List secrets available in this environment
            echo "Secret names:"
            ENV_SECRETS=$(gh api repos/$TARGET_ORG/$TARGET_REPO/environments/$ENVIRONMENT/secrets 2>/dev/null | jq -c '[.secrets[].name]' || echo "[]")
            echo "$ENV_SECRETS" | jq -r '.[]' || true'
            
          done
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
          if gh api --method DELETE repos/${{{{ github.repository }}}}/git/refs/heads/{branch_name} 2>/dev/null; then
            echo "✓ Successfully deleted migration branch"
          else
            echo "ℹ️  Migration branch already deleted or does not exist (this is okay)"
          fi

          if [ $CLEANUP_FAILED -eq 1 ]; then
            echo ""
            echo "ERROR: CLEANUP INCOMPLETE"
            if [ ! -z "$CLEANUP_FAILED" ]; then
              echo "MANUAL ACTION REQUIRED:"
              echo "  - Delete temporary secrets from ${{{{ github.repository }}}}"
            fi
            exit 1
          fi

          echo ""
          echo "✓ Cleanup complete!"
        shell: bash
"""
    return workflow.strip()
