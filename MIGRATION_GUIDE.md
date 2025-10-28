# Migration Guide: From Flat to Best Practice Go Structure

This guide explains the refactoring of the gh-secrets-migrator project and how to work with the new structure.

## What Changed?

The project was reorganized from a flat structure to follow Go best practices:

### Old Structure (Flat)
```
main.go, github_api.go, logger.go in root + src/ C# files
```

### New Structure (Go Best Practices)
```
cmd/            → Binary entry points
internal/       → Private packages (not importable)
├── cli/        → Command-line interface
├── github/     → GitHub API client
├── logger/     → Logging utilities
└── migrator/   → Core business logic
```

## For End Users

**No changes!** The CLI interface remains exactly the same:

```bash
gh-secrets-migrator \
  --source-org my-org \
  --source-repo old-repo \
  --target-org my-org \
  --target-repo new-repo \
  --source-pat <PAT> \
  --target-pat <PAT>
```

## For Developers

### Building the Project

**Old way:**
```bash
go build -o gh-secrets-migrator .
```

**New way:**
```bash
go build -o gh-secrets-migrator ./cmd/gh-secrets-migrator
# Or use the Makefile
make build
```

### Project Layout Benefits

#### 1. Clear Entry Point
- `cmd/gh-secrets-migrator/main.go` - Minimal entry point
- Only imports and initializes the CLI
- No business logic

#### 2. Organized Internal Packages
- `internal/cli/` - CLI concerns only
- `internal/github/` - GitHub API operations
- `internal/logger/` - Logging concerns
- `internal/migrator/` - Migration logic

#### 3. Testability
Each package is independently testable:

```bash
# Test specific package
go test ./internal/migrator

# Test with coverage
go test -cover ./...

# Test all
make test
```

#### 4. Reusability
Packages are designed for reuse:

```go
// Could import github package if it's internal/
```go
import "github.com/renan-alm/gh-secrets-migrator/internal/migrator"
```

config := &migrator.Config{...}
m := migrator.New(ctx, config, log)
if err := m.Run(ctx); err != nil {
    // Handle error
}
```

### Development Workflow

#### Quick Build & Test
```bash
make dev  # Formats, vets, and builds
```

#### Full Quality Check
```bash
make all  # Formats, lints, vets, tests, and builds
```

#### Specific Tasks
```bash
make fmt          # Format code
make lint         # Run linter
make vet          # Run go vet
make test         # Run tests
make build        # Build binary
make build-all    # Build for all platforms
make clean        # Clean artifacts
```

### Code Organization

#### Where should I add new code?

| Requirement | Package |
|---|---|
| New GitHub API method | `internal/github/client.go` |
| New command | `internal/cli/` (new file) |
| New log format | `internal/logger/logger.go` |
| New migration logic | `internal/migrator/migrator.go` |
| Binary changes | `cmd/gh-secrets-migrator/main.go` |

#### Example: Adding a new command

1. Create `internal/cli/my_command.go`
2. Define command with cobra
3. Import in `internal/cli/root.go`
4. Add to root command

### Dependency Flow

The clean architecture follows this dependency flow:

```
cmd/main.go (entry)
    ↓
internal/cli (commands)
    ↓
internal/migrator (business logic)
    ↓
internal/{github, logger} (utilities)
```

### Adding Tests

Tests should mirror the package structure:

```
internal/
├── github/
│   ├── client.go
│   └── client_test.go
├── logger/
│   ├── logger.go
│   └── logger_test.go
└── migrator/
    ├── migrator.go
    └── migrator_test.go
```

Example test:

```go
// internal/migrator/migrator_test.go
package migrator_test

import (
    "testing"
    "github.com/renan-alm/gh-secrets-migrator/internal/migrator"
)

func TestMigratorRun(t *testing.T) {
    // Test migration logic
}
```

### Release Process

The project uses GoReleaser for automated releases:

```bash
# Create and push a tag
git tag v1.0.0
git push origin v1.0.0

# GoReleaser automatically builds and publishes
# (Requires GitHub Actions to be configured)
```

See `.goreleaser.yml` for configuration.

### Common Tasks

#### Running locally
```bash
make build
./gh-secrets-migrator --help
```

#### Adding a dependency
```bash
go get github.com/user/package
go mod tidy
```

#### Checking for issues
```bash
go vet ./...
golangci-lint run ./...
go test -v ./...
```

#### Debugging
```bash
# Verbose output
go run ./cmd/gh-secrets-migrator --verbose

# With debugging
dlv debug ./cmd/gh-secrets-migrator
```

## Migration from Old Code

If you're maintaining custom changes:

### Old File → New Location
- `main.go` → `cmd/gh-secrets-migrator/main.go` (simplified)
- `github_api.go` → `internal/github/client.go`
- `logger.go` → `internal/logger/logger.go`
- `Program.cs` (CLI logic) → `internal/cli/root.go`

### Changes to Imports

Old import-free structure now uses internal packages:

```go
// Old way (not possible anymore)
import "github_api"  // ❌

// New way
import "github.com/renan-alm/gh-secrets-migrator/internal/github"
```

## Troubleshooting

### "can't load package"
Make sure you're building the correct path:
```bash
go build ./cmd/gh-secrets-migrator  # ✓ Correct
go build .                           # ✗ Won't work in subdirs
```

### Import errors
Ensure full package path:
```go
import "github.com/renan-alm/gh-secrets-migrator/internal/github"  // ✓ Correct
import "internal/github"                                           // ✗ Wrong
```

### Circular imports
The package structure prevents this by design. If you need code in multiple places, consider:
1. Moving to a shared internal package
2. Using dependency injection
3. Creating a new utility package

## Going Forward

With this structure:

✅ **Easy to test** - Each package is independent  
✅ **Easy to extend** - Clear where to add new features  
✅ **Easy to maintain** - Organized code separation  
✅ **Easy to release** - Automated build process  
✅ **Easy to deploy** - Single binary output  

## Questions?

Refer to:
- `README.md` - General usage
- `REFACTORING.md` - Detailed refactoring changes
- `Makefile` - Available development targets
- Go project layout conventions: https://github.com/golang-standards/project-layout
