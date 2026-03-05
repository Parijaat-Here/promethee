# tests/conftest.py
"""Fixtures partagées entre tous les modules de tests."""
import os
import sys
import pytest
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

os.environ.setdefault("QDRANT_URL", "http://localhost:6333")
os.environ.setdefault("QDRANT_COLLECTION", "test_collection")
os.environ.setdefault("EMBEDDING_MODE", "api")
os.environ.setdefault("EMBEDDING_MODEL", "test-model")
os.environ.setdefault("EMBEDDING_DIMENSION", "4")
os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("DB_ENCRYPTION", "OFF")


@pytest.fixture()
def tmp_db(tmp_path):
    return str(tmp_path / "test_history.db")


@pytest.fixture()
def skills_dir(tmp_path):
    d = tmp_path / "skills"
    d.mkdir()
    return d
