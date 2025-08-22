import os
import pytest


@pytest.fixture(autouse=True)
def isolate_db(tmp_path, monkeypatch):
    """Set DATABASE_NAME to a temp file before any app imports so tests use an isolated DB."""
    db_path = tmp_path / "test_db.sqlite"
    monkeypatch.setenv("DATABASE_NAME", str(db_path))
    # ensure any previously imported db module uses the new path
    # tests should import app after this fixture is applied
    yield
