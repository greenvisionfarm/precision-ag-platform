"""Утилиты для работы с базой данных."""
import threading
from contextlib import contextmanager

from db import database

# Счётчик активных контекстов db_connection
_db_lock = threading.Lock()
_db_ref_count = 0


@contextmanager
def db_connection():
    """Контекстный менеджер для управления подключением к БД.

    Гарантирует подключение к БД и корректное закрытие соединения
    после выполнения операции, даже в случае исключения.

    Поддерживает вложенные вызовы — соединение закрывается только
    когда выходит последний (внешний) контекст.

    Использование:
        with db_connection():
            Field.select()
    """
    global _db_ref_count

    with _db_lock:
        if database.is_closed():
            database.connect()
        _db_ref_count += 1

    try:
        yield
    finally:
        with _db_lock:
            _db_ref_count -= 1
            if _db_ref_count == 0 and not database.is_closed():
                database.close()
