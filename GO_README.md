# GitHub Secrets Migrator - Go Version

A command-line tool written in Go to migrate GitHub repository secrets from one repository to another. This is a complete rewrite of the original C# implementation in Go.

## Why Go?

This Go version offers several advantages over the C# implementation:

- **Single binary**: No runtime dependencies, just compile and run
- **Smaller footprint**: ~5-10MB compiled binary vs .NET's larger size  
- **Better for CLI tools**: Go's design philosophy aligns perfectly with command-line utilities
- **Cross-platform**: Easy compilation to Windows, macOS, and Linux
- **No installation required**: Users can just download and run the binary

## Features

- Migrates all secrets from a source GitHub repository to a target repository
- Securely encrypts secrets using the target repository's public key
- Automatically generates and commits a GitHub Actions workflow
- Workflow handles all encryption and migration via PowerShell
- Supports verbose logging for troubleshooting

## Prerequisites

- Go 1.21 or later (for building from source)
- GitHub Personal Access Tokens (PATs) for both source and target repositories with appropriate permissions
- Permissions to create branches, workflows, and secrets in the source repository

## Installation

### Option 1: Download Pre-built Binary

Pre-built binaries are available in the [releases section](https://github.com/renan-alm/gh-secrets-migrator/releases).

### Option 2: Build from Source

```bash
git clone https://github.com/renan-alm/gh-secrets-migrator.git
cd gh-secrets-migrator
go build -o gh-secrets-migrator .
```

### Option 3: Install with Go

```bash
go install github.com/renan-alm/gh-secrets-migrator@latest
```

## Usage

```bash
gh-secrets-migrator \
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

### Example

```bash
./gh-secrets-migrator \
  --source-org my-org \
  --source-repo old-repo \
  --target-org my-org \
  --target-repo new-repo \
  --source-pat ghp_xxxxxxxxxxxxxxxxxxxx \
  --target-pat ghp_yyyyyyyyyyyyyyyyyyyyyy \
  --verbose
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

- **PATs are never stored**: They are only used during the execution of this tool and the generated workflow
- **Encryption**: Secrets are encrypted using libsodium's sealed box encryption
- **Temporary cleanup**: The temporary `SECRETS_MIGRATOR_PAT` secret is automatically deleted after migration
- **Ignored secrets**: `github_token` and `SECRETS_MIGRATOR_PAT` are not migrated

## Comparison with Original C# Version

| Feature | C# Version | Go Version |
|---------|-----------|-----------|
| Runtime | .NET 6 required | No runtime needed |
| Binary size | ~100MB+ (with runtime) | ~8MB standalone |
| Single binary | No | Yes |
| CLI framework | System.CommandLine | Cobra |
| Compilation | MSBuild/dotnet CLI | go build |
| Cross-platform | Requires runtime on each platform | Single compile per platform |

## Troubleshooting

### "Failed to get target repository public key"

- Ensure the target PAT has `actions:read` and `secrets:write` permissions
- Verify the repository path is correct

### "Failed to create SECRETS_MIGRATOR_PAT secret"

- Ensure the source PAT has `repo` and `admin:repo_hook` permissions
- Verify both repositories exist

### "Failed to create workflow file"

- Ensure the `.github/workflows` directory exists or will be created
- Check that the source PAT has write access to the repository

## Development

### Project Structure

```text
.
├── main.go          # CLI setup and migration orchestration
├── github_api.go    # GitHub API client and operations
├── logger.go        # Logging utilities
├── go.mod           # Go module dependencies
├── go.sum           # Go module checksums
└── src/             # Original C# source files (for reference)
```

### Building for Different Platforms

```bash
# macOS (ARM64)
GOOS=darwin GOARCH=arm64 go build -o gh-secrets-migrator-darwin-arm64 .

# macOS (Intel)
GOOS=darwin GOARCH=amd64 go build -o gh-secrets-migrator-darwin-amd64 .

# Linux
GOOS=linux GOARCH=amd64 go build -o gh-secrets-migrator-linux-amd64 .

# Windows
GOOS=windows GOARCH=amd64 go build -o gh-secrets-migrator.exe .
```

## Dependencies

- **github.com/google/go-github/v57**: Official GitHub API client library
- **github.com/spf13/cobra**: Popular CLI framework
- **golang.org/x/crypto**: Cryptographic operations (libsodium bindings)
- **golang.org/x/oauth2**: OAuth2 authentication

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Demo

See the [original project demo](https://youtu.be/B5Xyp8VwR54) for a walkthrough of how the migration process works.

## Contributing

Contributions are welcome! Please open an issue or submit a pull request.

## Original Project

This project is maintained as a high-performance Go CLI tool for migrating GitHub secrets.
