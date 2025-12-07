"""Pytest configuration and shared fixtures."""

import os
import sys
import json
import logging
from pathlib import Path

import pytest

# Add src to Python path
project_root = Path(__file__).parent.parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

# Configure logging for tests
# Set DEBUG_TESTS=1 to see detailed API responses
log_level = logging.DEBUG if os.getenv("DEBUG_TESTS") else logging.INFO
logging.basicConfig(
    level=log_level,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

# Get logger for this module
logger = logging.getLogger(__name__)


@pytest.fixture
def mock_credentials_path(tmp_path):
    """Create a fake credentials file path."""
    return str(tmp_path / "fake_credentials.json")


@pytest.fixture
def mock_token_path(tmp_path):
    """Create a fake token file path."""
    return str(tmp_path / "fake_token.json")


@pytest.fixture(autouse=True)
def log_test_info(request):
    """Log test information for debugging."""
    if os.getenv("DEBUG_TESTS"):
        logger.debug(f"Running test: {request.node.name}")
    yield

