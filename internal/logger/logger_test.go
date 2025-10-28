package logger

import (
	"testing"
)

// TestNewLogger tests logger creation
func TestNewLogger(t *testing.T) {
	tests := []struct {
		name    string
		verbose bool
	}{
		{"verbose enabled", true},
		{"verbose disabled", false},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			l := New(tt.verbose)
			if l == nil {
				t.Error("New() returned nil logger")
			}
		})
	}
}

// TestLoggerInfo tests Info logging
func TestLoggerInfo(t *testing.T) {
	tests := []struct {
		name    string
		message string
	}{
		{"simple message", "test message"},
		{"message with special chars", "test @#$% message"},
		{"empty message", ""},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			l := New(false)
			// Should not panic
			l.Info(tt.message)
		})
	}
}

// TestLoggerInfof tests formatted Info logging
func TestLoggerInfof(t *testing.T) {
	tests := []struct {
		name   string
		format string
		args   []interface{}
	}{
		{"simple format", "test %s", []interface{}{"message"}},
		{"multiple args", "test %s %d %v", []interface{}{"msg", 42, true}},
		{"no args", "simple message", []interface{}{}},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			l := New(false)
			// Should not panic
			l.Infof(tt.format, tt.args...)
		})
	}
}

// TestLoggerDebug tests Debug logging
func TestLoggerDebug(t *testing.T) {
	tests := []struct {
		name    string
		message string
		verbose bool
	}{
		{"verbose on", "debug message", true},
		{"verbose off", "debug message", false},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			l := New(tt.verbose)
			// Should not panic
			l.Debug(tt.message)
		})
	}
}

// TestLoggerDebugf tests formatted Debug logging
func TestLoggerDebugf(t *testing.T) {
	l := New(true)
	// Should not panic
	l.Debugf("debug %s", "message")
}

// TestLoggerSuccess tests Success logging
func TestLoggerSuccess(t *testing.T) {
	l := New(false)
	// Should not panic
	l.Success("operation succeeded")
}

// TestLoggerError tests Error logging
func TestLoggerError(t *testing.T) {
	tests := []struct {
		name    string
		message string
	}{
		{"simple error", "error occurred"},
		{"error with context", "failed to migrate secrets"},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			l := New(false)
			// Should not panic
			l.Errorf(tt.message)
		})
	}
}

// TestMultipleLoggers tests multiple logger instances
func TestMultipleLoggers(t *testing.T) {
	l1 := New(true)
	l2 := New(false)

	if l1 == nil || l2 == nil {
		t.Error("failed to create multiple loggers")
	}

	// Both should work independently
	l1.Info("logger 1")
	l2.Info("logger 2")
}

// TestLoggerSequence tests multiple log calls in sequence
func TestLoggerSequence(t *testing.T) {
	l := New(true)

	l.Info("starting")
	l.Debug("processing")
	l.Success("completed")
	l.Errorf("recovered from error")
}

// TestLoggerWithVerbose tests verbose flag behavior
func TestLoggerWithVerbose(t *testing.T) {
	t.Run("verbose enabled", func(t *testing.T) {
		l := New(true)
		l.Debug("debug enabled") // Should output
	})

	t.Run("verbose disabled", func(t *testing.T) {
		l := New(false)
		l.Debug("debug disabled") // Should not output
	})
}
