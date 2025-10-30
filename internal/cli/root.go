// Package cli provides the command-line interface.
package cli

import (
	"context"
	"fmt"
	"os"

	"github.com/spf13/cobra"

	"github.com/renan-alm/gh-secrets-migrator/internal/logger"
	"github.com/renan-alm/gh-secrets-migrator/internal/migrator"
)

var (
	sourceOrg  string
	sourceRepo string
	targetOrg  string
	targetRepo string
	sourcePat  string
	targetPat  string
	verbose    bool
)

// NewRootCommand creates the root cobra command.
func NewRootCommand() *cobra.Command {
	cmd := &cobra.Command{
		Use:   "gh-secrets-migrator",
		Short: "Migrate GitHub secrets from one repository to another",
		Long: `A tool to migrate GitHub repository secrets from a source repository to a target repository.
All secrets are encrypted using the target repository's public key before migration.`,
		RunE: runMigration,
	}

	cmd.PersistentFlags().StringVar(&sourceOrg, "source-org", "", "Source organization name (required)")
	_ = cmd.MarkPersistentFlagRequired("source-org")

	cmd.PersistentFlags().StringVar(&sourceRepo, "source-repo", "", "Source repository name (required)")
	_ = cmd.MarkPersistentFlagRequired("source-repo")

	cmd.PersistentFlags().StringVar(&targetOrg, "target-org", "", "Target organization name (required)")
	_ = cmd.MarkPersistentFlagRequired("target-org")

	cmd.PersistentFlags().StringVar(&targetRepo, "target-repo", "", "Target repository name (required)")
	_ = cmd.MarkPersistentFlagRequired("target-repo")

	cmd.PersistentFlags().StringVar(&sourcePat, "source-pat", "", "Personal Access Token for source repository (optional if GITHUB_TOKEN is set)")
	cmd.PersistentFlags().StringVar(&targetPat, "target-pat", "", "Personal Access Token for target repository (optional if GITHUB_TOKEN is set)")

	cmd.PersistentFlags().BoolVar(&verbose, "verbose", false, "Enable verbose logging")

	return cmd
}

func runMigration(_ *cobra.Command, _ []string) error {
	log := logger.New(verbose)

	// Handle GITHUB_TOKEN environment variable
	sourcePatValue := sourcePat
	targetPatValue := targetPat

	githubToken := os.Getenv("GITHUB_TOKEN")
	if githubToken != "" {
		log.Infof("GITHUB_TOKEN environment variable detected, using it for both source and target authentication")
		sourcePatValue = githubToken
		targetPatValue = githubToken
	}

	// Validate that we have PATs for both source and target
	if sourcePatValue == "" || targetPatValue == "" {
		return fmt.Errorf("source-pat and target-pat are required (or set GITHUB_TOKEN environment variable)")
	}

	config := &migrator.Config{
		SourceOrg:  sourceOrg,
		SourceRepo: sourceRepo,
		TargetOrg:  targetOrg,
		TargetRepo: targetRepo,
		SourcePAT:  sourcePatValue,
		TargetPAT:  targetPatValue,
		Verbose:    verbose,
	}

	ctx := context.Background()
	m := migrator.New(ctx, config, log)

	if err := m.Run(ctx); err != nil {
		return fmt.Errorf("migration failed: %w", err)
	}

	return nil
}
