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
	loadAuth   bool
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
	cmd.MarkPersistentFlagRequired("source-org")

	cmd.PersistentFlags().StringVar(&sourceRepo, "source-repo", "", "Source repository name (required)")
	cmd.MarkPersistentFlagRequired("source-repo")

	cmd.PersistentFlags().StringVar(&targetOrg, "target-org", "", "Target organization name (required)")
	cmd.MarkPersistentFlagRequired("target-org")

	cmd.PersistentFlags().StringVar(&targetRepo, "target-repo", "", "Target repository name (required)")
	cmd.MarkPersistentFlagRequired("target-repo")

	cmd.PersistentFlags().StringVar(&sourcePat, "source-pat", "", "Personal Access Token for source repository (required unless --load is used)")
	cmd.PersistentFlags().StringVar(&targetPat, "target-pat", "", "Personal Access Token for target repository (required unless --load is used)")

	cmd.PersistentFlags().BoolVar(&verbose, "verbose", false, "Enable verbose logging")

	cmd.PersistentFlags().BoolVar(&loadAuth, "load", false, "Load both source-pat and target-pat from GITHUB_TOKEN environment variable")

	return cmd
}

func runMigration(cmd *cobra.Command, args []string) error {
	log := logger.New(verbose)

	// Handle --load flag to use GITHUB_TOKEN for both source-pat and target-pat
	sourcePatValue := sourcePat
	targetPatValue := targetPat
	if loadAuth {
		token := os.Getenv("GITHUB_TOKEN")
		if token == "" {
			return fmt.Errorf("--load flag requires GITHUB_TOKEN environment variable to be set")
		}
		sourcePatValue = token
		targetPatValue = token
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
