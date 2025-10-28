# Testing Guide

This document describes the testing strategy and best practices for the gh-secrets-migrator project.

## Testing Approach

We follow Go best practices for testing:

- **Unit Tests**: Test individual functions and types
- **Table-Driven Tests**: Use test tables for comprehensive coverage
- **Subtests**: Use `t.Run()` for organized test execution
- **Benchmarks**: Performance testing with `*_test.go` files
- **Integration Tests**: Test component interactions (future)

## Test Structure

Tests are organized alongside their corresponding source code:

```
internal/
├── logger/
│   ├── logger.go
│   └── logger_test.go    # Tests for logger package
├── github/
│   ├── client.go
│   └── client_test.go    # Tests for GitHub client
├── migrator/
│   ├── migrator.go
│   └── migrator_test.go  # Tests for migrator
└── cli/
    ├── root.go
    └── root_test.go      # Tests for CLI
```

## Running Tests

### Run all tests
```bash
make test
```

### Run tests with coverage
```bash
make coverage
```

### Run tests for a specific package
```bash
go test -v ./internal/logger/...
```

### Run a specific test
```bash
go test -v -run TestNewLogger ./internal/logger/
```

### Run tests with race detector
```bash
go test -race ./...
```

### Run benchmarks
```bash
go test -bench=. -benchmem ./...
```

## Test Best Practices

### 1. Table-Driven Tests
```go
func TestLoggerInfo(t *testing.T) {
    tests := []struct {
        name    string
        message string
    }{
        {"simple message", "test message"},
        {"empty message", ""},
    }

    for _, tt := range tests {
        t.Run(tt.name, func(t *testing.T) {
            l := logger.New(false)
            l.Info(tt.message)
        })
    }
}
```

### 2. Subtests
```go
func TestLoggerWithVerbose(t *testing.T) {
    t.Run("verbose enabled", func(t *testing.T) {
        l := logger.New(true)
        l.Debug("debug enabled")
    })

    t.Run("verbose disabled", func(t *testing.T) {
        l := logger.New(false)
        l.Debug("debug disabled")
    })
}
```

### 3. Naming Convention
- Test files: `*_test.go`
- Test functions: `TestFunctionName(t *testing.T)`
- Benchmarks: `BenchmarkFunctionName(b *testing.B)`
- Helpers: `testHelper()` (lowercase with 'test' prefix)

### 4. Test Isolation
- Each test is independent
- No shared state between tests
- Clean setup/teardown when needed
- Use `t.Parallel()` for parallel test execution (if safe)

## Code Coverage

### View Coverage Report
```bash
go test -coverprofile=coverage.out ./...
go tool cover -html=coverage.out
```

### Coverage Goals
- **Minimum**: 50% overall coverage
- **Target**: 70%+ coverage for critical paths
- **Ideal**: 85%+ for core business logic

Current coverage threshold is checked in CI/CD pipeline.

## CI/CD Integration

Tests run automatically on:
- Every push to `main` and `develop` branches
- Every pull request
- On multiple Go versions (1.20, 1.21)

Workflow: `.github/workflows/test.yml`

See workflow for:
- Coverage uploads to Codecov
- Race condition detection
- Multi-version testing

## Mocking and Test Doubles

For testing components that interact with external services (GitHub API):

### Future: Interface-based mocking
```go
type GitHubClient interface {
    CreateRepoSecret(ctx context.Context, ...) error
    // ... other methods
}

// Mock implementation for tests
type MockGitHubClient struct {
    CreateRepoSecretFunc func(...) error
}
```

## Common Testing Patterns

### Testing with Errors
```go
func TestWithError(t *testing.T) {
    _, err := someFunction()
    if err == nil {
        t.Error("expected error, got nil")
    }
    if err.Error() != "expected message" {
        t.Errorf("expected 'expected message', got %q", err.Error())
    }
}
```

### Testing Panics
```go
func TestPanic(t *testing.T) {
    defer func() {
        if r := recover(); r == nil {
            t.Error("expected panic")
        }
    }()
    // code that should panic
}
```

### Testing Goroutines
```go
func TestConcurrency(t *testing.T) {
    done := make(chan bool)
    go func() {
        // concurrent work
        done <- true
    }()
    <-done
}
```

## Performance Testing

### Run Benchmarks
```bash
go test -bench=. -benchmem -benchtime=10s ./...
```

### Benchmark Example
```go
func BenchmarkConfigCreation(b *testing.B) {
    for i := 0; i < b.N; i++ {
        _ = &Config{...}
    }
}
```

## Continuous Integration

### Local Pre-commit Checks
```bash
# Run linting
make lint

# Run tests
make test

# Check formatting
make fmt

# Run all checks
make all
```

### GitHub Actions
All checks run automatically in CI:
- **Test Workflow**: Run tests on multiple Go versions
- **Lint Workflow**: Code quality checks
- **Release Workflow**: Triggered on version tags

## Adding New Tests

When adding a new feature:

1. Create a `*_test.go` file in the same package
2. Write table-driven tests for all cases
3. Include both success and failure scenarios
4. Aim for >70% coverage of the new code
5. Run `make test` locally before committing
6. CI/CD will verify coverage on PR

## Troubleshooting Tests

### Test Hanging
- Check for unbuffered channel deadlocks
- Use `timeout` flag: `go test -timeout 10s ./...`

### Flaky Tests
- Avoid time-dependent tests
- Don't rely on ordering of maps/sets
- Use `t.Parallel()` carefully

### Import Cycles
- Use `*_test` package name for isolated tests
- Structure packages to avoid circular dependencies

## Resources

- [Go Testing Best Practices](https://golang.org/doc/effective_go#testing)
- [Table-Driven Tests](https://github.com/golang/go/wiki/TableDrivenTests)
- [Testing Package Documentation](https://pkg.go.dev/testing)
