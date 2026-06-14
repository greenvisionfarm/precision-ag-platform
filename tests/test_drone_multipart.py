"""Тесты для drone upload multipart парсера."""
import io
import json
import os
import tempfile
import uuid
from unittest.mock import MagicMock, patch

import pytest


def make_multipart_body(fields: dict, filename: str, file_content: bytes, boundary: str = "----TestBoundary") -> bytes:
    """Генерирует multipart/form-data тело для тестов."""
    parts = []
    for name, value in fields.items():
        part = (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="{name}"\r\n'
            f"\r\n"
            f"{value}\r\n"
        )
        parts.append(part.encode())

    file_part = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="drone_images"; filename="{filename}"\r\n'
        f"Content-Type: application/zip\r\n"
        f"\r\n"
    ).encode() + file_content + b"\r\n"

    end = f"--{boundary}--\r\n".encode()

    return b"".join(parts) + file_part + end


class TestMultipartParsing:
    """Тесты парсинга multipart/form-data для drone upload."""

    def _write_and_parse(self, body: bytes, content_type: str):
        """Записывает body во временный файл и парсит через DroneUploadHandler."""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".upload") as tmp:
            tmp.write(body)
            tmp_path = tmp.name

        try:
            from src.handlers.drone_handlers import DroneUploadHandler
            handler = DroneUploadHandler.__new__(DroneUploadHandler)
            handler._upload_tmpfile = MagicMock()
            handler._upload_tmpfile.name = tmp_path
            handler._upload_tmpfile.close = MagicMock()
            handler.request = MagicMock()
            handler.request.headers = {"Content-Type": content_type}
            handler._upload_size = len(body)

            return handler._parse_multipart()
        finally:
            os.unlink(tmp_path)

    def test_basic_multipart_data_first(self):
        """data поле идёт первым, drone_images вторым."""
        file_content = b"FAKE_ZIP_CONTENT_" * 100
        data = {"field_id": "5", "crop_type": "wheat", "processing_mode": "fast"}
        boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"

        body = make_multipart_body(
            fields={"data": json.dumps(data)},
            filename="test_archive.zip",
            file_content=file_content,
            boundary=boundary
        )
        content_type = f"multipart/form-data; boundary={boundary}"

        uploaded_filename, form_data, drone_file_path = self._write_and_parse(body, content_type)

        assert uploaded_filename == "test_archive.zip"
        assert form_data["field_id"] == "5"
        assert form_data["crop_type"] == "wheat"
        assert drone_file_path is not None
        assert os.path.exists(drone_file_path)

        with open(drone_file_path, "rb") as f:
            saved_content = f.read()
        assert saved_content == file_content

        os.unlink(drone_file_path)

    def test_basic_multipart_file_first(self):
        """drone_images идёт первым, data вторым."""
        file_content = b"REAL_ZIP_DATA_" * 200
        data = {"field_id": "11", "processing_mode": "orthomosaic"}
        boundary = "----Boundary123"

        body = make_multipart_body(
            fields={"data": json.dumps(data)},
            filename="drone_flight.zip",
            file_content=file_content,
            boundary=boundary
        )
        content_type = f"multipart/form-data; boundary={boundary}"

        uploaded_filename, form_data, drone_file_path = self._write_and_parse(body, content_type)

        assert uploaded_filename == "drone_flight.zip"
        assert form_data["field_id"] == "11"
        assert form_data["processing_mode"] == "orthomosaic"

        with open(drone_file_path, "rb") as f:
            saved = f.read()
        assert saved == file_content

        os.unlink(drone_file_path)

    def test_large_file_content(self):
        """Большой файл (10MB)."""
        file_content = os.urandom(10 * 1024 * 1024)
        data = {"field_id": "1"}
        boundary = "----BigFileBoundary"

        body = make_multipart_body(
            fields={"data": json.dumps(data)},
            filename="big_drone.zip",
            file_content=file_content,
            boundary=boundary
        )
        content_type = f"multipart/form-data; boundary={boundary}"

        uploaded_filename, form_data, drone_file_path = self._write_and_parse(body, content_type)

        assert uploaded_filename == "big_drone.zip"
        assert form_data["field_id"] == "1"

        with open(drone_file_path, "rb") as f:
            saved = f.read()
        assert saved == file_content
        assert len(saved) == 10 * 1024 * 1024

        os.unlink(drone_file_path)

    def test_filename_with_special_chars(self):
        """Имя файла с пробелами и кириллицей."""
        file_content = b"SPECIAL_CHARS"
        boundary = "----Special"

        body = make_multipart_body(
            fields={"data": "{}"},
            filename="Дрон поле 2024.zip",
            file_content=file_content,
            boundary=boundary
        )
        content_type = f"multipart/form-data; boundary={boundary}"

        uploaded_filename, _, drone_file_path = self._write_and_parse(body, content_type)

        assert uploaded_filename == "Дрон поле 2024.zip"
        os.unlink(drone_file_path)

    def test_minimal_fields(self):
        """Минимальный набор полей — только data с пустым JSON."""
        file_content = b"MINIMAL"
        boundary = "----Min"

        body = make_multipart_body(
            fields={"data": "{}"},
            filename="min.zip",
            file_content=file_content,
            boundary=boundary
        )
        content_type = f"multipart/form-data; boundary={boundary}"

        _, form_data, drone_file_path = self._write_and_parse(body, content_type)

        assert form_data == {}
        os.unlink(drone_file_path)

    def test_binary_file_content_preserved(self):
        """Бинарное содержимое файла не повреждается."""
        file_content = bytes(range(256)) * 100
        boundary = "----Binary"

        body = make_multipart_body(
            fields={"data": "{}"},
            filename="binary.zip",
            file_content=file_content,
            boundary=boundary
        )
        content_type = f"multipart/form-data; boundary={boundary}"

        _, _, drone_file_path = self._write_and_parse(body, content_type)

        with open(drone_file_path, "rb") as f:
            saved = f.read()
        assert saved == file_content

        os.unlink(drone_file_path)
