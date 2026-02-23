# GitHub Secrets Migrator

[![Tests](https://github.com/renan-alm/gh-secrets-migrator/actions/workflows/test-and-lint.yml/badge.svg)](https://github.com/renan-alm/gh-secrets-migrator/actions/workflows/test-and-lint.yml)
[![Release](https://github.com/renan-alm/gh-secrets-migrator/actions/workflows/release.yml/badge.svg)](https://github.com/renan-alm/gh-secrets-migrator/actions/workflows/release.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

A GitHub CLI extension to migrate GitHub repository secrets from a source repository to a target repository using GitHub Actions workflows. Written in Python and compiled to native binaries using PyInstaller.

## Features

- ✨ Migrates secrets from one GitHub repository to another
- � Supports organization-to-organization secret migration
- 🔍 Repository scoping for organization secrets (maintains visibility settings)
- 🌍 Recreates repository environments in target repository
- 🔐 Automatically encrypts secrets using GitHub's public key
- 🤖 Uses GitHub Actions workflow for automated migration
- 🔄 Supports both explicit PATs or GITHUB_TOKEN environment variable
- 🌐 Supports custom endpoints for GHEC Data Residency, GHES, and EMU
- ⏱️ Automatic rate limit monitoring and handling
- 📝 Comprehensive logging with verbose mode
- ✅ Validates PAT permissions before starting migration
- 🧹 Automatic cleanup of temporary secrets
- 🚀 Available as a GitHub CLI extension with precompiled binaries
- 🍎 Native support for macOS (Intel and Apple Silicon), Linux, and Windows

## Installation

### Option 1: GitHub CLI Extension (Recommended)

Install as a GitHub CLI extension for the easiest setup:

```bash
# Install from GitHub
gh extension install renan-alm/gh-secrets-migrator

# Use the extension
gh secrets-migrator --source-org myorg --source-repo myrepo --target-org targetorg --target-repo targetrepo
```

The extension comes with precompiled binaries for Linux, macOS, and Windows, so no Python installation is required.

### Option 2: Direct Binary Download

Download the latest precompiled binary for your platform from the [Releases page](https://github.com/renan-alm/gh-secrets-migrator/releases):

```bash
# Linux AMD64
curl -L https://github.com/renan-alm/gh-secrets-migrator/releases/latest/download/gh-secrets-migrator_v<version>_linux-amd64 -o gh-secrets-migrator
chmod +x gh-secrets-migrator
./gh-secrets-migrator --help

# macOS AMD64 (Intel)
curl -L https://github.com/renan-alm/gh-secrets-migrator/releases/latest/download/gh-secrets-migrator_v<version>_darwin-amd64 -o gh-secrets-migrator
chmod +x gh-secrets-migrator
./gh-secrets-migrator --help

# macOS ARM64 (Apple Silicon)
curl -L https://github.com/renan-alm/gh-secrets-migrator/releases/latest/download/gh-secrets-migrator_v<version>_darwin-arm64 -o gh-secrets-migrator
chmod +x gh-secrets-migrator
./gh-secrets-migrator --help

# Windows (PowerShell)
Invoke-WebRequest -Uri "https://github.com/renan-alm/gh-secrets-migrator/releases/latest/download/gh-secrets-migrator_v<version>_windows-amd64.exe" -OutFile "gh-secrets-migrator.exe"
.\gh-secrets-migrator.exe --help
```

**Note:** Replace `<version>` with the actual version number (e.g., `1.0.0`). The filenames include the `v` prefix.

### Option 3: From Source (Python)

If you prefer to run from source or need to make modifications:

#### Prerequisites

- Python 3.10 or higher (Python 3.8 and 3.9 are no longer supported as of v0.3.0)
- GitHub Personal Access Tokens (PAT) with appropriate scopes (see [Permissions](#permissions) section)

#### Setup

```bash
# Clone the repository
git clone https://github.com/renan-alm/gh-secrets-migrator.git
cd gh-secrets-migrator

# Install dependencies
pip install -r requirements.txt

# Run from source
python main.py --help

# Or build a local binary
make build
./bin/gh-secrets-migrator --help
```

### Docker Setup (Lightweight)

Run the application in a Docker container without installing dependencies locally:

**Build the image:**

```bash
docker build -t gh-secrets-migrator .
```

**Run with Docker:**

```bash
docker run --rm \
  -e GITHUB_TOKEN=<your-token> \
  gh-secrets-migrator \
  --source-org myorg \
  --source-repo .github \
  --target-org targetorg \
  --org-to-org \
  --verbose
```

**Or with explicit PATs:**

```bash
docker run --rm \
  gh-secrets-migrator \
  --source-org myorg \
  --source-repo .github \
  --target-org targetorg \
  --source-pat <source-pat> \
  --target-pat <target-pat> \
  --org-to-org
```

**Using Docker Compose:**

```bash
# Set your token in environment
export GITHUB_TOKEN=<your-token>

# Run the migration
docker-compose run --rm secrets-migrator \
  --source-org myorg \
  --source-repo .github \
  --target-org targetorg \
  --org-to-org
```

**Image Size:** ~200MB (lightweight Python 3.11 slim base)

### Push to GitHub Container Registry (GHCR)

**Authenticate with GHCR:**

```bash
echo $GITHUB_TOKEN | docker login ghcr.io -u <username> --password-stdin
```

**Tag and push the image:**

```bash
# Build with GHCR tag
docker build -t ghcr.io/renan-alm/gh-secrets-migrator:latest .

# Push to GHCR
docker push ghcr.io/renan-alm/gh-secrets-migrator:latest
```

**Run from GHCR:**

```bash
docker run --rm \
  -e GITHUB_TOKEN=<your-token> \
  ghcr.io/renan-alm/gh-secrets-migrator:latest \
  --source-org myorg \
  --source-repo .github \
  --target-org targetorg \
  --org-to-org
```

**Update docker-compose.yml to use GHCR:**

```yaml
services:
  secrets-migrator:
    image: ghcr.io/renan-alm/gh-secrets-migrator:latest
    # ... rest of config
```

### Automated Publishing (CI/CD)

The repository includes GitHub Actions workflows that automatically publish Docker images to GHCR:

- **On successful release**: When the Release workflow completes successfully (triggered by pushing a `v*` tag), the Docker image is automatically built and pushed
- **Pull requests to master**: Docker images are built (but not pushed) to validate the Dockerfile

**Release workflow:**

1. Push a version tag: `git tag v1.2.3 && git push origin v1.2.3`
2. Release workflow validates changelog entry exists and tests passed
3. Builds binaries for Windows, macOS, and Linux
4. Creates GitHub Release with artifacts and SHA256 checksums
5. On success, triggers Docker publish to `ghcr.io/renan-alm/gh-secrets-migrator:v1.2.3`

**No manual steps needed**—just push a tag and the release + Docker image are published!

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

You can use this tool in three ways:
1. **As a GitHub CLI extension** (recommended): `gh secrets-migrator [OPTIONS]`
2. **As a standalone binary**: `./gh-secrets-migrator [OPTIONS]`
3. **From Python source**: `python main.py [OPTIONS]`

All examples below work with any of these methods - just replace the command accordingly.

### Basic Usage with Explicit PATs

```bash
# As GitHub CLI extension
gh secrets-migrator \
  --source-org <source-org> \
  --source-repo <source-repo> \
  --target-org <target-org> \
  --target-repo <target-repo> \
  --source-pat <source-pat> \
  --target-pat <target-pat>

# As standalone binary
./gh-secrets-migrator \
  --source-org <source-org> \
  --source-repo <source-repo> \
  --target-org <target-org> \
  --target-repo <target-repo> \
  --source-pat <source-pat> \
  --target-pat <target-pat>

# From source
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

# Any of these will work
gh secrets-migrator \
  --source-org <source-org> \
  --source-repo <source-repo> \
  --target-org <target-org> \
  --target-repo <target-repo>
```

### Organization-to-Organization Migration (Org Secrets Only)

To migrate only organization-level secrets (ignoring repository and environment secrets):

```bash
gh secrets-migrator \
  --source-org <source-org> \
  --source-repo <source-repo> \
  --target-org <target-org> \
  --source-pat <source-pat> \
  --target-pat <target-pat> \
  --org-to-org
```

**Note:**

- Source repository is **required** to host the migration workflow
- Target repository is optional; if not provided, defaults to the same name as source repo
- Only organization-level secrets are migrated; repository and environment secrets are ignored

**Example:**

```bash
gh secrets-migrator \
  --source-org myorg \
  --source-repo .github \
  --target-org targetorg \
  --org-to-org \
  --verbose
```

**With explicit target repository:**

```bash
gh secrets-migrator \
  --source-org myorg \
  --source-repo .github \
  --target-org targetorg \
  --target-repo .github \
  --org-to-org \
  --verbose
```

### With Verbose Logging

```bash
gh secrets-migrator \
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
gh secrets-migrator \
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
gh secrets-migrator \
  --source-org renan-org \
  --source-repo .github \
  --target-org demo-org-renan \
  --target-repo migration-sample \
  --verbose
```

## How It Works

1. **Validates PAT permissions** - Checks both PATs have necessary scopes before proceeding
2. **Monitors rate limits** - Continuously checks GitHub API rate limits and automatically waits if critically low (< 100 calls remaining)
3. **Recreates environments** (unless `--skip-envs` is set) - Creates environments from source repo in target repo:
   - Lists all environments from source repository
   - Creates each environment in target repository
   - Gracefully skips if environment already exists (idempotent)
4. **Lists secrets** - Gets all secrets from source repo (repo, environment, and org secrets for logging)
5. **Creates temporary secrets** - Stores both PATs in source repo:
   - `SECRETS_MIGRATOR_TARGET_PAT` (encrypted) - Used by workflow to access target repo
   - `SECRETS_MIGRATOR_SOURCE_PAT` (encrypted) - Used by workflow cleanup to delete temporary secrets
6. **Creates migration branch** - Creates a new branch called `migrate-secrets`
7. **Pushes workflow** - Commits GitHub Actions workflow to migration branch
8. **Workflow runs** - Triggered by push to `migrate-secrets` branch:
   - Reads all secrets from source repo
   - Filters out system secrets (`SECRETS_MIGRATOR_*`, `github_token`)
   - For each remaining secret: creates it in target repo/environment/org using target PAT
   - Maintains organization secret visibility and repository scoping
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
- `--source-repo`: Source repository name (**always required** - migration workflow runs in this repository)
- `--target-org`: Target organization name

### Conditionally Required Flags

- `--target-repo`: Target repository name (required for repo-to-repo migration; optional for org-to-org, defaults to source-repo name if not provided)

### Optional Flags

- `--source-pat`: Source PAT (required if GITHUB_TOKEN not set)
- `--target-pat`: Target PAT (required if GITHUB_TOKEN not set)
- `--verbose`: Enable verbose logging (shows debug messages)
- `--skip-envs`: Skip environment recreation (by default environments are recreated)
- `--org-to-org`: Migrate only organization-level secrets (requires `--org-to-org` flag, ignores repo and env secrets)
- `--source-endpoint`: GitHub API endpoint for source (default: `https://api.github.com`)
- `--target-endpoint`: GitHub API endpoint for target (default: `https://api.github.com`)

### Environment Variables

All CLI flags can also be set via environment variables:

**Authentication:**
- `GITHUB_TOKEN`: If set, uses this token for both source and target authentication (must have permissions for both repos)
- `SOURCE_PAT`: Personal Access Token for source repository (overrides GITHUB_TOKEN if set)
- `TARGET_PAT`: Personal Access Token for target repository (overrides GITHUB_TOKEN if set)

**Repository Configuration:**
- `SOURCE_ORG`: Source organization name
- `SOURCE_REPO`: Source repository name
- `TARGET_ORG`: Target organization name
- `TARGET_REPO`: Target repository name

**Endpoints:**
- `SOURCE_ENDPOINT`: GitHub API endpoint for source organization/repository (default: https://api.github.com)
- `TARGET_ENDPOINT`: GitHub API endpoint for target organization/repository (default: https://api.github.com)

**Options:**
- `VERBOSE`: Enable verbose logging (set to any non-empty value)
- `SKIP_ENVS`: Skip environment recreation (set to any non-empty value)
- `ORG_TO_ORG`: Migrate only organization-level secrets (set to any non-empty value)

### Custom Endpoints (GHEC Data Residency, GHES, EMU)

The tool supports custom GitHub API endpoints for:
- **GHEC Data Residency**: GitHub Enterprise Cloud with data residency requirements
- **GHEC EMU**: GitHub Enterprise Cloud with Enterprise Managed Users
- **GHES**: GitHub Enterprise Server (self-hosted)

#### Endpoint URL Formats

- **Standard GitHub.com**: `https://api.github.com` (default)
- **GHEC Data Residency**: `https://api.<INSTANCE>.ghe.com` (where `<INSTANCE>` is your organization's instance name)
- **GitHub Enterprise Server**: `https://github.example.com/api/v3`

**Data Residency Example**: If your instance is `nicklegan`, use `https://api.nicklegan.ghe.com`

#### Examples

**Migrate from GitHub.com to GHEC Data Residency:**
```bash
gh secrets-migrator \
  --source-org myorg \
  --source-repo myrepo \
  --target-org targetorg \
  --target-repo targetrepo \
  --target-endpoint https://api.yourinstance.ghe.com
```

**Migrate from GHEC Data Residency to GitHub.com:**
```bash
gh secrets-migrator \
  --source-org myorg \
  --source-repo myrepo \
  --target-org targetorg \
  --target-repo targetrepo \
  --source-endpoint https://api.yourinstance.ghe.com
```

**Migrate between different GHEC Data Residency instances:**
```bash
gh secrets-migrator \
  --source-org myorg \
  --source-repo myrepo \
  --target-org targetorg \
  --target-repo targetrepo \
  --source-endpoint https://api.sourceinstance.ghe.com \
  --target-endpoint https://api.targetinstance.ghe.com
```

**Migrate from GitHub Enterprise Server:**
```bash
gh secrets-migrator \
  --source-org myorg \
  --source-repo myrepo \
  --target-org targetorg \
  --target-repo targetrepo \
  --source-endpoint https://github.example.com/api/v3
```

**Using environment variables:**
```bash
export SOURCE_ENDPOINT=https://api.sourceinstance.ghe.com
export TARGET_ENDPOINT=https://api.targetinstance.ghe.com

gh secrets-migrator \
  --source-org myorg \
  --source-repo myrepo \
  --target-org targetorg \
  --target-repo targetrepo
```

**Organization-to-Organization migration with custom endpoints:**
```bash
gh secrets-migrator \
  --source-org myorg \
  --source-repo .github \
  --target-org targetorg \
  --source-endpoint https://api.sourceinstance.ghe.com \
  --target-endpoint https://api.targetinstance.ghe.com \
  --org-to-org
```

**Note**: GHEC EMU (Enterprise Managed Users) can use either standard GitHub.com endpoints (`https://api.github.com`) or Data Residency endpoints (`https://api.<INSTANCE>.ghe.com`), depending on your organization's configuration.

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

- Both source and target PATs must have appropriate scopes
- Workflow runs on source repository (not target)
- Cannot migrate action secrets from Dependabot or Codespaces scopes
- Source and target repositories must be accessible to their respective PATs
- For org-to-org migration: only organization-level secrets are migrated (repo and environment secrets are excluded)

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

### Setting Up Development Environment

```bash
# Clone the repository
git clone https://github.com/renan-alm/gh-secrets-migrator.git
cd gh-secrets-migrator

# Set up development environment
make dev

# Run tests
make test

# Run linting
make lint

# Format code
make format
```

### Building Binaries

```bash
# Build for current platform
make build

# The binary will be in bin/gh-secrets-migrator
./gh-secrets-migrator --help

# Clean build artifacts
make clean
```

### Testing Changes

```bash
# Run with verbose logging from source
python main.py \
  --source-org myorg \
  --source-repo repo \
  --target-org targetorg \
  --target-repo target \
  --verbose

# Or test the built binary
make build
./gh-secrets-migrator --verbose --help
```

### Release Process

The project uses GitHub Actions to automatically build and release binaries for multiple platforms:

1. Update `CHANGELOG.md` with the new version entry
2. Ensure all tests pass: `make test`
3. Create and push a version tag:
   ```bash
   git tag v1.0.0
   git push origin v1.0.0
   ```
4. GitHub Actions will automatically:
   - Validate the changelog entry exists
   - Verify tests passed on master
   - Build binaries for Linux, macOS, and Windows
   - Create a GitHub release with binaries
   - Make the extension installable via `gh extension install`

### Available Make Targets

```bash
make help         # Show all available commands
make install      # Install dependencies
make dev          # Install with dev dependencies
make lint         # Run linting checks
make format       # Format code with black
make test         # Run tests with pytest
make build        # Build for current platform
make clean        # Clean build artifacts
```

## API Reference

### CLI Command

```bash
gh secrets-migrator [OPTIONS]
# or: ./gh-secrets-migrator [OPTIONS]
# or: python main.py [OPTIONS]

Options:
  --source-org TEXT         Source organization name [required]
  --source-repo TEXT        Source repository name [required]
  --target-org TEXT         Target organization name [required]
  --target-repo TEXT        Target repository name [conditionally required]
  --source-pat TEXT         Source Personal Access Token (defaults to GITHUB_TOKEN)
  --target-pat TEXT         Target Personal Access Token (defaults to GITHUB_TOKEN)
  --source-endpoint TEXT    GitHub API endpoint for source (default: https://api.github.com)
  --target-endpoint TEXT    GitHub API endpoint for target (default: https://api.github.com)
  --verbose                 Enable verbose logging
  --skip-envs               Skip environment recreation
  --org-to-org              Migrate only organization-level secrets
  --help                    Show help message
```

## Dependencies

The project uses the following dependencies (see `requirements.txt`):

**Core Dependencies:**
- `PyGithub==2.8.1` - GitHub API client library
- `Click==8.3.1` - CLI framework for building command-line interfaces
- `python-dotenv==1.2.1` - Environment variable management from .env files

**Development & Build Tools:**
- `PyInstaller==6.18.0` - Binary compilation for multi-platform distribution
- `pytest==9.0.2` - Testing framework
- `pytest-cov==7.0.0` - Code coverage reporting
- `mypy==1.19.1` - Static type checking
- `flake8==7.3.0` - Python linting
- `bandit==1.9.3` - Security vulnerability scanner

**Python Version:**
- Requires Python 3.10 or higher (Python 3.8 and 3.9 support was dropped in v0.3.0)

## License

[LICENSE](LICENSE)
