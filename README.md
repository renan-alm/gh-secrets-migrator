# GitHub Secrets Migrator (Python)

A tool to migrate GitHub repository secrets from a source repository to a target repository.

## Features

- ✨ Migrates secrets from one GitHub repository to another
- 🔐 Automatically encrypts secrets using GitHub's public key
- 🤖 Uses GitHub Actions workflow for automated migration
- 🔄 Supports both source and target PAT or GITHUB_TOKEN environment variable
- 📝 Comprehensive logging with verbose mode

## Installation

### Prerequisites

- Python 3.8+
- GitHub Personal Access Tokens (PAT) with repo and workflow scopes

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

## Usage

### Basic Usage

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

```bash
export GITHUB_TOKEN=<your-token>
python main.py \
  --source-org <source-org> \
  --source-repo <source-repo> \
  --target-org <target-org> \
  --target-repo <target-repo>
```

### With Verbose Logging

```bash
python main.py \
  --source-org myorg \
  --source-repo source-repo \
  --target-org targetorg \
  --target-repo target-repo \
  --verbose
```

## How It Works

1. **Go CLI validates** - Checks GITHUB_TOKEN or explicit PATs
2. **Lists secrets** - Gets all secrets from source repo (for logging)
3. **Creates target PAT secret** - Stores target PAT in source repo as `SECRETS_MIGRATOR_TARGET_PAT` (encrypted)
4. **Creates migration branch** - Creates a new branch called `migrate-secrets`
5. **Pushes workflow** - Commits GitHub Actions workflow to migration branch
6. **Workflow runs** - Triggered by push to `migrate-secrets` branch:
   - Reads all secrets from source repo
   - For each secret: creates it in target repo using target PAT
   - Cleans up: deletes `SECRETS_MIGRATOR_TARGET_PAT` from source repo
   - Deletes the migration branch

## Makefile Commands

```bash
make install       # Install dependencies
make dev          # Install with dev dependencies
make lint         # Run linting checks
make format       # Format code with black
make test         # Run tests
make run          # Run the migrator
make clean        # Clean build artifacts
make help         # Show help
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

### Environment Variables

- `GITHUB_TOKEN`: If set, uses this token for both source and target authentication

## Security Notes

- ✅ Secrets are encrypted at rest in GitHub
- ✅ Encrypted using GitHub's public key (libsodium sealed boxes)
- ✅ Only available to workflows via `${{ secrets.* }}` context
- ✅ Temporary `SECRETS_MIGRATOR_TARGET_PAT` is cleaned up after workflow
- ✅ Secrets are masked in logs by GitHub Actions

## Limitations

- Requires repo and workflow scopes on PATs
- Cannot migrate organization-level secrets (only repo-level)
- Workflow runs on source repo (not target)

## Troubleshooting

### "Connection refused" or Authentication errors

- Verify your PATs are valid and have correct scopes
- Check that organization/repository names are correct
- Ensure PATs have `repo` and `workflow` scopes

### Workflow doesn't run

- Check that the migration branch was created: `Settings > Branches`
- Verify GitHub Actions is enabled in the source repository
- Check the Actions tab for any workflow errors

### Secrets not appearing in target repo

- Verify target PAT has permission to create secrets in target repo
- Check that secret names don't start with `SECRETS_MIGRATOR_` (filtered out)
- Review workflow logs in the Actions tab

## Development

```bash
# Set up development environment
make dev

# Run with verbose logging
python main.py --source-org myorg --source-repo repo --target-org targetorg --target-repo target --verbose

# Format code
make format

# Run linting
make lint

# Clean up
make clean
```

## License

[LICENSE](LICENSE)
