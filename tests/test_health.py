"""
Tests for health check endpoint.
"""
import json
import pytest
from unittest.mock import patch, MagicMock


class TestHealthHandler:
    """Tests for GET /api/health."""

    def test_health_returns_200(self):
        """Health endpoint returns 200 when all checks pass."""
        from src.handlers.health_handler import HealthHandler

        handler = HealthHandler.__new__(HealthHandler)
        handler.set_status = MagicMock()
        handler.write = MagicMock()

        with patch.object(handler, '_check_db', return_value={"status": "ok"}), \
             patch.object(handler, '_check_redis', return_value={"status": "ok"}):
            handler.get()

            handler.set_status.assert_called_once_with(200)
            written = handler.write.call_args[0][0]
            assert written["status"] == "healthy"
            assert written["checks"]["db"]["status"] == "ok"
            assert written["checks"]["redis"]["status"] == "ok"
            assert "uptime_seconds" in written["checks"]["app"]

    def test_health_returns_503_on_db_failure(self):
        """Health endpoint returns 503 when DB check fails."""
        from src.handlers.health_handler import HealthHandler

        handler = HealthHandler.__new__(HealthHandler)
        handler.set_status = MagicMock()
        handler.write = MagicMock()

        with patch.object(handler, '_check_db', return_value={"status": "error", "message": "connection refused"}), \
             patch.object(handler, '_check_redis', return_value={"status": "ok"}):
            handler.get()

            handler.set_status.assert_called_once_with(503)
            written = handler.write.call_args[0][0]
            assert written["status"] == "degraded"

    def test_health_returns_503_on_redis_failure(self):
        """Health endpoint returns 503 when Redis check fails."""
        from src.handlers.health_handler import HealthHandler

        handler = HealthHandler.__new__(HealthHandler)
        handler.set_status = MagicMock()
        handler.write = MagicMock()

        with patch.object(handler, '_check_db', return_value={"status": "ok"}), \
             patch.object(handler, '_check_redis', return_value={"status": "error", "message": "timeout"}):
            handler.get()

            handler.set_status.assert_called_once_with(503)
            written = handler.write.call_args[0][0]
            assert written["status"] == "degraded"

    def test_check_db_ok(self):
        """_check_db returns ok when database responds."""
        from src.handlers.health_handler import HealthHandler

        handler = HealthHandler.__new__(HealthHandler)

        mock_db = MagicMock()
        mock_db.is_closed.return_value = False
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (1,)
        mock_db.execute_sql.return_value = mock_cursor

        with patch('src.handlers.health_handler.database', mock_db, create=True):
            with patch('db.database', mock_db):
                result = handler._check_db()
                assert result["status"] == "ok"

    def test_check_redis_ok(self):
        """_check_redis returns ok when Redis responds to ping."""
        from src.handlers.health_handler import HealthHandler

        handler = HealthHandler.__new__(HealthHandler)

        mock_redis_client = MagicMock()
        mock_redis_client.ping.return_value = True

        with patch('redis.from_url', return_value=mock_redis_client):
            result = handler._check_redis()
            assert result["status"] == "ok"

    def test_uptime_increases(self):
        """Uptime counter increases over time."""
        from src.handlers.health_handler import HealthHandler, _start_time
        import time

        handler = HealthHandler.__new__(HealthHandler)
        handler.set_status = MagicMock()
        handler.write = MagicMock()

        with patch.object(handler, '_check_db', return_value={"status": "ok"}), \
             patch.object(handler, '_check_redis', return_value={"status": "ok"}):
            handler.get()
            written1 = handler.write.call_args[0][0]
            uptime1 = written1["checks"]["app"]["uptime_seconds"]

            time.sleep(0.1)

            handler.write.reset_mock()
            handler.get()
            written2 = handler.write.call_args[0][0]
            uptime2 = written2["checks"]["app"]["uptime_seconds"]

            assert uptime2 > uptime1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
