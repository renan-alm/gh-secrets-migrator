# GitHub Secrets Migrator

A high-performance command-line tool written in Go to migrate GitHub repository secrets from one repository to another.

## Features

- Migrates all secrets from a source GitHub repository to a target repository
- Securely encrypts secrets using the target repository's public key
- Automatically generates and commits a GitHub Actions workflow
- Workflow handles all encryption and migration via PowerShell
- Supports verbose logging for troubleshooting
- Cross-platform compilation support

## Project Structure

```text
.
├── cmd/
│   └── gh-secrets-migrator/
│       └── main.go              # Application entry point
├── internal/
│   ├── cli/
│   │   └── root.go              # Cobra CLI command setup
│   ├── github/
│   │   └── client.go            # GitHub API client
│   ├── logger/
│   │   └── logger.go            # Logging utilities
│   └── migrator/
│       └── migrator.go          # Core migration logic
├── go.mod                        # Go module definition
├── go.sum                        # Go module checksums
├── Makefile                      # Build and development tasks
├── .goreleaser.yml              # Release automation configuration
└── README.md                     # This file
```

## Prerequisites

- Go 1.21 or later (for building from source)
- GitHub Personal Access Tokens (PATs) for both source and target repositories with appropriate permissions
- Permissions to create branches, workflows, and secrets in the source repository

## Installation

### ⭐ Recommended: GitHub CLI Extension

The easiest way to use `gh-secrets-migrator` is as a `gh` CLI extension. This integrates seamlessly with your GitHub CLI workflow.

**Prerequisites:**
- `gh` CLI installed ([Install gh CLI](https://cli.github.com/))

**Install the extension:**

```bash
gh extension install ralmeida/gh-secrets-migrator
```

**Verify installation:**

```bash
gh secrets-migrator --help
```

**Usage:**

```bash
gh secrets-migrator \
  --source-org SOURCE_ORG \
  --source-repo SOURCE_REPO \
  --target-org TARGET_ORG \
  --target-repo TARGET_REPO \
  --source-pat SOURCE_PAT \
  --target-pat TARGET_PAT \
  [--verbose]
```

**Example:**

```bash
gh secrets-migrator \
  --source-org my-org \
  --source-repo old-repo \
  --target-org my-org \
  --target-repo new-repo \
  --source-pat ghp_xxxxxxxxxxxxxxxxxxxx \
  --target-pat ghp_yyyyyyyyyyyyyyyyyyyyyy \
  --verbose
```

### Alternative Installation Methods

#### Option 1: Build from Source

**Requirements:**
- Go 1.21 or later ([Install Go](https://golang.org/dl/))
- Git

**Clone and build:**

```bash
git clone https://github.com/renan-alm/gh-secrets-migrator.git
cd gh-secrets-migrator
make build
```

The build command automatically embeds the current git commit hash as the version number. You can verify it by running:

```bash
./gh-secrets-migrator --help
```

**Install as `gh` extension manually:**

```bash
mkdir -p ~/.local/share/gh/extensions/gh-secrets-migrator
cp gh-secrets-migrator ~/.local/share/gh/extensions/gh-secrets-migrator/gh-secrets-migrator
gh secrets-migrator --help
```

#### Option 2: Download Pre-built Binary

Pre-built binaries are available in the [releases section](https://github.com/renan-alm/gh-secrets-migrator/releases).

**macOS (ARM64):**

```bash
wget https://github.com/renan-alm/gh-secrets-migrator/releases/download/v1.0.0/gh-secrets-migrator_1.0.0_darwin_arm64
chmod +x gh-secrets-migrator_1.0.0_darwin_arm64
sudo mv gh-secrets-migrator_1.0.0_darwin_arm64 /usr/local/bin/gh-secrets-migrator
```

**Linux (AMD64):**

```bash
wget https://github.com/renan-alm/gh-secrets-migrator/releases/download/v1.0.0/gh-secrets-migrator_1.0.0_linux_amd64
chmod +x gh-secrets-migrator_1.0.0_linux_amd64
sudo mv gh-secrets-migrator_1.0.0_linux_amd64 /usr/local/bin/gh-secrets-migrator
```

**Windows (PowerShell):**

```powershell
Invoke-WebRequest -Uri "https://github.com/renan-alm/gh-secrets-migrator/releases/download/v1.0.0/gh-secrets-migrator_1.0.0_windows_amd64.exe" -OutFile gh-secrets-migrator.exe
.\gh-secrets-migrator.exe --help
```

#### Option 3: Install with Go

```bash
go install github.com/renan-alm/gh-secrets-migrator/cmd/gh-secrets-migrator@latest
gh-secrets-migrator --help
```

## Usage

The recommended way to use this tool is as a `gh` CLI extension:

```bash
gh secrets-migrator \
  --source-org SOURCE_ORG \
  --source-repo SOURCE_REPO \
  --target-org TARGET_ORG \
  --target-repo TARGET_REPO \
  --source-pat SOURCE_PAT \
  --target-pat TARGET_PAT \
  [--verbose]
```

### Required Flags

- `--source-org`: The organization containing the source repository
- `--source-repo`: The source repository name
- `--target-org`: The organization containing the target repository
- `--target-repo`: The target repository name
- `--source-pat`: Personal Access Token for the source repository
- `--target-pat`: Personal Access Token for the target repository

### Optional Flags

- `--verbose`: Enable verbose logging for detailed output
- `--load`: Load both `source-pat` and `target-pat` from `GITHUB_TOKEN` environment variable (skips both PAT requirements)

### Example

```bash
gh secrets-migrator \
  --source-org my-org \
  --source-repo old-repo \
  --target-org my-org \
  --target-repo new-repo \
  --source-pat ghp_xxxxxxxxxxxxxxxxxxxx \
  --target-pat ghp_yyyyyyyyyyyyyyyyyyyyyy \
  --verbose
```

### Using GITHUB_TOKEN with --load

If you have `GITHUB_TOKEN` set in your environment (e.g., from `gh auth` or CI/CD), you can use the `--load` flag to automatically use it as both the source and target PATs:

```bash
# Set GITHUB_TOKEN first (or it's already set from gh CLI)
export GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxx

# Now you don't need --source-pat or --target-pat
gh secrets-migrator \
  --source-org my-org \
  --source-repo old-repo \
  --target-org my-org \
  --target-repo new-repo \
  --load \
  --verbose
```

## Development

### Make Targets

Use the provided Makefile for common development tasks:

```bash
make help          # Show all available commands
make build         # Build the binary
make build-all     # Build for all platforms
make test          # Run tests with coverage
make coverage      # Display test coverage report
make fmt           # Format code
make lint          # Run linter
make vet           # Run go vet
make dev           # Development workflow (fmt + vet + build)
make all           # Run all checks and build
make clean         # Clean build artifacts
make install       # Build and install locally
```

### Building for Different Platforms

```bash
# Using Make (preferred)
make build-all

# Or manually for specific platforms with version info
# Get the current git commit hash
COMMIT_HASH=$(git rev-parse --short HEAD)

# Build for different platforms
GOOS=linux GOARCH=amd64 go build -ldflags "-X main.Version=$COMMIT_HASH" -o gh-secrets-migrator-linux-amd64 ./cmd/gh-secrets-migrator
GOOS=darwin GOARCH=arm64 go build -ldflags "-X main.Version=$COMMIT_HASH" -o gh-secrets-migrator-darwin-arm64 ./cmd/gh-secrets-migrator
GOOS=windows GOARCH=amd64 go build -ldflags "-X main.Version=$COMMIT_HASH" -o gh-secrets-migrator.exe ./cmd/gh-secrets-migrator
```

### Running Tests

```bash
# Run all tests
make test

# Run with verbose output
go test -v ./...

# Run specific test
go test -v -run TestName ./...

# View coverage report
make coverage
```

### Code Quality

```bash
# Format code
make fmt

# Run linter (requires golangci-lint)
make lint

# Run go vet
make vet
```

## How It Works

1. **Authenticates** with both source and target repositories using the provided PATs
2. **Retrieves** the target repository's public key for encryption
3. **Stores** the target PAT as a temporary secret in the source repository
4. **Creates** a new branch (`migrate-secrets`) in the source repository
5. **Generates** a GitHub Actions workflow that will:
   - Retrieve all secrets from the source repository
   - Encrypt each secret with the target repository's public key
   - Create each secret in the target repository
   - Clean up the temporary secret and branch
6. **Commits** the workflow file to trigger the migration

The workflow runs on Windows with PowerShell and uses the `Sodium.Core` NuGet package for encryption, ensuring compatibility with GitHub's secret encryption standards.

## Security Considerations

- **PATs are never stored**: They are only used during execution and in the generated workflow
- **Encryption**: Secrets are encrypted using libsodium's sealed box encryption
- **Temporary cleanup**: The temporary `SECRETS_MIGRATOR_PAT` secret is automatically deleted after migration
- **Ignored secrets**: `github_token` and `SECRETS_MIGRATOR_PAT` are not migrated
- **No logging of secrets**: Actual secret values are never logged or displayed

## Troubleshooting

### "Failed to get target repository public key"

- Ensure the target PAT has `actions:read` and `secrets:write` permissions
- Verify the repository path is correct
- Check that the target repository exists and is accessible

### "Failed to create SECRETS_MIGRATOR_PAT secret"

- Ensure the source PAT has `repo` and `admin:repo_hook` permissions
- Verify both repositories exist
- Check that you have write access to the source repository

### "Failed to create workflow file"

- Ensure the `.github/workflows` directory can be created
- Check that the source PAT has write access to the repository
- Verify the branch was created successfully

## Dependencies

The project uses the following key dependencies:

- **github.com/google/go-github/v57**: Official GitHub API client library
- **github.com/spf13/cobra**: CLI framework for building commands
- **golang.org/x/crypto**: Cryptographic operations
- **golang.org/x/oauth2**: OAuth2 authentication

See `go.mod` for the complete list of dependencies.

## Release Process

Releases are automated using GoReleaser. To create a new release:

```bash
# Create a git tag
git tag v1.0.0

# Push the tag
git push origin v1.0.0

# GoReleaser will automatically build and publish
# (Requires GitHub Actions workflow to be configured)
```

See `.goreleaser.yml` for release configuration details.

## Comparison with Original C# Version

| Feature | C# Version | Go Version |
|---------|-----------|-----------|
| Runtime | .NET 6 required | No runtime needed |
| Binary size | ~100MB+ (with runtime) | ~8MB standalone |
| Single binary | No | Yes |
| CLI framework | System.CommandLine | Cobra |
| Project structure | Flat | Follows Go conventions |
| Build tool | MSBuild/dotnet CLI | go build / Make |
| Cross-platform | Requires runtime per platform | Single compile per platform |
| Code organization | Monolithic | Package-based |

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Demo

See the [project repository](https://github.com/renan-alm/gh-secrets-migrator) for documentation and examples.

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -am 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

Please ensure:

- Code is formatted with `go fmt`
- Tests pass with `go test ./...`
- Code passes linting with `golangci-lint`

## Original Project

This project migrates secrets between GitHub repositories efficiently and securely.
