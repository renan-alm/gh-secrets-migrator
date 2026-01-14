#!/usr/bin/env python3
"""GitHub Secrets Migrator - Migrate secrets from one repository to another."""

import warnings
from dotenv import load_dotenv

from src.cli import migrate

# Load environment variables from .env file
load_dotenv()

# Suppress urllib3 SSL warnings
warnings.filterwarnings("ignore", message="Unverified HTTPS request")
warnings.filterwarnings("ignore", module="urllib3")

if __name__ == "__main__":
    migrate()
