"""
Модуль для работы с базой данных Field Mapper.
Определяет модели данных и функции инициализации БД.
"""
import os
from typing import List

from peewee import (
    CharField,
    FloatField,
    ForeignKeyField,
    Model,
    SqliteDatabase,
    TextField,
)

# Константы для путей к базе данных
DB_FILE = 'fields.db'
TEST_DB_FILE = 'test_fields.db'

# Выбор базы данных в зависимости от окружения
if os.environ.get('FIELD_MAPPER_ENV') == 'test':
    database = SqliteDatabase(TEST_DB_FILE)
elif os.environ.get('FIELD_MAPPER_DB'):
    # Используем путь из переменной окружения (для Docker)
    database = SqliteDatabase(os.environ.get('FIELD_MAPPER_DB'))
else:
    database = SqliteDatabase(DB_FILE)


class BaseModel(Model):
    """Базовая модель для всех моделей базы данных."""
    
    class Meta:
        database = database


class Owner(BaseModel):
    """Модель владельца поля."""
    
    name = CharField(unique=True)


class Field(BaseModel):
    """Модель сельскохозяйственного поля."""
    
    name = CharField(null=True)
    geometry_wkt = TextField()  # Храним как WKT (Well-Known Text)
    properties_json = TextField(null=True)  # Доп. свойства (площадь и т.д.)
    owner = ForeignKeyField(Owner, backref='fields', null=True)


class FieldZone(BaseModel):
    """Модель зоны поля (для дифференцированного внесения)."""

    field = ForeignKeyField(Field, backref='zones')
    name = CharField()
    geometry_wkt = TextField()
    min_value = FloatField(null=True)
    max_value = FloatField(null=True)
    avg_ndvi = FloatField(null=True)
    color = CharField()


def initialize_db() -> None:
    """Инициализирует базу данных, удаляя все существующие таблицы и создавая новые.

    WARNING: Эта функция удаляет ВСЕ данные из базы!
    Используйте только в тестовом окружении или при первом запуске.
    
    Raises:
        RuntimeError: Если вызвана в production окружении с существующей БД.
    """
    # Защита от случайного вызова в production
    if os.environ.get('FIELD_MAPPER_ENV') != 'test':
        # Проверяем, существует ли уже база данных
        if os.path.exists(DB_FILE):
            raise RuntimeError(
                "База данных уже существует! Вызов initialize_db() удалит все данные. "
                "Если вы хотите использовать существующую базу, не вызывайте эту функцию. "
                "Для тестового окружения установите FIELD_MAPPER_ENV=test"
            )

    if not database.is_closed():
        database.close()
    database.connect(reuse_if_open=True)
    # Удаляем и создаем заново, чтобы тесты были изолированы
    database.drop_tables([Field, Owner, FieldZone])
    database.create_tables([Field, Owner, FieldZone])
    database.close()


def ensure_db_exists() -> None:
    """Гарантирует существование базы данных, создавая таблицы если их нет.

    Безопасная функция для production — не удаляет существующие данные.
    """
    if not database.is_closed():
        database.close()
    database.connect(reuse_if_open=True)

    # Проверяем, существуют ли таблицы
    existing_tables: List[str] = database.get_tables()
    required_tables = ['field', 'owner', 'fieldzone']

    # Создаём только отсутствующие таблицы
    tables_to_create = []
    if 'field' not in existing_tables:
        tables_to_create.append(Field)
    if 'owner' not in existing_tables:
        tables_to_create.append(Owner)
    if 'fieldzone' not in existing_tables:
        tables_to_create.append(FieldZone)

    if tables_to_create:
        database.create_tables(tables_to_create)

    database.close()
