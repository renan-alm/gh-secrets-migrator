"""Logger module for consistent output formatting."""
import sys


class Logger:
    """Simple logger for CLI output."""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose

    def info(self, message: str) -> None:
        """Log info message."""
        print(f"ℹ️  {message}")

    def debug(self, message: str) -> None:
        """Log debug message (only if verbose)."""
        if self.verbose:
            print(f"🔍 {message}", file=sys.stderr)

    def success(self, message: str) -> None:
        """Log success message."""
        print(f"✅ {message}")

    def error(self, message: str) -> None:
        """Log error message."""
        print(f"❌ {message}", file=sys.stderr)

    def warn(self, message: str) -> None:
        """Log warning message."""
        print(f"⚠️  {message}", file=sys.stderr)
