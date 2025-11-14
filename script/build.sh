#!/usr/bin/env bash
# GitHub CLI Extension Entry Point
# This script is the main entry point for the gh-secrets-migrator extension
# It delegates to the precompiled binary based on the current platform
# Reference: https://docs.github.com/en/github-cli/github-cli/creating-github-cli-extensions

set -e

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EXT_DIR="$(dirname "$SCRIPT_DIR")"

# Detect current platform and architecture
OS=$(uname -s)
ARCH=$(uname -m)

# Map architecture names
case "$ARCH" in
  x86_64|amd64)
    ARCH="amd64"
    ;;
  arm64|aarch64)
    ARCH="arm64"
    ;;
esac

# Map OS names to binary names
case "$OS" in
  Darwin)
    PLATFORM="darwin"
    ;;
  Linux)
    PLATFORM="linux"
    ;;
  MINGW*|MSYS*|CYGWIN*)
    PLATFORM="windows"
    EXE_EXT=".exe"
    ;;
  *)
    echo "❌ Error: Unsupported platform: $OS" >&2
    exit 1
    ;;
esac

# Construct binary name
BINARY_NAME="gh-secrets-migrator${EXE_EXT}"
BINARY_PATH="$EXT_DIR/dist/bin/$BINARY_NAME"

# Check if binary exists
if [ ! -f "$BINARY_PATH" ]; then
  echo "❌ Error: Binary not found at $BINARY_PATH" >&2
  echo "" >&2
  echo "Please build the extension first by running:" >&2
  echo "  make build" >&2
  exit 1
fi

# Make binary executable
chmod +x "$BINARY_PATH"

# Delegate all arguments to the binary
exec "$BINARY_PATH" "$@"
EOF
