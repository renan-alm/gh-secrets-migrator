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


def generate_org_secret_steps(org_secrets: List[str], target_org: str, repo_visibility_map: Optional[Dict[str, Dict]] = None) -> str:
    """Generate workflow steps for each organization secret.
    
    Args:
        org_secrets: List of organization secret names
                     Example: ['DB_PASSWORD', 'API_KEY', 'DEPLOY_TOKEN']
        target_org: Target organization
        repo_visibility_map: Optional dict mapping secret names to their visibility settings
                            Example: {'SECRET1': {'visibility': 'selected', 'repos': ['repo1', 'repo2']}}
        
    Returns:
        String containing all the generated workflow steps
    """
    steps = []
    
    for secret_name in org_secrets:
        # Check if we have visibility information for this secret
        visibility_info = repo_visibility_map.get(secret_name) if repo_visibility_map else None
        
        if visibility_info and visibility_info.get('visibility') == 'selected':
            # Secret with selected repositories
            repos = visibility_info.get('repos', [])
            repos_json = ' '.join([f'"{r}"' for r in repos])
            
            step = """      - name: Migrate Org Secret - """ + secret_name + """ (selected repos)
        env:
          TARGET_ORG: '""" + target_org + """'
          SECRET_NAME: '""" + secret_name + """'
          SECRET_VALUE: ${{ secrets.""" + secret_name + """ }}
          GH_TOKEN: ${{ secrets.SECRETS_MIGRATOR_TARGET_PAT }}
          SELECTED_REPOS: '""" + " ".join(repos) + """'
        run: |
          #!/bin/bash
          set -e

          echo "=========================================="
          echo "Migrating organization secret: $SECRET_NAME (selected repositories)"
          echo "=========================================="
          
          # Create secret in target organization with selected repository visibility
          # Note: gh secret set for org doesn't support --repos directly via CLI
          # We'll need to use GitHub API directly via gh api
          
          # First, get repository IDs
          REPO_IDS=()
          for repo in $SELECTED_REPOS; do
            echo "Getting ID for repository: $repo"
            repo_id=$(gh api "/repos/$TARGET_ORG/$repo" --jq '.id' 2>&1)
            if [ $? -eq 0 ]; then
              REPO_IDS+=($repo_id)
              echo "✓ Found repository ID: $repo_id for $repo"
            else
              echo "⚠️  Warning: Repository '$repo' not found in organization '$TARGET_ORG'"
            fi
          done
          
          if [ ${#REPO_IDS[@]} -eq 0 ]; then
            echo "❌ ERROR: No valid repositories found. Cannot create secret with empty repository list."
            exit 1
          fi
          
          # Build JSON array of repository IDs using jq for proper formatting (compact output)
          REPO_IDS_JSON=$(printf '%s\\n' "${REPO_IDS[@]}" | jq -Rs -c 'split("\\n") | map(select(length > 0) | tonumber)')
          
          echo "Creating org secret with visibility 'selected' with repository IDs: $REPO_IDS_JSON"
          
          # Get org public key for encryption
          KEY_RESPONSE=$(gh api "/orgs/$TARGET_ORG/actions/secrets/public-key")
          KEY_ID=$(echo "$KEY_RESPONSE" | jq -r '.key_id')
          PUBLIC_KEY=$(echo "$KEY_RESPONSE" | jq -r '.key')
          
          # Encrypt the secret and create JSON payload using Python
          python3 scripts/encrypt_org_secret_selected.py
          
          # Create/update the secret via API using the JSON payload
          gh api --method PUT "/orgs/$TARGET_ORG/actions/secrets/$SECRET_NAME" --input /tmp/payload.json
          
          if [ $? -eq 0 ]; then
            echo "✓ Successfully migrated '$SECRET_NAME' to organization '$TARGET_ORG' with selected repository visibility"
          else
            echo "❌ ERROR: Failed to create secret '$SECRET_NAME' in target organization '$TARGET_ORG'"
            exit 1
          fi
        shell: bash
"""
        else:
            # Standard org secret (all or private visibility)
            visibility = visibility_info.get('visibility', 'all') if visibility_info else 'all'
            
            step = """      - name: Migrate Org Secret - """ + secret_name + """
        env:
          TARGET_ORG: '""" + target_org + """'
          SECRET_NAME: '""" + secret_name + """'
          SECRET_VALUE: ${{ secrets.""" + secret_name + """ }}
          GH_TOKEN: ${{ secrets.SECRETS_MIGRATOR_TARGET_PAT }}
          VISIBILITY: '""" + visibility + """'
        run: |
          #!/bin/bash
          set -e

          echo "=========================================="
          echo "Migrating organization secret: $SECRET_NAME (visibility: $VISIBILITY)"
          echo "=========================================="
          
          # Get org public key for encryption
          KEY_RESPONSE=$(gh api "/orgs/$TARGET_ORG/actions/secrets/public-key")
          KEY_ID=$(echo "$KEY_RESPONSE" | jq -r '.key_id')
          PUBLIC_KEY=$(echo "$KEY_RESPONSE" | jq -r '.key')
          
          # Encrypt the secret and create JSON payload using Python
          python3 scripts/encrypt_org_secret.py
          
          # Create/update the secret via API with visibility setting
          if gh api --method PUT "/orgs/$TARGET_ORG/actions/secrets/$SECRET_NAME" --input /tmp/payload.json; then
            echo "✓ Successfully migrated '$SECRET_NAME' to organization '$TARGET_ORG' with visibility '$VISIBILITY'"
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
    org_secrets: Optional[List[str]] = None,
    org_secret_visibility: Optional[Dict[str, Dict]] = None,
    secrets_needing_cleanup: Optional[List[str]] = None
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
        org_secret_visibility: Optional dict mapping secret names to visibility settings
                              Example: {'SECRET1': {'visibility': 'selected', 'repos': ['repo1']}}
        secrets_needing_cleanup: Optional list of secret names that had temporary repository access granted
                                Example: ['SECRET1', 'SECRET2']
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
        migration_steps += generate_org_secret_steps(org_secrets, target_org, org_secret_visibility)
        env_steps = ""
    else:
        # Environment secrets only for repo-to-repo migrations
        env_steps = ""
        if env_secrets:
            env_steps = "\n" + generate_environment_secret_steps(env_secrets, source_org, source_repo, target_org, target_repo)
    
    # Generate cleanup code for temporary repository access
    cleanup_temp_access_step = ""
    if secrets_needing_cleanup:
        cleanup_code = ""
        for secret_name in secrets_needing_cleanup:
            cleanup_code += f"""          echo "Removing access for secret: {secret_name}"
          gh api --method DELETE "/orgs/$SOURCE_ORG/actions/secrets/{secret_name}/repositories/$(gh api '/repos/$SOURCE_ORG/$SOURCE_REPO' --jq '.id')" || echo "⚠️  Could not remove access (may already be removed)"
"""
        
        cleanup_temp_access_step = f"""      - name: Cleanup Temporary Repository Access from Org Secrets (Always)
        if: always()
        env:
          GH_TOKEN: ${{{{ secrets.SECRETS_MIGRATOR_SOURCE_PAT }}}}
          SOURCE_ORG: '{source_org}'
          SOURCE_REPO: '{source_repo}'
        run: |
          #!/bin/bash
          set +e
          
          echo "Removing temporary repository access from org secrets..."
          
          SOURCE_REPO_ID=$(gh api '/repos/$SOURCE_ORG/$SOURCE_REPO' --jq '.id' 2>/dev/null)
          
          if [ -z "$SOURCE_REPO_ID" ]; then
            echo "⚠️  Could not determine source repository ID"
          else
{cleanup_code}
          fi

"""
    
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
    strategy:
      matrix:
        python-version: ['3.11']
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
        
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: ${{{{ matrix.python-version }}}}
          
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          # pip install -r scripts/requirements.txt
{migration_steps}{env_steps}
{cleanup_temp_access_step}      - name: Cleanup Temporary Secrets (Always)
        if: always()
        env:
          GH_TOKEN: ${{{{ secrets.SECRETS_MIGRATOR_SOURCE_PAT }}}}
          GITHUB_TOKEN: ${{{{ secrets.SECRETS_MIGRATOR_SOURCE_PAT }}}}
          SOURCE_ORG: '{source_org}'
          SOURCE_REPO: '{source_repo}'
        run: |
          #!/bin/bash
          set +e

          CLEANUP_FAILED=0

          echo "Cleaning up temporary secrets from source repo..."
          
          if gh secret delete SECRETS_MIGRATOR_TARGET_PAT --repo ${{{{ github.repository }}}} 2>/dev/null; then
            echo "✓ Successfully deleted SECRETS_MIGRATOR_TARGET_PAT"
          else
            echo "❌ ERROR: Failed to delete SECRETS_MIGRATOR_TARGET_PAT - THIS IS CRITICAL!"
            CLEANUP_FAILED=1
          fi

          if gh secret delete SECRETS_MIGRATOR_SOURCE_PAT --repo ${{{{ github.repository }}}} 2>/dev/null; then
            echo "✓ Successfully deleted SECRETS_MIGRATOR_SOURCE_PAT"
          else
            echo "❌ ERROR: Failed to delete SECRETS_MIGRATOR_SOURCE_PAT - THIS IS CRITICAL!"
            CLEANUP_FAILED=1
          fi

          if [ $CLEANUP_FAILED -eq 1 ]; then
            echo ""
            echo "❌ CLEANUP INCOMPLETE - MANUAL ACTION REQUIRED!"
            echo "⚠️  CRITICAL: Temporary secrets were NOT successfully deleted from the source repository!"
            echo "Please manually delete the following secrets from ${{{{ github.repository }}}}:"
            echo "  - SECRETS_MIGRATOR_TARGET_PAT"
            echo "  - SECRETS_MIGRATOR_SOURCE_PAT"
            echo ""
            echo "These secrets contain access tokens and must be removed to prevent unauthorized access!"
            exit 1
          fi

          echo "✓ Temporary secrets cleanup complete!"
        shell: bash

      - name: Cleanup Migration Branch (Always)
        if: always()
        env:
          GH_TOKEN: ${{{{ secrets.SECRETS_MIGRATOR_SOURCE_PAT }}}}
        run: |
          #!/bin/bash
          set +e

          echo "Deleting migration branch..."
          if gh api --method DELETE repos/${{{{ github.repository }}}}/git/refs/heads/{branch_name} 2>/dev/null; then
            echo "✓ Successfully deleted migration branch"
          else
            echo "ℹ️  Migration branch already deleted or does not exist (this is okay)"
          fi

          echo "✓ Migration branch cleanup complete!"
        shell: bash
"""
    return workflow.strip()
