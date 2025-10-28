.PHONY: help build build-all test test-verbose test-race coverage clean fmt lint vet mod-tidy install dev all

# Variables
BINARY_NAME=gh-secrets-migrator
MAIN_PATH=./cmd/gh-secrets-migrator
VERSION?=$(shell git describe --tags --always --dirty)
LDFLAGS=-ldflags "-X main.Version=$(VERSION)"

help: ## Display this help screen
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

build: ## Build the binary
	go build $(LDFLAGS) -o $(BINARY_NAME) $(MAIN_PATH)

build-all: clean ## Build binaries for all platforms
	@echo "Building for multiple platforms..."
	GOOS=linux GOARCH=amd64 go build $(LDFLAGS) -o $(BINARY_NAME)-linux-amd64 $(MAIN_PATH)
	GOOS=linux GOARCH=arm64 go build $(LDFLAGS) -o $(BINARY_NAME)-linux-arm64 $(MAIN_PATH)
	GOOS=darwin GOARCH=amd64 go build $(LDFLAGS) -o $(BINARY_NAME)-darwin-amd64 $(MAIN_PATH)
	GOOS=darwin GOARCH=arm64 go build $(LDFLAGS) -o $(BINARY_NAME)-darwin-arm64 $(MAIN_PATH)
	GOOS=windows GOARCH=amd64 go build $(LDFLAGS) -o $(BINARY_NAME)-windows-amd64.exe $(MAIN_PATH)
	@echo "Build complete!"

test: ## Run tests with coverage
	go test -v -race -coverprofile=coverage.out ./...

test-verbose: ## Run tests with verbose output
	go test -v -race ./...

test-race: ## Run tests with race detector
	go test -race ./...

test-bench: ## Run benchmark tests
	go test -bench=. -benchmem ./...

coverage: test ## Display test coverage
	go tool cover -html=coverage.out

coverage-report: test ## Print coverage report to console
	@echo "=== Coverage Report ===" 
	@go tool cover -func=coverage.out | tail -1

clean: ## Clean build artifacts
	rm -f $(BINARY_NAME) $(BINARY_NAME)-* coverage.out

fmt: ## Format code
	go fmt ./...

lint: ## Run linter (requires golangci-lint)
	@which golangci-lint > /dev/null || (echo "golangci-lint not found. Install with: brew install golangci-lint" && exit 1)
	golangci-lint run ./...

vet: ## Run go vet
	go vet ./...

mod-tidy: ## Tidy and verify dependencies
	go mod tidy
	go mod verify

install: build ## Build and install the binary
	go install $(LDFLAGS) $(MAIN_PATH)

dev: fmt vet build ## Format, vet, and build (development workflow)

all: fmt vet lint test build ## Run all checks and build
	@echo "Development build complete!"

all: fmt lint vet test build ## Run all checks and build
	@echo "All checks passed!"

.PHONY: help build build-all test clean fmt lint vet coverage mod-tidy install dev all
