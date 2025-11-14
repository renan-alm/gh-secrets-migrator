# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.1.0] - 2025-11-14

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

## [1.0.0] - 2025-11-07

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

[Unreleased]: https://github.com/renan-alm/gh-secrets-migrator/compare/v1.1.0...HEAD
[1.1.0]: https://github.com/renan-alm/gh-secrets-migrator/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/renan-alm/gh-secrets-migrator/releases/tag/v1.0.0
