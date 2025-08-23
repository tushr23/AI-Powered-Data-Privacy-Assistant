import os
import sys
import pytest

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


@pytest.fixture(autouse=True)
def isolate_db(tmp_path, monkeypatch):
    db_path = tmp_path / "test_db.sqlite"
    monkeypatch.setenv("DATABASE_NAME", str(db_path))
    yield
