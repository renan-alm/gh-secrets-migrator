#!/usr/bin/env bash
# Build script for gh-secrets-migrator extension
# This script is called by gh-extension-precompile action
# It receives the release tag as the first argument

set -e

TAG="$1"
if [ -z "$TAG" ]; then
  echo "Error: TAG argument is required"
  exit 1
fi

# Install dependencies
echo "Installing dependencies..."
python -m pip install --upgrade pip
pip install -r requirements.txt

# Build with PyInstaller
echo "Building with PyInstaller for current platform..."
python -m PyInstaller gh-secrets-migrator.spec --clean --distpath dist_temp

# Detect platform
OS=$(uname -s | tr '[:upper:]' '[:lower:]')
ARCH=$(uname -m)

# Normalize OS names
case "$OS" in
  darwin) OS="darwin" ;;
  linux) OS="linux" ;;
  mingw*|msys*|cygwin*) OS="windows" ;;
  *) echo "Unsupported OS: $OS"; exit 1 ;;
esac

# Normalize architecture
case "$ARCH" in
  x86_64|amd64) ARCH="amd64" ;;
  arm64|aarch64) ARCH="arm64" ;;
  i386|i686) ARCH="386" ;;
  *) echo "Unsupported architecture: $ARCH"; exit 1 ;;
esac

# Set extension for Windows
EXT=""
if [ "$OS" = "windows" ]; then
  EXT=".exe"
fi

# Create dist directory if it doesn't exist
mkdir -p dist

# Copy the built binary to the expected location with the correct name
BINARY_NAME="gh-secrets-migrator_${TAG}_${OS}-${ARCH}${EXT}"
echo "Copying binary to dist/${BINARY_NAME}"

if [ -f "dist_temp/bin/gh-secrets-migrator${EXT}" ]; then
  cp "dist_temp/bin/gh-secrets-migrator${EXT}" "dist/${BINARY_NAME}"
else
  echo "Error: Binary not found at dist_temp/bin/gh-secrets-migrator${EXT}"
  exit 1
fi

# Clean up temporary dist
rm -rf dist_temp

echo "Build complete: dist/${BINARY_NAME}"
ls -lh "dist/${BINARY_NAME}"
