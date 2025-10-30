// Package migrator provides the main migration logic.
package migrator

import (
	"context"
	"fmt"
	"strings"

	"github.com/renan-alm/gh-secrets-migrator/internal/github"
	"github.com/renan-alm/gh-secrets-migrator/internal/logger"
)

// Config holds the migration configuration.
type Config struct {
	SourceOrg  string
	SourceRepo string
	TargetOrg  string
	TargetRepo string
	SourcePAT  string
	TargetPAT  string
	Verbose    bool
}

// Migrator handles the migration process.
type Migrator struct {
	config    *Config
	sourceAPI *github.Client
	targetAPI *github.Client
	log       *logger.Logger
}

// New creates a new migrator instance.
func New(ctx context.Context, config *Config, log *logger.Logger) *Migrator {
	sourceAPI := github.New(ctx, config.SourcePAT, log)
	targetAPI := github.New(ctx, config.TargetPAT, log)

	return &Migrator{
		config:    config,
		sourceAPI: sourceAPI,
		targetAPI: targetAPI,
		log:       log,
	}
}

// Run executes the migration process.
func (m *Migrator) Run(ctx context.Context) error {
	m.log.Info("Migrating Secrets...")
	m.log.Infof("SOURCE ORG: %s", m.config.SourceOrg)
	m.log.Infof("SOURCE REPO: %s", m.config.SourceRepo)
	m.log.Infof("TARGET ORG: %s", m.config.TargetOrg)
	m.log.Infof("TARGET REPO: %s", m.config.TargetRepo)

	branchName := "migrate-secrets"

	// Get all secrets from source repository (read-only, for information)
	m.log.Debug("Fetching list of secrets from source repository...")
	secretNames, err := m.sourceAPI.ListRepoSecrets(ctx, m.config.SourceOrg, m.config.SourceRepo)
	if err != nil {
		return fmt.Errorf("failed to list secrets: %w", err)
	}

	// Filter out system secrets and display what will be migrated
	var secretsToMigrate []string
	for _, name := range secretNames {
		if name != "github_token" && name != "SECRETS_MIGRATOR_PAT" {
			secretsToMigrate = append(secretsToMigrate, name)
		}
	}

	if len(secretsToMigrate) == 0 {
		m.log.Info("No secrets to migrate (found only system secrets)")
		return nil
	}

	m.log.Infof("Secrets to migrate (%d total):", len(secretsToMigrate))
	for _, name := range secretsToMigrate {
		m.log.Infof("  - %s", name)
	}

	// Get default branch and commit SHA
	m.log.Debug("Getting default branch...")
	defaultBranch, err := m.sourceAPI.GetDefaultBranch(ctx, m.config.SourceOrg, m.config.SourceRepo)
	if err != nil {
		return fmt.Errorf("failed to get default branch: %w", err)
	}
	m.log.Debugf("Default branch: %s", defaultBranch)

	masterCommitSha, err := m.sourceAPI.GetCommitSha(ctx, m.config.SourceOrg, m.config.SourceRepo, defaultBranch)
	if err != nil {
		return fmt.Errorf("failed to get commit SHA: %w", err)
	}

	// Delete the migration branch if it already exists (cleanup from previous run)
	m.log.Debugf("Checking if branch %s exists...", branchName)
	err = m.sourceAPI.DeleteBranch(ctx, m.config.SourceOrg, m.config.SourceRepo, branchName)
	if err != nil {
		// It's okay if the branch doesn't exist, only log at debug level
		m.log.Debugf("Branch %s does not exist or could not be deleted (this is normal): %v", branchName, err)
	} else {
		m.log.Debugf("Deleted existing branch %s", branchName)
	}

	// Create the migration branch
	m.log.Debugf("Creating branch %s...", branchName)
	err = m.sourceAPI.CreateBranch(ctx, m.config.SourceOrg, m.config.SourceRepo, branchName, masterCommitSha)
	if err != nil {
		return fmt.Errorf("failed to create branch: %w", err)
	}

	// Create placeholder secrets in target repository
	m.log.Infof("Creating placeholder secrets in target repository...")
	for _, secretName := range secretsToMigrate {
		m.log.Debugf("Creating placeholder for secret: %s", secretName)
		err = m.targetAPI.CreateRepoSecretPlaintext(ctx, m.config.TargetOrg, m.config.TargetRepo, secretName, "REPLACE_ME_LATER")
		if err != nil {
			return fmt.Errorf("failed to create placeholder for secret %s: %w", secretName, err)
		}
		m.log.Infof("  ✓ Created placeholder for '%s'", secretName)
	}

	// Generate and create the workflow file
	workflow := GenerateWorkflow(m.config.TargetOrg, m.config.TargetRepo, branchName, secretsToMigrate)
	m.log.Debug("Creating workflow file...")
	err = m.sourceAPI.CreateFile(ctx, m.config.SourceOrg, m.config.SourceRepo, branchName, ".github/workflows/migrate-secrets.yml", workflow)
	if err != nil {
		return fmt.Errorf("failed to create workflow file: %w", err)
	}

	m.log.Successf("Secrets migration in progress. Check on status at https://github.com/%s/%s/actions", m.config.SourceOrg, m.config.SourceRepo)

	return nil
}

// GenerateWorkflow generates the GitHub Actions workflow for secret migration.
func GenerateWorkflow(targetOrg, targetRepo, branchName string, secretNames []string) string {
	workflow := fmt.Sprintf(`name: move-secrets
on:
  push:
    branches: [ "%s" ]
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'

      - name: Migrate Secrets
        env:
          REPO_SECRETS: ${{ toJSON(secrets) }}
          TARGET_PAT: ${{ secrets.SECRETS_MIGRATOR_PAT }}
          TARGET_ORG: '%s'
          TARGET_REPO: '%s'
          GH_TOKEN: ${{ secrets.SECRETS_MIGRATOR_PAT }}
        run: |
          #!/bin/bash
          set -e

          # Install tweetnacl for encryption
          npm install tweetnacl --save

          # Get target repo public key using GH CLI
          echo "Fetching target repo public key..."
          PUBLIC_KEY_RESPONSE=$(gh api repos/$TARGET_ORG/$TARGET_REPO/actions/secrets/public-key --jq .)
          PUBLIC_KEY=$(echo "$PUBLIC_KEY_RESPONSE" | jq -r '.key')
          KEY_ID=$(echo "$PUBLIC_KEY_RESPONSE" | jq -r '.key_id')

          # Create Node.js script for encryption
          cat > encrypt.js << 'EOF'
          const nacl = require('tweetnacl');

          const publicKeyBase64 = process.argv[1];
          const secretValue = process.argv[2];

          // Decode public key from base64
          const publicKey = Buffer.from(publicKeyBase64, 'base64');

          // Encrypt using sealed box (anonymous encryption)
          const secretBytes = Buffer.from(secretValue, 'utf8');
          const encrypted = nacl.box.seal(secretBytes, publicKey);

          // Return as base64
          console.log(Buffer.from(encrypted).toString('base64'));
          EOF

          # Parse secrets JSON and migrate each one
          echo "Migrating secrets..."
          echo "$REPO_SECRETS" | jq -r 'to_entries[] | "\(.key)|\(.value)"' | while IFS='|' read -r SECRET_NAME SECRET_VALUE; do
            if [[ "$SECRET_NAME" != "github_token" && "$SECRET_NAME" != "SECRETS_MIGRATOR_PAT" ]]; then
              echo "Migrating Secret: $SECRET_NAME"
              
              # Encrypt the secret using Node.js
              ENCRYPTED=$(node encrypt.js "$PUBLIC_KEY" "$SECRET_VALUE")
              
              # Create secret in target repo using GH CLI
              gh secret set "$SECRET_NAME" \
                --body "$ENCRYPTED" \
                --repo "$TARGET_ORG/$TARGET_REPO" \
                --env actions || echo "Warning: Could not set secret $SECRET_NAME"
            fi
          done

          # Cleanup: delete SECRETS_MIGRATOR_PAT from source repo
          echo "Cleaning up..."
          gh secret delete SECRETS_MIGRATOR_PAT --repo ${{ github.repository }} --confirm || echo "Warning: Could not delete SECRETS_MIGRATOR_PAT"

          # Delete the migration branch
          gh api repos/${{ github.repository_owner }}/${{ github.repository_name }}/git/refs/heads/%s -X DELETE || echo "Warning: Could not delete branch"
        shell: bash
`, branchName, targetOrg, targetRepo, branchName)

	return strings.TrimSpace(workflow)
}
