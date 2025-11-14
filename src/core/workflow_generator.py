"""Workflow generation for secrets migration."""
from typing import Dict, List, Optional
# flake8: noqa: E501

def generate_environment_secret_steps(env_secrets: Dict[str, List[str]], source_org: str, source_repo: str, target_org: str, target_repo: str) -> str:
    """Generate workflow steps for each environment secret.
    
    Args:
        env_secrets: Dict mapping environment names to lists of secret names
                     Example: {'production': ['DB_PASSWORD', 'API_KEY'], 'staging': ['DB_PASSWORD']}
        source_org: Source organization
        source_repo: Source repository
        target_org: Target organization
        target_repo: Target repository
        
    Returns:
        String containing all the generated workflow steps
    """
    steps = []
    
    for env_name, secret_names in env_secrets.items():
        for secret_name in secret_names:
            step = f"""      - name: Migrate {env_name} - {secret_name}
        env:
          TARGET_ORG: '{target_org}'
          TARGET_REPO: '{target_repo}'
          ENVIRONMENT: '{env_name}'
          SECRET_NAME: '{secret_name}'
          SECRET_VALUE: ${{{{ secrets.{secret_name} }}}}
          GH_TOKEN: ${{{{ secrets.SECRETS_MIGRATOR_TARGET_PAT }}}}
        run: |
          #!/bin/bash
          set -e

          echo "=========================================="
          echo "Migrating environment secret: $ENVIRONMENT - $SECRET_NAME"
          echo "=========================================="
          
          # Create secret in target environment with the value from workflow secrets
          if gh secret set "$SECRET_NAME" \\
            --body "$SECRET_VALUE" \\
            --repo "$TARGET_ORG/$TARGET_REPO" \\
            --env "$ENVIRONMENT"; then
            echo "✓ Successfully migrated '$SECRET_NAME' to $ENVIRONMENT"
          else
            echo "❌ ERROR: Failed to create secret '$SECRET_NAME' in target environment '$ENVIRONMENT'"
            exit 1
          fi
        shell: bash
"""
            steps.append(step)
    
    return "\n".join(steps)


def generate_org_secret_steps(org_secrets: List[str], target_org: str) -> str:
    """Generate workflow steps for each organization secret.
    
    Args:
        org_secrets: List of organization secret names
                     Example: ['DB_PASSWORD', 'API_KEY', 'DEPLOY_TOKEN']
        target_org: Target organization
        
    Returns:
        String containing all the generated workflow steps
    """
    steps = []
    
    for secret_name in org_secrets:
        step = f"""      - name: Migrate Org Secret - {secret_name}
        env:
          TARGET_ORG: '{target_org}'
          SECRET_NAME: '{secret_name}'
          SECRET_VALUE: ${{{{ secrets.{secret_name} }}}}
          GH_TOKEN: ${{{{ secrets.SECRETS_MIGRATOR_TARGET_PAT }}}}
        run: |
          #!/bin/bash
          set -e

          echo "=========================================="
          echo "Migrating organization secret: $SECRET_NAME"
          echo "=========================================="
          
          # Create secret in target organization with the value from workflow secrets
          if gh secret set "$SECRET_NAME" \\
            --body "$SECRET_VALUE" \\
            --org "$TARGET_ORG"; then
            echo "✓ Successfully migrated '$SECRET_NAME' to organization '$TARGET_ORG'"
          else
            echo "❌ ERROR: Failed to create secret '$SECRET_NAME' in target organization '$TARGET_ORG'"
            exit 1
          fi
        shell: bash
"""
        steps.append(step)
    
    return "\n".join(steps)


def generate_workflow(
    source_org: str, 
    source_repo: str, 
    target_org: str, 
    target_repo: str, 
    branch_name: str, 
    env_secrets: Optional[Dict[str, List[str]]] = None,
    org_secrets: Optional[List[str]] = None
) -> str:
    """Generate the GitHub Actions workflow for secret migration.
    
    Args:
        source_org: Source organization
        source_repo: Source repository
        target_org: Target organization
        target_repo: Target repository
        branch_name: Migration branch name
        env_secrets: Optional dict of environment secrets to generate dynamic steps
                     Example: {'production': ['DB_PASSWORD', 'API_KEY']}
        org_secrets: Optional list of organization secret names for org-to-org migration
                     Example: ['DB_PASSWORD', 'API_KEY', 'DEPLOY_TOKEN']
    """
    # Generate migration steps based on type
    migration_steps = ""
    
    # Repo-to-repo: include repository secrets step
    if not org_secrets:
        migration_steps = f"""      - name: Populate Repository Secrets
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
"""
    
    # Org-to-org Migration flow
    if org_secrets:
        migration_steps += generate_org_secret_steps(org_secrets, target_org)
        env_steps = ""
    else:
        # Environment secrets only for repo-to-repo migrations
        env_steps = ""
        if env_secrets:
            env_steps = generate_environment_secret_steps(env_secrets, source_org, source_repo, target_org, target_repo)
    
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
{migration_steps}
{env_steps if env_steps else '      # No environment secrets to migrate'}

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
