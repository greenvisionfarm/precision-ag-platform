"""
Structured logging setup — JSON format + correlation ID.
"""
import logging
import os
import uuid
from contextvars import ContextVar

from pythonjsonlogger import json as json_logger

request_id_var: ContextVar[str] = ContextVar("request_id", default="-")


class RequestIdFilter(logging.Filter):
    """Добавляет request_id в каждый log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get("-")
        return True


def setup_logging() -> None:
    """Настраивает JSON-логирование для всего приложения."""
    env = os.getenv("FIELD_MAPPER_ENV", "development")
    level = logging.DEBUG if env == "test" else logging.INFO

    root = logging.getLogger()
    root.setLevel(level)

    for handler in root.handlers[:]:
        root.removeHandler(handler)

    formatter = json_logger.JsonFormatter(
        fmt="%(asctime)s %(levelname)s %(name)s %(message)s",
        rename_fields={
            "asctime": "timestamp",
            "levelname": "level",
            "name": "logger",
        },
        datefmt="%Y-%m-%dT%H:%M:%S",
    )

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    stream_handler.addFilter(RequestIdFilter())
    root.addHandler(stream_handler)


def generate_request_id() -> str:
    """Генерирует уникальный ID для запроса."""
    return uuid.uuid4().hex[:12]
