# Quick Reference: Development & Testing

## Installation Methods

```bash
# As GitHub CLI extension (recommended)
gh extension install renan-alm/gh-secrets-migrator

# From source
git clone https://github.com/renan-alm/gh-secrets-migrator.git
cd gh-secrets-migrator
make dev

# Build local binary
make build
```

## Run Commands

### Development Setup

```bash
make install           # Install dependencies
make dev              # Install with dev dependencies (includes linters/testing)
make build            # Build binary for current platform
```

### Code Quality

```bash
make format           # Format code with black
make lint             # Run flake8 and pylint checks
```

### Testing

```bash
make test             # Run test suite with pytest
```

### Cleanup

```bash
make clean            # Remove build artifacts, cache, pyc files
```

## Project Structure

```text
src/
├── core/              # Business logic
│   ├── config.py      # Configuration container
│   ├── migrator.py    # Main orchestration logic
│   └── workflow_generator.py  # GitHub Actions workflow generation
├── clients/
│   └── github.py      # GitHub API wrapper
├── cli/
│   └── commands.py    # CLI interface with Click
└── utils/
    └── logger.py      # Logging utility

script/
└── build.sh          # Build script for gh-extension-precompile

gh-secrets-migrator   # Wrapper script for GH CLI extension
gh-secrets-migrator.spec  # PyInstaller specification
manifest.json         # GH CLI extension manifest
main.py               # Entry point
requirements.txt      # Dependencies
Makefile             # Development commands
```

## Key Features

- ✅ Repository-to-Repository secret migration
- ✅ Organization-to-Organization secret migration
- ✅ Repository scoping for organization secrets (maintains visibility settings)
- ✅ Recreates environments in target repository
- ✅ Generates dynamic GitHub Actions workflow
- ✅ One workflow step per secret (repo/env/org)
- ✅ Automatic cleanup of temporary secrets
- ✅ Automatic rate limit monitoring and handling
- ✅ PAT permission validation
- ✅ Comprehensive logging with verbose mode
- ✅ Custom endpoint support (GHEC Data Residency, GHES, EMU)
- ✅ Available as GitHub CLI extension
- ✅ Precompiled binaries for Linux, macOS (Intel & Apple Silicon), Windows

## Before Committing

```bash
# Format code
make format

# Check linting
make lint

# Run tests
make test

# Clean up artifacts
make clean
```

## CLI Usage

All examples work with any of these commands:
- `gh secrets-migrator` (as extension)
- `./gh-secrets-migrator` (local binary)
- `python main.py` (from source)

### Repository-to-Repository Migration

```bash
gh secrets-migrator \
  --source-org <org> \
  --source-repo <repo> \
  --target-org <org> \
  --target-repo <repo> \
  --source-pat <token> \
  --target-pat <token> \
  [--source-endpoint <url>] \
  [--target-endpoint <url>] \
  [--verbose] \
  [--skip-envs]
```

### Organization-to-Organization Migration

```bash
gh secrets-migrator \
  --source-org <org> \
  --target-org <org> \
  --source-repo <repo> \
  --source-pat <token> \
  --target-pat <token> \
  [--source-endpoint <url>] \
  [--target-endpoint <url>] \
  --org-to-org \
  [--verbose]
```

### Options

- `--verbose` - Enable debug logging
- `--skip-envs` - Skip environment recreation (repo-to-repo only)
- `--org-to-org` - Migrate only organization-level secrets (ignores repo/env secrets)
- `--source-endpoint` - GitHub API endpoint for source (default: https://api.github.com)
- `--target-endpoint` - GitHub API endpoint for target (default: https://api.github.com)

### Environment Variable

**Authentication:**
- `GITHUB_TOKEN` - Fallback for both source and target PATs (if not explicitly provided)
- `SOURCE_PAT` - Source Personal Access Token (overrides GITHUB_TOKEN)
- `TARGET_PAT` - Target Personal Access Token (overrides GITHUB_TOKEN)

**Repository Configuration:**
- `SOURCE_ORG` - Source organization name
- `SOURCE_REPO` - Source repository name  
- `TARGET_ORG` - Target organization name
- `TARGET_REPO` - Target repository name

**Endpoints:**
- `SOURCE_ENDPOINT` - GitHub API endpoint for source (default: https://api.github.com)
- `TARGET_ENDPOINT` - GitHub API endpoint for target (default: https://api.github.com)

**Options:**
- `VERBOSE` - Enable debug logging (set to any non-empty value)
- `SKIP_ENVS` - Skip environment recreation (set to any non-empty value)
- `ORG_TO_ORG` - Migrate only organization-level secrets (set to any non-empty value)

## How It Works

1. **Validate** PAT permissions
2. **Check** rate limits and wait if critically low
3. **Recreate** environments (unless `--skip-envs`)
4. **List** secrets from source (repo, environment, and org secrets)
5. **Create** temporary secrets in source (for workflow access)
6. **Generate** dynamic workflow steps
7. **Workflow runs** - migrates each secret to target with proper scoping
8. **Cleanup** - deletes temporary secrets and branch

## Release Process

1. Update CHANGELOG.md with version entry
2. Create and push tag: `git tag v1.0.0 && git push origin v1.0.0`
3. GitHub Actions automatically:
   - Validates changelog and tests
   - Builds binaries for all platforms (Linux, macOS, Windows)
   - Creates GitHub release
   - Makes extension installable via `gh extension install`

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Import errors | `make install` to ensure dependencies installed |
| Linting errors | `make lint` to check; `make format` to fix |
| Workflow fails | Check GitHub Actions tab in source repo |
| Permission denied | Verify PAT scopes (repo + workflow required) |
| Binary not found | Run `make build` to build for your platform |
| Rate limit errors | Tool automatically waits when rate limit is low; check current limits in verbose mode |

## Dependencies

See `requirements.txt`:

**Core:**
- PyGithub==2.8.1 - GitHub API client
- Click==8.3.1 - CLI framework
- python-dotenv==1.2.1 - Environment variable loading

**Development & Build:**
- PyInstaller==6.18.0 - Binary compilation
- pytest==9.0.2 - Testing framework
- pytest-cov==7.0.0 - Code coverage
- mypy==1.19.1 - Type checking
- flake8==7.3.0 - Linting
- bandit==1.9.3 - Security scanning

**Python Version:**
- Requires Python 3.10+ (3.8/3.9 support dropped in v0.3.0)

## Success Indicators

- ✅ Code formatted correctly
- ✅ No linting errors
- ✅ All commands execute without errors
- ✅ Workflow file generated successfully
- ✅ Tests pass
- ✅ Binary builds successfully
