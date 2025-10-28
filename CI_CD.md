# CI/CD Pipeline Documentation

This project uses GitHub Actions for continuous integration and continuous deployment.

## Overview

The CI/CD pipeline consists of three workflows:

1. **Test Workflow** - Runs on every push and PR
2. **Lint Workflow** - Checks code quality on every push and PR
3. **Release Workflow** - Publishes binaries on version tags

## Workflows

### 1. Test Workflow (.github/workflows/test.yml)

**Triggers**: Push to main/develop, Pull requests

**What it does**:
- Tests on Go 1.23 and 1.24
- Runs tests with race detector
- Generates coverage reports
- Uploads to Codecov
- Checks minimum coverage threshold (50%)

**Steps**:
```
Checkout → Setup Go → Cache deps → Download → Test → Coverage
```

**Outputs**:
- Test results in GitHub Actions
- Coverage uploaded to Codecov
- Coverage badge available

### 2. Lint Workflow (.github/workflows/lint.yml)

**Triggers**: Push to main/develop, Pull requests

**What it does**:
- Runs golangci-lint
- Checks go vet
- Verifies go fmt
- Ensures go mod is tidy

**Steps**:
```
Checkout → Setup Go → Cache deps → golangci-lint → go vet → go fmt → go mod tidy
```

**Linters Enabled**:
- errcheck - Checks error handling
- gosimple - Simplifies code
- govet - Vet analysis
- ineffassign - Detects ineffectual assignments
- staticcheck - Static analysis
- typecheck - Type checking
- unused - Finds unused code
- gofmt - Format checking
- goimports - Import organization
- revive - Fast linter
- misspell - Catches typos
- unparam - Unused parameters
- stylecheck - Style consistency

### 3. Release Workflow (.github/workflows/release.yml)

**Triggers**: Push with version tag (v*.*)

**What it does**:
- Runs tests before release
- Builds binaries for all platforms
- Creates GitHub release
- Includes release notes from RELEASENOTES.md

**Steps**:
```
Checkout → Setup Go → Cache deps → Test → GoReleaser → Create Release
```

**Platforms Built**:
- Linux (amd64, arm64)
- macOS (amd64, arm64)
- Windows (amd64)

## How to Use

### Running Tests Locally

Before pushing, run tests locally:

```bash
make test          # Run all tests
make coverage      # Run tests with coverage
make lint          # Run linters
make fmt           # Format code
make all           # Run all checks
```

### Creating a Release

1. Update version in relevant files
2. Update RELEASENOTES.md
3. Commit and push changes
4. Tag the release:
   ```bash
   git tag v1.0.0
   git push origin v1.0.0
   ```
5. GitHub Actions will automatically:
   - Run tests
   - Build binaries
   - Create GitHub release
   - Upload artifacts

### Viewing Results

- **Test Results**: GitHub Actions → Actions → Test workflow
- **Coverage**: Codecov.io dashboard (if configured)
- **Releases**: GitHub Releases page
- **Build Logs**: GitHub Actions → Workflow run → Job output

## Best Practices

### For Developers

1. **Run local checks before push**:
   ```bash
   make all
   ```

2. **Fix linting issues immediately**:
   ```bash
   make lint
   ```

3. **Ensure tests pass**:
   ```bash
   make test
   ```

4. **Format code before commit**:
   ```bash
   make fmt
   ```

### For Pull Requests

1. All checks must pass before merge
2. Maintain or improve code coverage
3. No new linting errors
4. All tests must pass on multiple Go versions

### For Releases

1. Update version consistently
2. Document changes in RELEASENOTES.md
3. Tag carefully (use semantic versioning)
4. Verify release artifacts

## Configuration Files

### .github/workflows/test.yml
- Multi-version Go testing
- Coverage tracking
- Race detector

### .github/workflows/lint.yml
- golangci-lint configuration
- Code quality checks
- Format and import verification

### .github/workflows/release.yml
- GoReleaser integration
- Platform-specific builds
- GitHub release creation

### .golangci.yml
- Linter configuration
- Rule definitions
- Linter-specific settings

## Troubleshooting

### Tests Failing

1. Check test output in GitHub Actions
2. Run locally: `go test -v ./...`
3. Check for timing issues: `go test -race ./...`

### Linting Failures

1. Run locally: `make lint`
2. Fix issues with: `go fmt ./...` or golangci-lint suggestions
3. Check .golangci.yml for rules

### Release Issues

1. Verify tag format: `v*.*.*`
2. Check RELEASENOTES.md exists
3. Ensure tests pass
4. Verify GoReleaser config (.goreleaser.yml)

## Monitoring

### GitHub Actions Dashboard
- View all workflows
- Check run history
- Review logs

### Codecov Integration (Optional)
- Set up in repository settings
- Configure status checks
- View coverage trends

## Future Enhancements

- Integration tests
- Performance benchmarks
- Container image builds
- Artifact signing
- Automated version bumping
- Slack notifications

## Resources

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [GoReleaser Documentation](https://goreleaser.com/)
- [golangci-lint Documentation](https://golangci-lint.run/)
- [Go Testing](https://golang.org/doc/effective_go#testing)
