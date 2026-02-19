# Changelog

All notable changes to this project will be documented in this file.

This changelog is auto-generated from [Conventional Commits](https://www.conventionalcommits.org/).
This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.0] - 2026-01-21
## [0.7.0] - 2026-02-19

### Added

- add darwin-arm64 support with matrix build strategy (930b407)

### Changed

- Update platform for macos-14 in release workflow (92bbf85)

### Fixed

- use macos-14-large for darwin-amd64 to avoid deprecated macos-13 (930b407)

### Other

- Add darwin-arm64 build support via matrix strategy (#66) (930b407)

## [0.7.0] - 2026-02-19

### Added

- add darwin-arm64 support with matrix build strategy (930b407)

### Fixed

- use macos-14 for darwin-amd64 to avoid deprecated macos-13 (930b407)

### Other

- Add darwin-arm64 build support via matrix strategy (#66) (930b407)

## [0.6.0] - 2026-02-11

### Added

- add endpoint configuration support for GHEC Data Residency and GHES (ae9ce01)

### Changed

- extract URL parsing logic and improve test naming (ae9ce01)
- add constant and helper for endpoint comparison logic (ae9ce01)

### Fixed

- correct GH_HOST extraction, normalize endpoints, and derive web URLs from API endpoints (ae9ce01)

### Other

- Add custom endpoint support for GHEC Data Residency and GHES (#63) (ae9ce01)

## [0.5.0] - 2026-02-02

### Added

- Update getting previous tag logic to exclude current tag (5330ae7)
- Add release notes download and update steps (d4a543e)

### Changed

- Improve commit message categorization (78be4e8)

## [0.5.0] - 2026-02-02

### Added

- Update getting previous tag logic to exclude current tag (5330ae7)
- Add release notes download and update steps (d4a543e)

## [0.5.0] - 2026-02-02

### Added

- Add release notes download and update steps (d4a543e)

## [0.5.0] - 2026-02-02

### Added

- Add release notes download and update steps (d4a543e)

## [0.5.0] - 2026-02-02

- Release 0.5.0

## [0.4.0] - 2026-01-26

### Changed

- Add token and fetch-depth to code checkout step (251214e)

### Other

- Add GitHub CLI extension support with PyInstaller binary compilation (#55) (c8d2b41)


### Added

- Rate limit watcher for GitHub API requests with automatic handling
- Dependabot configuration for automated dependency updates
- Pre-release checklist workflow for ensuring quality before releases
- Cross-platform build and release pipeline supporting Linux, macOS, and Windows
- Environment file (.env.example) for easier configuration management
- GitHub Copilot instructions for better AI-assisted development

### Improved

- Organization secrets are now filtered out during repository-to-repository migrations
- Environment creation logic now checks for existing environments to prevent overwriting configurations
- Enhanced CLI with better repository requirement messages
- Docker build process with updated configuration
- Comprehensive test coverage including organization secret filtering tests
- Enhanced workflow generator to handle repository-specific secrets

### Changed

- **Breaking**: Removed Python 3.8 and 3.9 support (now requires Python 3.10+)
- Consolidated CI/CD workflows (merged CI.yml and lint.yml into test-and-lint.yml)
- Updated GitHub Actions dependencies to latest versions
- Enhanced Makefile with improved cross-platform compatibility

### Fixed

- Environment overwrite issue in repository-to-repository migrations
- Cross-platform compatibility issues in build system and CI workflow
- Badge rendering in README

## [0.2.0] - 2025-11-14

### Added

- Comprehensive test coverage with pytest and fixtures
- Type checking with mypy for improved code quality
- Security scanning with bandit for vulnerability detection
- Code coverage reporting and Codecov integration
- Comprehensive logging module with multiple log levels
- Enhanced error handling and validation throughout the application
- Docker support with Dockerfile and docker-compose for easy deployment
- CI/CD workflow with automated testing across Python 3.8, 3.9, 3.10, 3.11, and 3.12
- GitHub Actions workflow generation for automated secret migration
- Configuration management system for handling application settings

### Improved

- Better code organization with modular structure (cli, clients, core, utils)
- Enhanced CLI command interface for better user experience
- Improved GitHub client with better error handling
- More robust workflow generator with validation

### Fixed

- Edge case handling in secret migration process
- Improved error messages for better debugging

## [0.1.0] - 2025-11-07

### Added

- Initial release of GitHub Secrets Migrator
- Core functionality to migrate secrets between GitHub repositories
- Support for repository environments
- Automatic encryption of secrets using GitHub's public key
- GitHub API client for repository operations
- Comprehensive README documentation with usage examples
- MIT License
- Migrates secrets from source to target repository
- Recreates repository environments in target repository
- Validates PAT permissions before migration
- Automatic cleanup of temporary secrets
- Docker containerization support
- Support for both explicit PATs and GITHUB_TOKEN environment variable
- Verbose logging mode for debugging

[Unreleased]: https://github.com/renan-alm/gh-secrets-migrator/compare/v0.3.0...HEAD
[0.3.0]: https://github.com/renan-alm/gh-secrets-migrator/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/renan-alm/gh-secrets-migrator/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/renan-alm/gh-secrets-migrator/releases/tag/v0.1.0
