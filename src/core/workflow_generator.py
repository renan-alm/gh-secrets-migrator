"""Workflow generation for secrets migration."""
from typing import Dict, List, Optional
from urllib.parse import urlparse
# flake8: noqa: E501

# Default GitHub API endpoint
DEFAULT_GITHUB_ENDPOINT = "https://api.github.com"


def normalize_endpoint(endpoint: str) -> str:
    """Normalize an endpoint URL by removing trailing slashes and ensuring consistent format.
    
    Args:
        endpoint: GitHub API endpoint URL
        
    Returns:
        Normalized endpoint URL
        
    Examples:
        >>> normalize_endpoint('https://api.github.com/')
        'https://api.github.com'
        >>> normalize_endpoint('https://api.github.com')
        'https://api.github.com'
    """
    return endpoint.rstrip("/")


def extract_gh_host(endpoint: str) -> str:
    """Extract hostname from API endpoint for GH_HOST environment variable.
    
    GH_HOST should be just the hostname (and optional port), without any path.
    
    Args:
        endpoint: GitHub API endpoint URL
        
    Returns:
        Hostname for GH_HOST (e.g., 'api.github.com', 'github.example.com:8080')
    
    Examples:
        >>> extract_gh_host('https://api.github.com')
        'api.github.com'
        >>> extract_gh_host('https://us.api.github.com')
        'us.api.github.com'
        >>> extract_gh_host('https://github.example.com/api/v3')
        'github.example.com'
        >>> extract_gh_host('http://localhost:8080/api/v3')
        'localhost:8080'
    """
    parsed = urlparse(endpoint)
    return parsed.netloc


def should_set_gh_host(endpoint: str) -> bool:
    """Check if GH_HOST should be set for the given endpoint.
    
    Normalizes endpoints before comparison to handle equivalent URLs.
    
    Args:
        endpoint: GitHub API endpoint URL
        
    Returns:
        True if GH_HOST should be set (non-default endpoint), False otherwise
    """
    return normalize_endpoint(endpoint) != DEFAULT_GITHUB_ENDPOINT


def derive_web_host(api_endpoint: str) -> str:
    """Derive the web host URL from an API endpoint.
    
    For standard GitHub.com and GHEC Data Residency:
    - https://api.github.com -> https://github.com
    - https://us.api.github.com -> https://us.github.com
    - https://eu.api.github.com -> https://eu.github.com
    
    For GHES:
    - https://github.example.com/api/v3 -> https://github.example.com
    
    Args:
        api_endpoint: GitHub API endpoint URL
        
    Returns:
        Web host URL for constructing user-facing links
    """
    parsed = urlparse(api_endpoint)
    
    # For standard github.com and GHEC Data Residency, replace api. prefix
    if parsed.hostname and parsed.hostname.endswith(".github.com"):
        # Remove 'api.' prefix if present
        web_hostname = parsed.hostname.replace("api.", "", 1)
        return f"{parsed.scheme}://{web_hostname}"
    
    # For GHES or other deployments, use the base URL without path
    return f"{parsed.scheme}://{parsed.netloc}"


def generate_environment_secret_steps(env_secrets: Dict[str, List[str]], source_org: str, source_repo: str, target_org: str, target_repo: str, target_endpoint: str = DEFAULT_GITHUB_ENDPOINT) -> str:
    """Generate workflow steps for each environment secret.
    
    Args:
        env_secrets: Dict mapping environment names to lists of secret names
                     Example: {'production': ['DB_PASSWORD', 'API_KEY'], 'staging': ['DB_PASSWORD']}
        source_org: Source organization
        source_repo: Source repository
        target_org: Target organization
        target_repo: Target repository
        target_endpoint: Target GitHub API endpoint (default: https://api.github.com)
        
    Returns:
        String containing all the generated workflow steps
    """
    steps = []
    
    # Extract hostname from API endpoint for GH_HOST
    gh_host = extract_gh_host(target_endpoint)
    gh_env_vars = f"GH_HOST: '{gh_host}'" if should_set_gh_host(target_endpoint) else ""
    
    for env_name, secret_names in env_secrets.items():
        for secret_name in secret_names:
            # Build env section with optional GH_HOST
            env_lines = [
                f"          TARGET_ORG: '{target_org}'",
                f"          TARGET_REPO: '{target_repo}'",
                f"          ENVIRONMENT: '{env_name}'",
                f"          SECRET_NAME: '{secret_name}'",
                f"          SECRET_VALUE: ${{{{ secrets.{secret_name} }}}}",
                f"          GH_TOKEN: ${{{{ secrets.SECRETS_MIGRATOR_TARGET_PAT }}}}"
            ]
            if gh_env_vars:
                env_lines.append(f"          {gh_env_vars}")
            
            env_section = "\n".join(env_lines)
            
            step = f"""      - name: Migrate {env_name} - {secret_name}
        env:
{env_section}
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


def generate_org_secret_steps(org_secrets: List[str], target_org: str, target_endpoint: str = DEFAULT_GITHUB_ENDPOINT) -> str:
    """Generate workflow steps for each organization secret.
    
    Args:
        org_secrets: List of organization secret names
                     Example: ['DB_PASSWORD', 'API_KEY', 'DEPLOY_TOKEN']
        target_org: Target organization
        target_endpoint: Target GitHub API endpoint (default: https://api.github.com)
        
    Returns:
        String containing all the generated workflow steps
    """
    steps = []
    
    # Extract hostname from API endpoint for GH_HOST
    gh_host = extract_gh_host(target_endpoint)
    gh_env_vars = f"GH_HOST: '{gh_host}'" if should_set_gh_host(target_endpoint) else ""
    
    for secret_name in org_secrets:
        # Build env section with optional GH_HOST
        env_lines = [
            f"          TARGET_ORG: '{target_org}'",
            f"          SECRET_NAME: '{secret_name}'",
            f"          SECRET_VALUE: ${{{{ secrets.{secret_name} }}}}",
            f"          GH_TOKEN: ${{{{ secrets.SECRETS_MIGRATOR_TARGET_PAT }}}}"
        ]
        if gh_env_vars:
            env_lines.append(f"          {gh_env_vars}")
        
        env_section = "\n".join(env_lines)
        
        step = f"""      - name: Migrate Org Secret - {secret_name}
        env:
{env_section}
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


def generate_repo_secret_steps(repo_secrets: List[str], target_org: str, target_repo: str, target_endpoint: str = DEFAULT_GITHUB_ENDPOINT) -> str:
    """Generate workflow steps for each repository secret.
    
    Args:
        repo_secrets: List of repository secret names
        target_org: Target organization
        target_repo: Target repository
        target_endpoint: Target GitHub API endpoint (default: https://api.github.com)
        
    Returns:
        String containing all the generated workflow steps
    """
    steps = []
    
    # Extract hostname from API endpoint for GH_HOST
    gh_host = extract_gh_host(target_endpoint)
    gh_env_vars = f"GH_HOST: '{gh_host}'" if should_set_gh_host(target_endpoint) else ""
    
    for secret_name in repo_secrets:
        # Skip system secrets
        if secret_name in ["github_token", "SECRETS_MIGRATOR_PAT", "SECRETS_MIGRATOR_TARGET_PAT", "SECRETS_MIGRATOR_SOURCE_PAT"]:
            continue

        # Create a display name with spaces to prevent GitHub masking if the name matches a value
        display_name = " ".join(secret_name)

        # Build env section with optional GH_HOST
        env_lines = [
            f"          TARGET_ORG: '{target_org}'",
            f"          TARGET_REPO: '{target_repo}'",
            f"          SECRET_NAME: '{secret_name}'",
            f"          SECRET_VALUE: ${{{{ secrets.{secret_name} }}}}",
            f"          GH_TOKEN: ${{{{ secrets.SECRETS_MIGRATOR_TARGET_PAT }}}}"
        ]
        if gh_env_vars:
            env_lines.append(f"          {gh_env_vars}")
        
        env_section = "\n".join(env_lines)

        step = f"""      - name: Migrate Repo Secret - {secret_name}
        env:
{env_section}
        run: |
          #!/bin/bash
          set -e

          echo "=========================================="
          echo "Migrating repository secret: {display_name}"
          echo "=========================================="
          
          # Create secret in target repo
          if gh secret set "$SECRET_NAME" \\
            --body "$SECRET_VALUE" \\
            --repo "$TARGET_ORG/$TARGET_REPO"; then
            echo "✓ Successfully migrated '{display_name}' to target repo"
          else
            echo "❌ ERROR: Failed to create secret '{display_name}'"
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
    repo_secrets: Optional[List[str]] = None,
    source_endpoint: str = DEFAULT_GITHUB_ENDPOINT,
    target_endpoint: str = DEFAULT_GITHUB_ENDPOINT
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
        repo_secrets: Optional list of repository secret names for repo-to-repo migration
                     Example: ['DB_PASSWORD', 'API_KEY', 'DEPLOY_TOKEN']
                     If provided, only these secrets will be migrated (excludes org secrets)
        source_endpoint: Source GitHub API endpoint (default: https://api.github.com)
        target_endpoint: Target GitHub API endpoint (default: https://api.github.com)
    """
    # Generate migration steps based on type
    migration_steps = ""
    
    # Repo-to-repo: include repository secrets step
    if not org_secrets:
        if repo_secrets is not None:
            migration_steps = generate_repo_secret_steps(repo_secrets, target_org, target_repo, target_endpoint)
        else:
            # Extract hostname from API endpoint for GH_HOST
            gh_host = extract_gh_host(target_endpoint)
            gh_env_vars = f"\n          GH_HOST: '{gh_host}'" if should_set_gh_host(target_endpoint) else ""
            
            migration_steps = f"""      - name: Populate Repository Secrets
        id: migrate
        env:
          REPO_SECRETS: ${{{{ toJSON(secrets) }}}}
          TARGET_ORG: '{target_org}'
          TARGET_REPO: '{target_repo}'
          GH_TOKEN: ${{{{ secrets.SECRETS_MIGRATOR_TARGET_PAT }}}}{gh_env_vars}
        run: |
          #!/bin/bash
          set -e

          MIGRATION_FAILED=0

          echo "Populating secrets in target repository..."
          echo "$REPO_SECRETS" | jq -r 'to_entries[] | "\\(.key)|\\(.value)"' | while IFS='|' read -r SECRET_NAME SECRET_VALUE; do
            # Skip system secrets
            if [[ "$SECRET_NAME" == "github_token" || "$SECRET_NAME" == "SECRETS_MIGRATOR_PAT" || "$SECRET_NAME" == "SECRETS_MIGRATOR_TARGET_PAT" || "$SECRET_NAME" == "SECRETS_MIGRATOR_SOURCE_PAT" ]]; then
              continue
            fi

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
        migration_steps += generate_org_secret_steps(org_secrets, target_org, target_endpoint)
        env_steps = ""
    else:
        # Environment secrets only for repo-to-repo migrations
        env_steps = ""
        if env_secrets:
            env_steps = generate_environment_secret_steps(env_secrets, source_org, source_repo, target_org, target_repo, target_endpoint)
    
    # Extract hostname from API endpoint for GH_HOST (for cleanup step)
    gh_host_source = extract_gh_host(source_endpoint)
    gh_env_vars_cleanup = f"\n          GH_HOST: '{gh_host_source}'" if should_set_gh_host(source_endpoint) else ""
    
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
          GITHUB_TOKEN: ${{{{ secrets.SECRETS_MIGRATOR_SOURCE_PAT }}}}{gh_env_vars_cleanup}
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
