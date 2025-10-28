# Quick Reference: Testing & CI/CD

## Run Commands

### Local Testing
```bash
make test              # Full test suite with coverage
make test-verbose      # Show detailed output
make test-race         # Check for race conditions
make test-bench        # Run benchmarks
make coverage          # Generate HTML coverage report
make coverage-report   # Print coverage %
```

### Code Quality
```bash
make fmt               # Format code
make vet               # Run go vet
make lint              # Run linters
make mod-tidy          # Tidy dependencies
make all               # Format + vet + lint + test + build
```

### Build & Release
```bash
make build             # Build binary
make build-all         # Build for all platforms
make clean             # Remove build artifacts
make install           # Build and install
```

## GitHub Actions Workflows

| Workflow | Trigger | Purpose |
|----------|---------|---------|
| test.yml | Push to main/develop, PRs | Run tests on Go 1.20 & 1.21 |
| lint.yml | Push to main/develop, PRs | Check code quality |
| release.yml | Push tags (v*) | Build & release binaries |

## Test Files

| File | Tests | Coverage |
|------|-------|----------|
| internal/logger/logger_test.go | 10 | Logger functionality |
| internal/migrator/migrator_test.go | 7 + 1 benchmark | Config & performance |

## Key Files

```
.github/workflows/test.yml          Multi-version testing
.github/workflows/lint.yml          Code quality checks
.github/workflows/release.yml       Automated releases
.golangci.yml                       14 enabled linters
Makefile                            Development commands
TESTING.md                          Testing guide
CI_CD.md                            Pipeline docs
```

## Test Best Practices Used

✅ Table-driven tests
✅ Subtests with t.Run()
✅ Race detector enabled
✅ Coverage tracking
✅ Benchmarks included
✅ Clear test naming
✅ Test isolation
✅ Multiple Go versions

## Before Committing

```bash
# Local pre-commit check
make all

# Or step by step
make fmt               # Fix formatting
make vet               # Check with vet
make lint              # Fix linting issues
make test              # Verify tests pass
```

## Creating a Release

```bash
# 1. Update version info
# 2. Update RELEASENOTES.md
# 3. Commit changes
git add .
git commit -m "Release v1.0.0"

# 4. Create tag
git tag v1.0.0

# 5. Push
git push origin v1.0.0

# ✅ GitHub Actions automatically:
#    - Runs all tests
#    - Builds for all platforms
#    - Creates GitHub release
#    - Publishes binaries
```

## Coverage Goals

- Minimum: 50% (enforced)
- Target: 70%
- Ideal: 85%

Check: `make coverage-report`

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Tests fail | `make test-verbose` |
| Linting errors | `make lint` |
| Format issues | `make fmt` |
| Build fails | `make clean && make build` |

## Workflows Summary

### 1. Test Workflow
- ✅ Go 1.20 & 1.21
- ✅ Race detector
- ✅ Coverage → Codecov
- ✅ Caching

### 2. Lint Workflow
- ✅ golangci-lint (14 linters)
- ✅ go vet
- ✅ go fmt
- ✅ go mod tidy

### 3. Release Workflow
- ✅ Tests first
- ✅ 5 platform builds
- ✅ GitHub release
- ✅ Checksums

## Success Indicators

✅ All tests pass
✅ Coverage > 50%
✅ No linting errors
✅ Code formatted
✅ Builds successful

You're ready! Push with confidence! 🚀
