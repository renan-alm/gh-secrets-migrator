"""Core migration logic."""
# Re-export for backwards compatibility
from src.core.migrator import Migrator
from src.core.config import MigrationConfig
from src.core.workflow_generator import generate_workflow

__all__ = ['Migrator', 'MigrationConfig', 'generate_workflow']
