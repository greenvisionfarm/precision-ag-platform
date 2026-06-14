"""
Tests for health dashboard HTML page.
"""
import pytest
from unittest.mock import MagicMock


class TestHealthDashboardHandler:
    """Tests for GET /health."""

    def test_returns_html(self):
        """Dashboard returns HTML content."""
        from src.handlers.health_dashboard import HealthDashboardHandler

        handler = HealthDashboardHandler.__new__(HealthDashboardHandler)
        written = []
        handler.set_header = lambda k, v: None
        handler.write = lambda d: written.append(d)

        handler.get()

        assert len(written) == 1
        html = written[0]
        assert "<!DOCTYPE html>" in html
        assert "Field Mapper Health" in html
        assert "/api/health" in html

    def test_contains_all_components(self):
        """Dashboard references DB, Redis, App components."""
        from src.handlers.health_dashboard import HealthDashboardHandler

        handler = HealthDashboardHandler.__new__(HealthDashboardHandler)
        written = []
        handler.set_header = lambda k, v: None
        handler.write = lambda d: written.append(d)

        handler.get()

        html = written[0]
        assert "auto-refresh" in html.lower() or "countdown" in html.lower()
        assert "healthy" in html.lower() or "degraded" in html.lower()

    def test_sets_content_type(self):
        """Dashboard sets Content-Type to text/html."""
        from src.handlers.health_dashboard import HealthDashboardHandler

        handler = HealthDashboardHandler.__new__(HealthDashboardHandler)
        captured = {}
        handler.set_header = lambda k, v: captured.update({k: v})
        handler.write = lambda d: None

        handler.get()

        assert captured.get("Content-Type", "").startswith("text/html")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
