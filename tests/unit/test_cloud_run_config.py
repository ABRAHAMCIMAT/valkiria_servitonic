"""Ajustes de configuración para Cloud Run (Fase 2, I3/I4)."""

import importlib
import json


def _reload_config(monkeypatch, **env):
    for k in ("LOG_FILE", "TELEMETRY_LOG", "CONV_STORE", "AUDIT_LOG", "STRUCTURED_STDOUT", "K_SERVICE"):
        monkeypatch.delenv(k, raising=False)
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    import backend.config

    return importlib.reload(backend.config)


def test_cloud_run_disables_local_files_and_enables_stdout(monkeypatch):
    cfg = _reload_config(monkeypatch, K_SERVICE="snow-multiagent-api")
    try:
        assert cfg.ON_CLOUD_RUN and cfg.STRUCTURED_STDOUT
        assert cfg.LOG_FILE == cfg.TELEMETRY_LOG == cfg.AUDIT_LOG == cfg.CONV_STORE == ""
    finally:
        monkeypatch.delenv("K_SERVICE")
        importlib.reload(cfg)


def test_local_keeps_files_and_no_stdout(monkeypatch):
    cfg = _reload_config(monkeypatch)
    assert not cfg.ON_CLOUD_RUN and not cfg.STRUCTURED_STDOUT
    assert cfg.AUDIT_LOG.endswith("audit.jsonl")


def test_audit_and_telemetry_write_structured_stdout(monkeypatch, capsys):
    cfg = _reload_config(monkeypatch, STRUCTURED_STDOUT="true")
    try:
        from backend.observability.telemetry import Telemetry
        from backend.security.audit import AuditLog

        AuditLog(path="").record(action="approval.approved", actor="k1", target="a1")
        Telemetry(log_path="").emit({"type": "approval", "status": "approved"})
        lines = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
        audit = next(entry for entry in lines if entry.get("log_type") == "audit")
        telemetry = next(entry for entry in lines if entry.get("log_type") == "telemetry")
        assert audit["severity"] == "NOTICE" and audit["action"] == "approval.approved"
        assert telemetry["severity"] == "INFO" and telemetry["type"] == "approval"
    finally:
        monkeypatch.delenv("STRUCTURED_STDOUT")
        importlib.reload(cfg)


def test_json_log_lines_carry_cloud_logging_severity():
    import logging

    from backend.llmops.logging import JsonFormatter

    record = logging.LogRecord("x", logging.WARNING, __file__, 1, "hola", None, None)
    assert json.loads(JsonFormatter().format(record))["severity"] == "WARNING"
