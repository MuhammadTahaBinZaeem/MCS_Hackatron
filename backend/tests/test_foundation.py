import logging

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import text

from app.config import Settings
from app.database import create_database
from app.main import create_app
from app.providers import DisabledProviders, ProviderStatus
from app.safe_logging import get_logger
from app.secrets_store import ensure_local_secrets


def test_health_and_readiness(tmp_path):
    with TestClient(create_app(Settings(runtime_dir=tmp_path / "runtime"))) as client:
        assert client.get("/api/v1/healthz").json() == {"status": "ok"}
        assert client.get("/api/v1/readyz").json() == {"status": "ready"}
        client.app.state.engine.dispose()


def test_unavailable_database_returns_503(tmp_path):
    with TestClient(create_app(Settings(runtime_dir=tmp_path / "runtime"))) as client:
        client.app.state.engine.dispose()
        client.app.state.engine = create_database(tmp_path / "missing")
        client.app.state.engine.dispose()
        from unittest.mock import patch
        from sqlalchemy.exc import OperationalError
        with patch("app.main.database_ready", side_effect=OperationalError("", {}, Exception())):
            assert client.get("/api/v1/readyz").status_code == 503


def test_configuration_rejects_non_loopback_and_unsafe_paths(tmp_path):
    with pytest.raises(ValidationError):
        Settings(host="0.0.0.0", runtime_dir=tmp_path)
    with pytest.raises(ValidationError):
        Settings(runtime_dir=tmp_path.anchor)
    file = tmp_path / "file"
    file.write_text("x")
    with pytest.raises(ValidationError):
        Settings(runtime_dir=file)


def test_sqlite_pragmas_and_fk(tmp_path):
    engine = create_database(tmp_path)
    with engine.begin() as conn:
        assert conn.execute(text("PRAGMA foreign_keys")).scalar() == 1
        assert conn.execute(text("PRAGMA journal_mode")).scalar().lower() == "wal"
        assert conn.execute(text("PRAGMA busy_timeout")).scalar() == 5000
        conn.execute(text("CREATE TABLE parent (id INTEGER PRIMARY KEY)"))
        conn.execute(text("CREATE TABLE child (parent_id INTEGER REFERENCES parent(id))"))
        with pytest.raises(Exception):
            conn.execute(text("INSERT INTO child VALUES (123)"))
    engine.dispose()


def test_disabled_providers():
    provider = DisabledProviders()
    for result in [provider.classify("x"), provider.compare("x", []), provider.summarize({}), provider.analyze(b"x"), provider.save(b"x"), provider.read("x"), provider.delete("x"), provider.send("x", "x")]:
        assert result.status == ProviderStatus.NOT_CONFIGURED


def test_secrets_are_persistent_and_invalid_secrets_fail(tmp_path):
    ensure_local_secrets(tmp_path)
    path = tmp_path / "local-secrets.json"
    first = path.read_bytes()
    ensure_local_secrets(tmp_path)
    assert path.read_bytes() == first
    path.write_text("{}")
    with pytest.raises(ValueError):
        ensure_local_secrets(tmp_path)


def test_logging_redacts_secrets(monkeypatch, caplog):
    monkeypatch.setenv("REPORTFIX_API_KEY", "synthetic-secret-123")
    logger = get_logger("reportfix.test")
    with caplog.at_level(logging.INFO):
        logger.info("provider %s", "synthetic-secret-123")
    assert "synthetic-secret-123" not in caplog.text
    assert "[REDACTED]" in caplog.text
