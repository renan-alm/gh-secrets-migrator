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

	// Get the public key from the target repository
	m.log.Debug("Getting target repository public key...")
	publicKey, publicKeyID, err := m.targetAPI.GetRepoPublicKey(ctx, m.config.TargetOrg, m.config.TargetRepo)
	if err != nil {
		return fmt.Errorf("failed to get target repository public key: %w", err)
	}

	// Create the target PAT secret in the source repository
	m.log.Debug("Creating SECRETS_MIGRATOR_PAT secret in source repository...")
	err = m.sourceAPI.CreateRepoSecret(ctx, m.config.SourceOrg, m.config.SourceRepo, publicKey, publicKeyID, "SECRETS_MIGRATOR_PAT", m.config.TargetPAT)
	if err != nil {
		return fmt.Errorf("failed to create SECRETS_MIGRATOR_PAT secret: %w", err)
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

	// Create the migration branch
	m.log.Debugf("Creating branch %s...", branchName)
	err = m.sourceAPI.CreateBranch(ctx, m.config.SourceOrg, m.config.SourceRepo, branchName, masterCommitSha)
	if err != nil {
		return fmt.Errorf("failed to create branch: %w", err)
	}

	// Generate and create the workflow file
	workflow := GenerateWorkflow(m.config.TargetOrg, m.config.TargetRepo, branchName)
	m.log.Debug("Creating workflow file...")
	err = m.sourceAPI.CreateFile(ctx, m.config.SourceOrg, m.config.SourceRepo, branchName, ".github/workflows/migrate-secrets.yml", workflow)
	if err != nil {
		return fmt.Errorf("failed to create workflow file: %w", err)
	}

	m.log.Successf("Secrets migration in progress. Check on status at https://github.com/%s/%s/actions", m.config.SourceOrg, m.config.SourceRepo)

	return nil
}

// GenerateWorkflow generates the GitHub Actions workflow for secret migration.
func GenerateWorkflow(targetOrg, targetRepo, branchName string) string {
	workflow := fmt.Sprintf(`name: move-secrets
on:
  push:
    branches: [ "%s" ]
jobs:
  build:
    runs-on: windows-latest
    steps:
      - name: Install Crypto Package
        run: |
          Install-Package -Name Sodium.Core -ProviderName NuGet -Scope CurrentUser -RequiredVersion 1.3.0 -Destination . -Force
        shell: pwsh
      - name: Migrate Secrets
        run: |
          $sodiumPath = Resolve-Path ".\Sodium.Core.1.3.0\lib\netstandard2.1\Sodium.Core.dll"
          [System.Reflection.Assembly]::LoadFrom($sodiumPath)

          $targetPat = [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes(":$($env:TARGET_PAT)"))
          $publicKeyResponse = Invoke-RestMethod -Uri "https://api.github.com/repos/$env:TARGET_ORG/$env:TARGET_REPO/actions/secrets/public-key" -Method "GET" -Headers @{ Authorization = "Basic $targetPat" }
          $publicKey = [Convert]::FromBase64String($publicKeyResponse.key)
          $publicKeyId = $publicKeyResponse.key_id
              
          $secrets = $env:REPO_SECRETS | ConvertFrom-Json
          $secrets | Get-Member -MemberType NoteProperty | ForEach-Object {
            $secretName = $_.Name
            $secretValue = $secrets."$secretName"
     
            if ($secretName -ne "github_token" -and $secretName -ne "SECRETS_MIGRATOR_PAT") {
              Write-Output "Migrating Secret: $secretName"
              $secretBytes = [Text.Encoding]::UTF8.GetBytes($secretValue)
              $sealedPublicKeyBox = [Sodium.SealedPublicKeyBox]::Create($secretBytes, $publicKey)
              $encryptedSecret = [Convert]::ToBase64String($sealedPublicKeyBox)
                 
              $Params = @{
                Uri = "https://api.github.com/repos/$env:TARGET_ORG/$env:TARGET_REPO/actions/secrets/$secretName"
                Headers = @{
                  Authorization = "Basic $targetPat"
                }
                Method = "PUT"
                Body = "{ \"encrypted_value\": \"$encryptedSecret\", \"key_id\": \"$publicKeyId\" }"
              }

              $createSecretResponse = Invoke-RestMethod @Params
            }
          }

          Write-Output "Cleaning up..."
          Invoke-RestMethod -Uri "https://api.github.com/repos/${{ github.repository }}/git/${{ github.ref }}" -Method "DELETE" -Headers @{ Authorization = "Basic $targetPat" }
          Invoke-RestMethod -Uri "https://api.github.com/repos/${{ github.repository }}/actions/secrets/SECRETS_MIGRATOR_PAT" -Method "DELETE" -Headers @{ Authorization = "Basic $targetPat" }
        env:
          REPO_SECRETS: ${{ toJSON(secrets) }}
          TARGET_PAT: ${{ secrets.SECRETS_MIGRATOR_PAT }}
          TARGET_ORG: '%s'
          TARGET_REPO: '%s'
        shell: pwsh
`, branchName, targetOrg, targetRepo)

	return strings.TrimSpace(workflow)
}
