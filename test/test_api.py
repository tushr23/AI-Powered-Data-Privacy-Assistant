"""
Comprehensive API tests for the AI-Powered Data Privacy Assistant.
Tests all FastAPI endpoints, edge cases, and error handling scenarios.
"""
import pytest
from fastapi.testclient import TestClient
import os
import tempfile
import importlib
import sys
import runpy
from types import ModuleType
from starlette.requests import Request as StarletteRequest


def _get_client():
    """Create a TestClient with isolated database for testing."""
    # Ensure DATABASE_NAME is set before importing backend so DB module picks it up
    if not os.environ.get("DATABASE_NAME"):
        fd, tmp_path = tempfile.mkstemp(prefix="test_db_", suffix=".sqlite")
        os.close(fd)
        os.unlink(tmp_path)  # remove file; sqlite will create it
        os.environ["DATABASE_NAME"] = tmp_path

    # If backend.db was previously imported with a different DB_NAME, reload it so it reads the new env var
    if "backend.db" in sys.modules:
        importlib.reload(sys.modules["backend.db"])
    # ensure the table exists for this test DB
    import backend.db as _dbmod
    _dbmod.create_table()

    from backend.main import app
    return TestClient(app)


# Basic endpoint tests
def test_scan_detects_email_and_phone():
    """Test /scan endpoint with basic PII detection (realistic example)."""
    client = _get_client()
    response = client.post("/scan", data={"text": "My email is test@example.com and my phone is 123-456-7890."})
    assert response.status_code == 200
    assert "findings" in response.json()
    assert "risk_score" in response.json()
    assert any(f["type"] == "email" for f in response.json()["findings"])
    assert any(f["type"] == "phone" for f in response.json()["findings"])


def test_redact_endpoint():
    """Test /redact endpoint with PII redaction."""
    client = _get_client()
    response = client.post("/redact", data={"text": "My email is test@example.com"})
    assert response.status_code == 200
    assert "redacted_text" in response.json()
    assert "[REDACTED]" in response.json()["redacted_text"]


def test_upload_endpoint(tmp_path):
    """Test /upload endpoint with file upload."""
    client = _get_client()
    file_path = tmp_path / "test.txt"
    file_path.write_text("My ssn is 123-45-6789.")

    with open(file_path, "rb") as f:
        response = client.post("/upload", files={"file": f})
    assert response.status_code == 200
    assert "message" in response.json()
    assert any(f["type"] == "ssn" for f in response.json()["findings"])


def test_logs_endpoint():
    """Test /logs endpoint to retrieve audit logs."""
    client = _get_client()
    response = client.get("/logs")
    assert response.status_code == 200
    assert "logs" in response.json()
    assert isinstance(response.json()["logs"], list)


# Edge case tests
def test_scan_empty_text():
    """Test /scan with empty text."""
    client = _get_client()
    response = client.post("/scan", json={"text": ""})
    assert response.status_code == 200
    assert "findings" in response.json()


def test_redact_empty_text():
    """Test /redact with empty text."""
    client = _get_client()
    response = client.post("/redact", json={"text": ""})
    assert response.status_code == 200
    assert "redacted_text" in response.json()


def test_upload_non_utf8_file():
    """Test /upload with non-UTF8 binary file."""
    client = _get_client()
    data = b"\xff\xfe\x00\x00\xff"
    files = {"file": ("blob.bin", data)}
    response = client.post("/upload", files=files)
    assert response.status_code == 200
    assert "findings" in response.json()


def test_json_non_dict_handling(tmp_path, monkeypatch):
    """Test endpoints handle JSON that's not a dict."""
    monkeypatch.setenv('DATABASE_NAME', str(tmp_path / 'test_json.sqlite'))
    if 'backend.db' in sys.modules:
        importlib.reload(sys.modules['backend.db'])
    import backend.db as _db
    _db.create_table()

    from backend.main import app
    client = TestClient(app)
    
    # JSON list -> payload not a dict branch
    response = client.post('/scan', json=[1, 2, 3])
    assert response.status_code == 200

    # JSON empty dict -> payload is dict but no text key -> text becomes '' branch
    response = client.post('/scan', json={})
    assert response.status_code == 200


def test_form_and_invalid_json_fallback(monkeypatch, tmp_path):
    """Test form-encoded requests and invalid JSON fallback."""
    db_file = tmp_path / "test_form.sqlite"
    monkeypatch.setenv("DATABASE_NAME", str(db_file))
    if 'backend.db' in sys.modules:
        importlib.reload(sys.modules['backend.db'])
    import backend.db as _db
    _db.create_table()

    from backend.main import app
    client = TestClient(app)

    # Form-encoded posting
    response = client.post('/scan', data={'text': 'Contact: bob@example.com'})
    assert response.status_code == 200

    # Invalid JSON should be caught and fallback to form attempt
    response = client.post('/scan', content='not-json', headers={'Content-Type': 'application/json'})
    assert response.status_code == 200

    # Same for /redact endpoint
    response = client.post('/redact', content='not-json', headers={'Content-Type': 'application/json'})
    assert response.status_code == 200


def test_request_exception_handling(monkeypatch, tmp_path):
    """Test exception handling when both JSON and form parsing fail."""
    def raise_json(self):
        raise RuntimeError('json fail')

    def raise_form(self):
        raise RuntimeError('form fail')

    monkeypatch.setattr(StarletteRequest, 'json', raise_json, raising=False)
    monkeypatch.setattr(StarletteRequest, 'form', raise_form, raising=False)

    monkeypatch.setenv('DATABASE_NAME', str(tmp_path / 'test_exception.sqlite'))
    if 'backend.db' in sys.modules:
        importlib.reload(sys.modules['backend.db'])
    import backend.db as _db
    _db.create_table()

    from fastapi.testclient import TestClient
    from backend.main import app
    client = TestClient(app)

    # Test both endpoints handle exceptions gracefully
    response = client.post('/scan', json={'text': 'ignored due to exception'})
    assert response.status_code == 200

    response = client.post('/redact', json={'text': 'ignored due to exception'})
    assert response.status_code == 200


def test_startup_event_coverage(monkeypatch, tmp_path):
    """Test that FastAPI startup events are executed."""
    monkeypatch.setenv('DATABASE_NAME', str(tmp_path / 'startup.sqlite'))
    if 'backend.db' in sys.modules:
        importlib.reload(sys.modules['backend.db'])
    
    from fastapi.testclient import TestClient
    from backend.main import app
    
    # Using TestClient context ensures startup/shutdown events are executed
    with TestClient(app) as client:
        response = client.get('/logs')
        assert response.status_code == 200


def test_main_module_execution(monkeypatch, tmp_path):
    """Test running backend.main as __main__ module."""
    monkeypatch.setenv("DATABASE_NAME", str(tmp_path / "test_main_exec.sqlite"))

    called = {}
    def fake_uvicorn_run(app, host, port, reload=False):
        called['host'] = host
        called['port'] = port

    monkeypatch.setattr('uvicorn.run', fake_uvicorn_run)
    
    # Run module as __main__ to hit the uvicorn.run(...) block
    runpy.run_module('backend.main', run_name='__main__')
    
    assert called.get('host') == '0.0.0.0'
    assert called.get('port') == 8000

