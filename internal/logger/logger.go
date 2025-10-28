// Package logger provides logging utilities for the secrets migrator.
package logger

import (
	"fmt"
	"os"
)

// Logger handles all logging for the application.
type Logger struct {
	Verbose bool
}

// New creates a new logger instance.
func New(verbose bool) *Logger {
	return &Logger{
		Verbose: verbose,
	}
}

// Info logs an information message.
func (l *Logger) Info(message string) {
	fmt.Printf("[INFO] %s\n", message)
}

// Infof logs a formatted information message.
func (l *Logger) Infof(format string, args ...interface{}) {
	fmt.Printf("[INFO] "+format+"\n", args...)
}

// Success logs a success message.
func (l *Logger) Success(message string) {
	fmt.Printf("[SUCCESS] %s\n", message)
}

// Successf logs a formatted success message.
func (l *Logger) Successf(format string, args ...interface{}) {
	fmt.Printf("[SUCCESS] "+format+"\n", args...)
}

// Debug logs a message only if verbose mode is enabled.
func (l *Logger) Debug(message string) {
	if l.Verbose {
		fmt.Printf("[DEBUG] %s\n", message)
	}
}

// Debugf logs a formatted message only if verbose mode is enabled.
func (l *Logger) Debugf(format string, args ...interface{}) {
	if l.Verbose {
		fmt.Printf("[DEBUG] "+format+"\n", args...)
	}
}

// Error logs an error message and exits.
func (l *Logger) Error(err error) {
	fmt.Fprintf(os.Stderr, "[ERROR] %v\n", err)
	os.Exit(1)
}

// Errorf logs a formatted error message.
func (l *Logger) Errorf(format string, args ...interface{}) {
	fmt.Fprintf(os.Stderr, "[ERROR] "+format+"\n", args...)
}

// Fatal logs a fatal message and exits.
func (l *Logger) Fatal(message string) {
	fmt.Fprintf(os.Stderr, "[FATAL] %s\n", message)
	os.Exit(1)
}

// Fatalf logs a formatted fatal message and exits.
func (l *Logger) Fatalf(format string, args ...interface{}) {
	fmt.Fprintf(os.Stderr, "[FATAL] "+format+"\n", args...)
	os.Exit(1)
}
