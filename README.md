# GitHub Secrets Migrator (Python)

A tool to migrate GitHub repository secrets from a source repository to a target repository using GitHub Actions workflows.

## Features

- ✨ Migrates secrets from one GitHub repository to another
- 🌍 Recreates repository environments in target repository
- 🔐 Automatically encrypts secrets using GitHub's public key
- 🤖 Uses GitHub Actions workflow for automated migration
- 🔄 Supports both explicit PATs or GITHUB_TOKEN environment variable
- 📝 Comprehensive logging with verbose mode
- ✅ Validates PAT permissions before starting migration
- 🧹 Automatic cleanup of temporary secrets

## Installation

### Prerequisites

- Python 3.8+
- GitHub Personal Access Tokens (PAT) with appropriate scopes (see [Permissions](#permissions) section)

### Setup

```bash
# Clone the repository
git clone <repo-url>
cd gh-secrets-migrator

# Install dependencies
pip install -r requirements.txt

# Or with dev dependencies
make dev
```

## Permissions

### Required PAT Scopes

Both **source** and **target** PATs must have the following scopes:

#### Source PAT Scopes

For reading source repo and managing temporary secrets:

- `repo` - Full control of private repositories
- `workflow` - Update GitHub Action workflows (for branch/workflow management)

#### Target PAT Scopes

For creating secrets in target repository:

- `repo` - Full control of private repositories

### Minimal Permissions Checklist

**Source PAT:**

- ✅ Read repository secrets
- ✅ Create/update repository secrets (temporary PAT storage)
- ✅ Delete repository secrets (cleanup)
- ✅ Create/delete branches
- ✅ Push to repository

**Target PAT:**

- ✅ Create/update repository secrets

### Creating a Personal Access Token (Classic)

1. Go to GitHub Settings → Developer settings → Personal access tokens (classic)
2. Click "Generate new token (classic)"
3. Give it a descriptive name (e.g., "Secrets Migrator Source")
4. Select the required scopes (see above)
5. Click "Generate token"
6. Copy the token immediately (you won't see it again)

⚠️ **Security Note**: Store these tokens securely. Never commit them to repositories.

## Usage

### Basic Usage with Explicit PATs

```bash
python main.py \
  --source-org <source-org> \
  --source-repo <source-repo> \
  --target-org <target-org> \
  --target-repo <target-repo> \
  --source-pat <source-pat> \
  --target-pat <target-pat>
```

### Using GITHUB_TOKEN Environment Variable

If you have a single token with permissions for both source and target:

```bash
export GITHUB_TOKEN=<your-token>
python main.py \
  --source-org <source-org> \
  --source-repo <source-repo> \
  --target-org <target-org> \
  --target-repo <target-repo>
```

### Organization-to-Organization Migration (Org Secrets Only)

To migrate only organization-level secrets (ignoring repository and environment secrets):

```bash
python main.py \
  --source-org <source-org> \
  --target-org <target-org> \
  --source-pat <source-pat> \
  --target-pat <target-pat> \
  --org-to-org
```

**Note:** This requires `--source-repo` and `--target-repo` to be provided as well for the workflow execution context, but only organization-level secrets will be migrated. Repository and environment-specific secrets will be ignored.

```bash
python main.py \
  --source-org myorg \
  --target-org targetorg \
  --source-repo .github \
  --target-repo .github \
  --org-to-org \
  --verbose
```

### With Verbose Logging

```bash
python main.py \
  --source-org myorg \
  --source-repo source-repo \
  --target-org targetorg \
  --target-repo target-repo \
  --source-pat <source-pat> \
  --target-pat <target-pat> \
  --verbose
```

### Skipping Environment Recreation

By default, environments from the source repository are recreated in the target repository. To skip this:

```bash
python main.py \
  --source-org <source-org> \
  --source-repo <source-repo> \
  --target-org <target-org> \
  --target-repo <target-repo> \
  --source-pat <source-pat> \
  --target-pat <target-pat> \
  --skip-envs
```

### Example

```bash
./main.py \
  --source-org renan-org \
  --source-repo .github \
  --target-org demo-org-renan \
  --target-repo migration-sample \
  --verbose
```

## How It Works

1. **Validates PAT permissions** - Checks both PATs have necessary scopes before proceeding
2. **Recreates environments** (unless `--skip-envs` is set) - Creates environments from source repo in target repo:
   - Lists all environments from source repository
   - Creates each environment in target repository
   - Gracefully skips if environment already exists (idempotent)
3. **Lists secrets** - Gets all secrets from source repo (for logging)
4. **Creates temporary secrets** - Stores both PATs in source repo:
   - `SECRETS_MIGRATOR_TARGET_PAT` (encrypted) - Used by workflow to access target repo
   - `SECRETS_MIGRATOR_SOURCE_PAT` (encrypted) - Used by workflow cleanup to delete temporary secrets
5. **Creates migration branch** - Creates a new branch called `migrate-secrets`
6. **Pushes workflow** - Commits GitHub Actions workflow to migration branch
7. **Workflow runs** - Triggered by push to `migrate-secrets` branch:
   - Reads all secrets from source repo
   - Filters out system secrets (`SECRETS_MIGRATOR_*`, `github_token`)
   - For each remaining secret: creates it in target repo using target PAT
   - Cleanup (always runs):
     - Deletes `SECRETS_MIGRATOR_TARGET_PAT` from source repo
     - Deletes `SECRETS_MIGRATOR_SOURCE_PAT` from source repo
     - Deletes the migration branch

## Makefile Commands

```bash
make install       # Install dependencies
make dev          # Install with dev dependencies (includes linters/testing)
make lint         # Run linting checks (flake8 + pylint)
make format       # Format code with black
make test         # Run tests with pytest
make clean        # Clean build artifacts, cache, .pyc files
make help         # Show all available commands
```

## Configuration

### Required Flags

- `--source-org`: Source organization name
- `--source-repo`: Source repository name
- `--target-org`: Target organization name
- `--target-repo`: Target repository name

### Optional Flags

- `--source-pat`: Source PAT (required if GITHUB_TOKEN not set)
- `--target-pat`: Target PAT (required if GITHUB_TOKEN not set)
- `--verbose`: Enable verbose logging (shows debug messages)
- `--skip-envs`: Skip environment recreation (by default environments are recreated)

### Environment Variables

- `GITHUB_TOKEN`: If set, uses this token for both source and target authentication (must have permissions for both repos)

## Security

### ✅ What's Secure

- Secrets are **encrypted at rest** in GitHub using libsodium sealed boxes
- Only available to workflows via `${{ secrets.* }}` context
- Secrets are **masked in GitHub Actions logs** (redacted automatically)
- Temporary `SECRETS_MIGRATOR_TARGET_PAT` and `SECRETS_MIGRATOR_SOURCE_PAT` are **always cleaned up** after workflow completes
- Cleanup runs even if migration fails (`if: always()` condition)
- Workflow cleanup deletes the migration branch automatically

### ⚠️ Security Notes

- PATs should be treated like passwords - keep them secret
- Use separate PATs for source and target for better access control
- Consider using organization-level secrets to rotate credentials
- Review the generated workflow before running (it's visible in the Actions tab)
- Tokens are visible to anyone with write access to the source repository (they can read the workflow file)

## Environment Recreation

The tool automatically recreates all environments from the source repository in the target repository. This is useful for maintaining environment parity between repositories.

### Behavior

- **Default**: Environments are automatically recreated
- **Graceful**: If an environment already exists in the target (HTTP 409), it is silently skipped
- **Idempotent**: Safe to run multiple times; existing environments won't cause failures
- **Optional**: Use `--skip-envs` flag to skip environment recreation

### Example Output

```bash
ℹ️  Recreating environments...
ℹ️  Environments to recreate (3 total):
  - production
  - staging
  - development
✅ Environment recreation completed!
```

### Environment-Specific Secrets

Environment-specific secrets are now migrated! The tool generates one workflow step per environment-secret combination:

- Lists all environment secrets from the source repository
- Creates dynamic workflow steps for each secret
- Each step migrates that specific secret to the target environment
- Secrets are created using the values already available in the workflow context

## Limitations

- Requires repo-level secrets (cannot migrate organization-level secrets)
- Both source and target PATs must have appropriate scopes
- Workflow runs on source repository (not target)
- Cannot migrate action secrets from Dependabot or Codespaces scopes
- Source and target repositories must be accessible to their respective PATs
- Environment-specific secrets are not yet migrated (repository-level only)

## Troubleshooting

### "Invalid PAT credentials or insufficient permissions"

- Verify your PATs are valid: `curl -H "Authorization: token <PAT>" https://api.github.com/user`
- Check scopes: Go to GitHub Settings → Developer settings → Personal access tokens (classic) → Select token → View scopes
- Ensure PATs have `repo` and `workflow` scopes

### "Connection refused" or Authentication errors

- Verify organization/repository names are correct
- Check that PATs haven't expired
- Ensure you have access to both organizations

### Workflow doesn't run

- Check that the migration branch was created: `Settings > Branches`
- Verify GitHub Actions is enabled in the source repository
- Check the Actions tab for any workflow errors
- Ensure the workflow file `.github/workflows/migrate-secrets.yml` was created

### Secrets not appearing in target repo

- Verify target PAT has permission to create secrets in target repo
- Check that secret names don't start with `SECRETS_MIGRATOR_` (filtered out)
- Review workflow logs in the Actions tab
- Verify target repository is accessible to target PAT

### "Resource not accessible by integration" error

- This typically means the PAT doesn't have the `repo` or `workflow` scope
- Update your source PAT to include these scopes
- Regenerate the PAT if needed

### Temporary secrets not being deleted

- Check workflow cleanup logs in Actions tab
- Manually delete `SECRETS_MIGRATOR_TARGET_PAT` and `SECRETS_MIGRATOR_SOURCE_PAT` from source repo
- Verify source PAT has delete permissions

## Development

```bash
# Set up development environment
make dev

# Run with verbose logging
python main.py \
  --source-org myorg \
  --source-repo repo \
  --target-org targetorg \
  --target-repo target \
  --verbose

# Format code
make format

# Run linting
make lint

# Clean up
make clean
```

## API Reference

### CLI Command

```bash
python main.py [OPTIONS]

Options:
  --source-org TEXT       Source organization name [required]
  --source-repo TEXT      Source repository name [required]
  --target-org TEXT       Target organization name [required]
  --target-repo TEXT      Target repository name [required]
  --source-pat TEXT       Source Personal Access Token (defaults to GITHUB_TOKEN)
  --target-pat TEXT       Target Personal Access Token (defaults to GITHUB_TOKEN)
  --verbose              Enable verbose logging
  --help                 Show help message
```

## License

[LICENSE](LICENSE)
