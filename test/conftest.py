import os
import sys
import pytest


# Add project root to Python path so backend module can be imported
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


@pytest.fixture(autouse=True)
def isolate_db(tmp_path, monkeypatch):
    """Set DATABASE_NAME to a temp file before any app imports so tests use an isolated DB."""
    db_path = tmp_path / "test_db.sqlite"
    monkeypatch.setenv("DATABASE_NAME", str(db_path))
    # ensure any previously imported db module uses the new path
    # tests should import app after this fixture is applied
    yield
