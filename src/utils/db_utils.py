"""Утилиты для работы с базой данных."""
from contextlib import contextmanager

from db import database


@contextmanager
def db_connection():
    """Контекстный менеджер для управления подключением к БД.
    
    Гарантирует подключение к БД и корректное закрытие соединения
    после выполнения операции, даже в случае исключения.
    
    Использование:
        with db_connection():
            Field.select()
    """
    if database.is_closed():
        database.connect()
    try:
        yield
    finally:
        if not database.is_closed():
            database.close()
