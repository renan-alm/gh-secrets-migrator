// Package cli provides the command-line interface.
package cli

import (
	"context"
	"fmt"

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
	cmd.MarkPersistentFlagRequired("source-org")

	cmd.PersistentFlags().StringVar(&sourceRepo, "source-repo", "", "Source repository name (required)")
	cmd.MarkPersistentFlagRequired("source-repo")

	cmd.PersistentFlags().StringVar(&targetOrg, "target-org", "", "Target organization name (required)")
	cmd.MarkPersistentFlagRequired("target-org")

	cmd.PersistentFlags().StringVar(&targetRepo, "target-repo", "", "Target repository name (required)")
	cmd.MarkPersistentFlagRequired("target-repo")

	cmd.PersistentFlags().StringVar(&sourcePat, "source-pat", "", "Personal Access Token for source repository (required)")
	cmd.MarkPersistentFlagRequired("source-pat")

	cmd.PersistentFlags().StringVar(&targetPat, "target-pat", "", "Personal Access Token for target repository (required)")
	cmd.MarkPersistentFlagRequired("target-pat")

	cmd.PersistentFlags().BoolVar(&verbose, "verbose", false, "Enable verbose logging")

	return cmd
}

func runMigration(cmd *cobra.Command, args []string) error {
	log := logger.New(verbose)

	config := &migrator.Config{
		SourceOrg:  sourceOrg,
		SourceRepo: sourceRepo,
		TargetOrg:  targetOrg,
		TargetRepo: targetRepo,
		SourcePAT:  sourcePat,
		TargetPAT:  targetPat,
		Verbose:    verbose,
	}

	ctx := context.Background()
	m := migrator.New(ctx, config, log)

	if err := m.Run(ctx); err != nil {
		return fmt.Errorf("migration failed: %w", err)
	}

	return nil
}
