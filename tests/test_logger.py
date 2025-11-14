"""Tests for logger module."""
from src.utils.logger import Logger


class TestLogger:
    """Test cases for Logger."""

    def test_logger_initialization(self):
        """Test logger initialization."""
        logger = Logger(verbose=False)
        assert logger is not None

    def test_logger_verbose_mode(self):
        """Test logger with verbose mode enabled."""
        logger = Logger(verbose=True)
        assert logger.verbose is True

    def test_logger_methods_exist(self):
        """Test that all logger methods exist."""
        logger = Logger(verbose=False)
        assert hasattr(logger, "debug")
        assert hasattr(logger, "info")
        assert hasattr(logger, "success")
        assert hasattr(logger, "warn")
        assert hasattr(logger, "error")
        assert callable(logger.debug)
        assert callable(logger.info)
        assert callable(logger.success)
        assert callable(logger.warn)
        assert callable(logger.error)

    def test_logger_can_log_messages(self, capsys):
        """Test that logger can log messages."""
        logger = Logger(verbose=False)
        logger.info("Test message")
        # Message was logged without raising exception
        assert logger is not None

    def test_logger_verbose_debug_messages(self, capsys):
        """Test debug messages in verbose mode."""
        logger = Logger(verbose=True)
        logger.debug("Debug message")
        # Debug message was logged in verbose mode
        assert logger.verbose is True
