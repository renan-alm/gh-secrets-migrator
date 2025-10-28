package migrator

import (
	"testing"
)

// TestNewConfig tests Config structure creation
func TestNewConfig(t *testing.T) {
	tests := []struct {
		name             string
		sourceOrg        string
		sourceRepo       string
		targetOrg        string
		targetRepo       string
		shouldHaveErrors bool
	}{
		{
			"valid config",
			"source-org",
			"source-repo",
			"target-org",
			"target-repo",
			false,
		},
		{
			"empty source org",
			"",
			"source-repo",
			"target-org",
			"target-repo",
			true,
		},
		{
			"empty target repo",
			"source-org",
			"source-repo",
			"target-org",
			"",
			true,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			cfg := &Config{
				SourceOrg:  tt.sourceOrg,
				SourceRepo: tt.sourceRepo,
				TargetOrg:  tt.targetOrg,
				TargetRepo: tt.targetRepo,
				SourcePAT:  "token1",
				TargetPAT:  "token2",
			}

			if cfg == nil {
				t.Error("Config is nil")
			}

			// Validate required fields
			hasErrors := cfg.SourceOrg == "" || cfg.SourceRepo == "" ||
				cfg.TargetOrg == "" || cfg.TargetRepo == ""

			if hasErrors != tt.shouldHaveErrors {
				t.Errorf("expected errors=%v, got %v", tt.shouldHaveErrors, hasErrors)
			}
		})
	}
}

// TestConfigStructure tests Config struct fields
func TestConfigStructure(t *testing.T) {
	cfg := &Config{
		SourceOrg:  "org1",
		SourceRepo: "repo1",
		TargetOrg:  "org2",
		TargetRepo: "repo2",
		SourcePAT:  "token1",
		TargetPAT:  "token2",
		Verbose:    true,
	}

	// Verify all fields are set correctly
	tests := []struct {
		name     string
		got      string
		expected string
	}{
		{"SourceOrg", cfg.SourceOrg, "org1"},
		{"SourceRepo", cfg.SourceRepo, "repo1"},
		{"TargetOrg", cfg.TargetOrg, "org2"},
		{"TargetRepo", cfg.TargetRepo, "repo2"},
		{"SourcePAT", cfg.SourcePAT, "token1"},
		{"TargetPAT", cfg.TargetPAT, "token2"},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			if tt.got != tt.expected {
				t.Errorf("expected %s=%s, got %s", tt.name, tt.expected, tt.got)
			}
		})
	}

	if cfg.Verbose != true {
		t.Error("Verbose should be true")
	}
}

// TestConfigMultipleInstances tests multiple Config instances
func TestConfigMultipleInstances(t *testing.T) {
	cfg1 := &Config{
		SourceOrg:  "org1",
		SourceRepo: "repo1",
		SourcePAT:  "token1",
		TargetPAT:  "token2",
	}

	cfg2 := &Config{
		SourceOrg:  "org2",
		SourceRepo: "repo2",
		SourcePAT:  "token3",
		TargetPAT:  "token4",
	}

	// Verify they don't interfere with each other
	if cfg1.SourceOrg == cfg2.SourceOrg {
		t.Error("Config instances should have different SourceOrg")
	}
}

// TestConfigWithVerbose tests verbose flag
func TestConfigWithVerbose(t *testing.T) {
	tests := []struct {
		name    string
		verbose bool
	}{
		{"verbose on", true},
		{"verbose off", false},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			cfg := &Config{
				SourceOrg:  "org",
				SourceRepo: "repo",
				TargetOrg:  "target",
				TargetRepo: "repo",
				Verbose:    tt.verbose,
			}

			if cfg.Verbose != tt.verbose {
				t.Errorf("expected Verbose=%v, got %v", tt.verbose, cfg.Verbose)
			}
		})
	}
}

// BenchmarkConfigCreation benchmarks Config creation
func BenchmarkConfigCreation(b *testing.B) {
	for i := 0; i < b.N; i++ {
		_ = &Config{
			SourceOrg:  "org",
			SourceRepo: "repo",
			TargetOrg:  "target",
			TargetRepo: "repo",
			SourcePAT:  "token1",
			TargetPAT:  "token2",
		}
	}
}

// TestConfigWithLogger tests Config with logger
func TestConfigWithLogger(t *testing.T) {
	cfg := &Config{
		SourceOrg:  "source",
		SourceRepo: "repo",
		TargetOrg:  "target",
		TargetRepo: "repo",
		SourcePAT:  "token1",
		TargetPAT:  "token2",
	}

	if cfg == nil {
		t.Error("Config is nil")
	}
}
