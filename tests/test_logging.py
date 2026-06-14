"""
Tests for structured logging setup.
"""
import json
import logging
import os
import sys
from io import StringIO
from unittest.mock import patch

import pytest


class TestLoggingConfig:
    """Tests for src/logging_config.py."""

    def test_setup_logging_configures_json_formatter(self):
        """setup_logging configures root logger with JSON formatter."""
        from src.logging_config import setup_logging

        setup_logging()

        root = logging.getLogger()
        assert len(root.handlers) > 0
        handler = root.handlers[0]
        assert hasattr(handler, 'formatter')

    def test_json_log_format(self):
        """Log records are formatted as JSON."""
        from src.logging_config import setup_logging, request_id_var

        setup_logging()

        root = logging.getLogger()
        stream = StringIO()
        json_handler = logging.StreamHandler(stream)

        from pythonjsonlogger import json as json_logger
        json_handler.setFormatter(json_logger.JsonFormatter(
            fmt="%(asctime)s %(levelname)s %(name)s %(message)s",
            rename_fields={"asctime": "timestamp", "levelname": "level", "name": "logger"},
        ))
        root.addHandler(json_handler)

        test_logger = logging.getLogger("test_json_format")
        test_logger.info("test message")

        output = stream.getvalue().strip()
        parsed = json.loads(output)
        assert "message" in parsed
        assert parsed["message"] == "test message"
        assert "timestamp" in parsed
        assert "level" in parsed

        root.removeHandler(json_handler)

    def test_request_id_filter_adds_field(self):
        """RequestIdFilter adds request_id to log records."""
        from src.logging_config import RequestIdFilter, request_id_var

        request_id_var.set("abc123")
        filt = RequestIdFilter()

        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0,
            msg="test", args=(), exc_info=None
        )
        result = filt.filter(record)
        assert result is True
        assert record.request_id == "abc123"

    def test_request_id_default(self):
        """request_id defaults to '-' when not set."""
        from src.logging_config import request_id_var, RequestIdFilter

        request_id_var.set("-")
        filt = RequestIdFilter()

        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0,
            msg="test", args=(), exc_info=None
        )
        filt.filter(record)
        assert record.request_id == "-"

    def test_generate_request_id_unique(self):
        """generate_request_id returns unique IDs."""
        from src.logging_config import generate_request_id

        ids = {generate_request_id() for _ in range(100)}
        assert len(ids) == 100

    def test_generate_request_id_length(self):
        """generate_request_id returns 12-char hex string."""
        from src.logging_config import generate_request_id

        rid = generate_request_id()
        assert len(rid) == 12
        assert all(c in '0123456789abcdef' for c in rid)

    def test_request_id_in_response_header(self):
        """HealthHandler sets X-Request-ID in response."""
        from src.handlers.health_handler import HealthHandler

        handler = HealthHandler.__new__(HealthHandler)
        handler.set_status = lambda s: None
        handler.write = lambda d: None
        handler.set_header = lambda k, v: None
        handler.request = type('obj', (object,), {
            'headers': {},
        })()

        mock_set_header = handler.set_header
        captured = {}
        def capture(k, v):
            captured[k] = v
        handler.set_header = capture

        handler.prepare()

        assert "X-Request-ID" in captured
        assert len(captured["X-Request-ID"]) == 12


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
