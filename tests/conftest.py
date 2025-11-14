"""Pytest configuration and fixtures."""
import pytest
import sys
from pathlib import Path

# Add src directory to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


@pytest.fixture
def temp_config():
    """Fixture providing a temporary configuration."""
    from src.core.config import MigrationConfig

    return MigrationConfig(
        source_org="test-source-org",
        source_repo="test-source-repo",
        target_org="test-target-org",
        target_repo="test-target-repo",
        source_pat="test-source-pat",
        target_pat="test-target-pat",
    )


@pytest.fixture
def temp_logger():
    """Fixture providing a temporary logger."""
    from src.utils.logger import Logger

    return Logger(verbose=False)
