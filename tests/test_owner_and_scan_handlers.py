"""
Тесты для owner_handlers (color CRUD), ScanDateUpdateHandler, ScanMergeHandler.
"""
import json
import pytest
from datetime import datetime

from db import Field
from src.models.field import Owner, FieldScan


class TestOwnerColorHandlers:
    """Тесты CRUD операций с цветом владельца."""

    def test_get_owners_includes_color(self, test_db, test_company, auth_cookies):
        owner = Owner.create(name="Цветной", company=test_company, color="#ff0000")
        resp = auth_cookies

        from tornado.testing import AsyncHTTPTestCase
        from app import make_app
        import os, socket

        with socket.socket() as s:
            s.bind(("127.0.0.1", 0))
            port = s.getsockname()[1]

        app = make_app()
        server = app.listen(port)
        try:
            import tornado.ioloop
            from tornado.httpclient import HTTPClient

            client = HTTPClient()
            r = client.fetch(
                f"http://127.0.0.1:{port}/api/owners",
                headers=auth_cookies,
            )
            data = json.loads(r.body)
            assert "data" in data
            owners = data["data"]
            assert any(o["name"] == "Цветной" and o["color"] == "#ff0000" for o in owners)
            client.close()
        finally:
            server.stop()

    def test_create_owner_with_color(self, test_db, test_company, auth_cookies):
        from tornado.httpclient import HTTPClient
        import socket

        with socket.socket() as s:
            s.bind(("127.0.0.1", 0))
            port = s.getsockname()[1]

        app = __import__("app", fromlist=["make_app"]).make_app()
        server = app.listen(port)
        try:
            client = HTTPClient()
            body = json.dumps({"name": "Зелёный", "color": "#00ff00"})
            r = client.fetch(
                f"http://127.0.0.1:{port}/api/owners",
                method="POST",
                body=body,
                headers={**auth_cookies, "Content-Type": "application/json"},
            )
            assert r.code == 200

            r2 = client.fetch(
                f"http://127.0.0.1:{port}/api/owners",
                headers=auth_cookies,
            )
            data = json.loads(r2.body)
            assert any(o["name"] == "Зелёный" and o["color"] == "#00ff00" for o in data["data"])
            client.close()
        finally:
            server.stop()

    def test_update_owner_color(self, test_db, test_company, auth_cookies):
        owner = Owner.create(name="Обновляемый", company=test_company, color="#000000")

        from tornado.httpclient import HTTPClient
        import socket

        with socket.socket() as s:
            s.bind(("127.0.0.1", 0))
            port = s.getsockname()[1]

        app = __import__("app", fromlist=["make_app"]).make_app()
        server = app.listen(port)
        try:
            client = HTTPClient()
            body = json.dumps({"color": "#aabbcc"})
            r = client.fetch(
                f"http://127.0.0.1:{port}/api/owner/update/{owner.id}",
                method="PUT",
                body=body,
                headers={**auth_cookies, "Content-Type": "application/json"},
            )
            assert r.code == 200

            owner_db = Owner.get_by_id(owner.id)
            assert owner_db.color == "#aabbcc"
            client.close()
        finally:
            server.stop()

    def test_update_owner_name(self, test_db, test_company, auth_cookies):
        owner = Owner.create(name="Старое имя", company=test_company)

        from tornado.httpclient import HTTPClient
        import socket

        with socket.socket() as s:
            s.bind(("127.0.0.1", 0))
            port = s.getsockname()[1]

        app = __import__("app", fromlist=["make_app"]).make_app()
        server = app.listen(port)
        try:
            client = HTTPClient()
            body = json.dumps({"name": "Новое имя"})
            r = client.fetch(
                f"http://127.0.0.1:{port}/api/owner/update/{owner.id}",
                method="PUT",
                body=body,
                headers={**auth_cookies, "Content-Type": "application/json"},
            )
            assert r.code == 200

            owner_db = Owner.get_by_id(owner.id)
            assert owner_db.name == "Новое имя"
            client.close()
        finally:
            server.stop()

    def test_update_owner_not_found(self, test_db, test_company, auth_cookies):
        from tornado.httpclient import HTTPClient
        import socket

        with socket.socket() as s:
            s.bind(("127.0.0.1", 0))
            port = s.getsockname()[1]

        app = __import__("app", fromlist=["make_app"]).make_app()
        server = app.listen(port)
        try:
            client = HTTPClient()
            body = json.dumps({"color": "#ffffff"})
            r = client.fetch(
                f"http://127.0.0.1:{port}/api/owner/update/99999",
                method="PUT",
                body=body,
                headers={**auth_cookies, "Content-Type": "application/json"},
                raise_error=False,
            )
            assert r.code == 404
            client.close()
        finally:
            server.stop()


class TestScanDateUpdateHandler:
    """Тесты обновления даты съёмки скана."""

    def test_update_scan_date(self, test_db, test_company, test_user, auth_cookies):
        field = Field.create(
            name="Test Field",
            geometry_wkt="POLYGON ((0 0, 1 0, 1 1, 0 1, 0 0))",
            company_id=test_company.id,
        )
        scan = FieldScan.create(
            field=field,
            source="drone_fast",
            uploaded_at=datetime(2026, 1, 1),
        )

        from tornado.httpclient import HTTPClient
        import socket

        with socket.socket() as s:
            s.bind(("127.0.0.1", 0))
            port = s.getsockname()[1]

        app = __import__("app", fromlist=["make_app"]).make_app()
        server = app.listen(port)
        try:
            client = HTTPClient()
            body = json.dumps({"flight_date": "2026-06-15T10:30:00"})
            r = client.fetch(
                f"http://127.0.0.1:{port}/api/scans/{scan.id}/date",
                method="POST",
                body=body,
                headers={**auth_cookies, "Content-Type": "application/json"},
            )
            data = json.loads(r.body)
            assert data["success"] is True
            assert "2026-06-15" in data["uploaded_at"]
            client.close()
        finally:
            server.stop()

    def test_update_scan_date_missing_field(self, test_db, test_company, auth_cookies):
        from tornado.httpclient import HTTPClient
        import socket

        with socket.socket() as s:
            s.bind(("127.0.0.1", 0))
            port = s.getsockname()[1]

        app = __import__("app", fromlist=["make_app"]).make_app()
        server = app.listen(port)
        try:
            client = HTTPClient()
            body = json.dumps({})
            r = client.fetch(
                f"http://127.0.0.1:{port}/api/scans/1/date",
                method="POST",
                body=body,
                headers={**auth_cookies, "Content-Type": "application/json"},
                raise_error=False,
            )
            assert r.code == 400
            client.close()
        finally:
            server.stop()

    def test_update_scan_date_invalid_format(self, test_db, test_company, auth_cookies):
        from tornado.httpclient import HTTPClient
        import socket

        with socket.socket() as s:
            s.bind(("127.0.0.1", 0))
            port = s.getsockname()[1]

        app = __import__("app", fromlist=["make_app"]).make_app()
        server = app.listen(port)
        try:
            client = HTTPClient()
            body = json.dumps({"flight_date": "not-a-date"})
            r = client.fetch(
                f"http://127.0.0.1:{port}/api/scans/1/date",
                method="POST",
                body=body,
                headers={**auth_cookies, "Content-Type": "application/json"},
                raise_error=False,
            )
            assert r.code == 400
            client.close()
        finally:
            server.stop()

    def test_update_scan_date_not_found(self, test_db, test_company, auth_cookies):
        from tornado.httpclient import HTTPClient
        import socket

        with socket.socket() as s:
            s.bind(("127.0.0.1", 0))
            port = s.getsockname()[1]

        app = __import__("app", fromlist=["make_app"]).make_app()
        server = app.listen(port)
        try:
            client = HTTPClient()
            body = json.dumps({"flight_date": "2026-06-15T10:00:00"})
            r = client.fetch(
                f"http://127.0.0.1:{port}/api/scans/99999/date",
                method="POST",
                body=body,
                headers={**auth_cookies, "Content-Type": "application/json"},
                raise_error=False,
            )
            assert r.code == 404
            client.close()
        finally:
            server.stop()
