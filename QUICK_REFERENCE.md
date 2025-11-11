# Quick Reference: Development & Testing

## Run Commands

### Development Setup

```bash
make install           # Install dependencies
make dev              # Install with dev dependencies (includes linters/testing)
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

main.py               # Entry point
requirements.txt      # Dependencies
Makefile             # Development commands
```

## Key Features

- ✅ Migrates repository secrets from source to target
- ✅ Recreates environments in target repository
- ✅ Generates dynamic GitHub Actions workflow
- ✅ One workflow step per environment secret
- ✅ Automatic cleanup of temporary secrets
- ✅ PAT permission validation
- ✅ Comprehensive logging with verbose mode

## Before Committing

```bash
# Format code
make format

# Check linting
make lint

# Run tests (if configured)
make test

# Clean up artifacts
make clean
```

## CLI Usage

```bash
python main.py \
  --source-org <org> \
  --source-repo <repo> \
  --target-org <org> \
  --target-repo <repo> \
  --source-pat <token> \
  --target-pat <token> \
  [--verbose] \
  [--skip-envs]
```

### Options

- `--verbose` - Enable debug logging
- `--skip-envs` - Skip environment recreation (default: recreate)

### Environment Variable

- `GITHUB_TOKEN` - Fallback for both source and target PATs (if not explicitly provided)

## How It Works

1. **Validate** PAT permissions
2. **Recreate** environments (unless `--skip-envs`)
3. **List** secrets from source
4. **Create** temporary secrets in source (for workflow access)
5. **Generate** dynamic workflow steps
6. **Workflow runs** - migrates each secret to target environment
7. **Cleanup** - deletes temporary secrets and branch

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Import errors | `make install` to ensure dependencies installed |
| Linting errors | `make lint` to check; `make format` to fix |
| Workflow fails | Check GitHub Actions tab in source repo |
| Permission denied | Verify PAT scopes (repo + workflow required) |

## Dependencies

See `requirements.txt`:

- PyGithub - GitHub API client
- Click - CLI framework
- requests - HTTP library

## Success Indicators

- ✅ Code formatted correctly
- ✅ No linting errors
- ✅ All commands execute without errors
- ✅ Workflow file generated successfully
- ✅ Tests pass (when configured)
