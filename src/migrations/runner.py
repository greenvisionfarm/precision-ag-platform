"""
Миграции БД через playhouse.migrate.

Использование:
    python -m src.migrations.runner up       # применить все новые миграции
    python -m src.migrations.runner down     # откатить последнюю миграцию
    python -m src.migrations.runner status   # показать текущую версию
    python -m src.migrations.runner history  # список всех миграций
"""
import importlib
import logging
import os
import re
import sys
from glob import glob
from typing import List, Tuple

from peewee import SqliteDatabase
from playhouse.migrate import SchemaMigrator

logger = logging.getLogger(__name__)

MIGRATIONS_DIR = os.path.dirname(os.path.abspath(__file__))
VERSION_TABLE = 'schema_version'


def get_database() -> SqliteDatabase:
    """Возвращает текущую БД."""
    if os.environ.get('FIELD_MAPPER_ENV') == 'test':
        return SqliteDatabase('test_fields.db')
    db_path = os.getenv('FIELD_MAPPER_DB', 'fields.db')
    return SqliteDatabase(db_path)


def ensure_version_table(db: SqliteDatabase) -> None:
    """Создаёт таблицу версий если её нет."""
    db.execute_sql(f"""
        CREATE TABLE IF NOT EXISTS {VERSION_TABLE} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            version VARCHAR(50) UNIQUE NOT NULL,
            applied_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            name VARCHAR(255)
        )
    """)


def get_current_version(db: SqliteDatabase) -> str:
    """Возвращает текущую версию миграции."""
    ensure_version_table(db)
    cursor = db.execute_sql(
        f"SELECT version FROM {VERSION_TABLE} ORDER BY id DESC LIMIT 1"
    )
    row = cursor.fetchone()
    return row[0] if row else '000'


def get_applied_versions(db: SqliteDatabase) -> List[str]:
    """Возвращает список применённых версий."""
    ensure_version_table(db)
    cursor = db.execute_sql(
        f"SELECT version FROM {VERSION_TABLE} ORDER BY id"
    )
    return [row[0] for row in cursor.fetchall()]


def discover_migrations() -> List[Tuple[str, str]]:
    """Находит все файлы миграций и возвращает [(version, module_path), ...]."""
    pattern = os.path.join(MIGRATIONS_DIR, '[0-9]*.py')
    files = sorted(glob(pattern))
    result = []
    for f in files:
        name = os.path.basename(f).replace('.py', '')
        if re.match(r'^\d{3}_', name):
            version = name.split('_')[0]
            module_path = f'src.migrations.{name}'
            result.append((version, module_path))
    return result


def apply_migration(
    db: SqliteDatabase, version: str, module_path: str
) -> None:
    """Применяет одну миграцию."""
    logger.info(f"Применение миграции {version}...")
    ensure_version_table(db)
    mod = importlib.import_module(module_path)
    migrator = SchemaMigrator(db)
    mod.upgrade(migrator)

    db.execute_sql(
        f"INSERT INTO {VERSION_TABLE} (version, name) VALUES (?, ?)",
        (version, mod.__doc__ or version)
    )
    logger.info(f"Миграция {version} применена.")


def rollback_migration(
    db: SqliteDatabase, version: str, module_path: str
) -> None:
    """Откатывает одну миграцию."""
    logger.info(f"Откат миграции {version}...")
    mod = importlib.import_module(module_path)
    if not hasattr(mod, 'downgrade'):
        raise ValueError(f"Миграция {version} не поддерживает downgrade")

    migrator = SchemaMigrator(db)
    mod.downgrade(migrator)

    db.execute_sql(
        f"DELETE FROM {VERSION_TABLE} WHERE version = ?", (version,)
    )
    logger.info(f"Миграция {version} откачена.")


def run_up(db: SqliteDatabase) -> int:
    """Применяет все неприменённые миграции. Возвращает количество."""
    ensure_version_table(db)
    applied = set(get_applied_versions(db))
    all_migrations = discover_migrations()
    count = 0

    for version, module_path in all_migrations:
        if version not in applied:
            apply_migration(db, version, module_path)
            count += 1

    if count == 0:
        logger.info("Все миграции уже применены.")
    return count


def run_down(db: SqliteDatabase) -> None:
    """Откатывает последнюю миграцию."""
    ensure_version_table(db)
    applied = get_applied_versions(db)
    if not applied:
        logger.info("Нет миграций для отката.")
        return

    last_version = applied[-1]
    all_migrations = dict(discover_migrations())
    module_path = all_migrations.get(last_version)
    if not module_path:
        raise ValueError(f"Файл миграции {last_version} не найден")

    rollback_migration(db, last_version, module_path)


def run_status(db: SqliteDatabase) -> None:
    """Печатает текущую версию."""
    version = get_current_version(db)
    applied = get_applied_versions(db)
    total = len(discover_migrations())
    print(f"Текущая версия: {version}")
    print(f"Применено: {len(applied)}/{total}")


def run_history(db: SqliteDatabase) -> None:
    """Печатает историю миграций."""
    ensure_version_table(db)
    applied = set(get_applied_versions(db))
    all_migrations = discover_migrations()

    for version, module_path in all_migrations:
        status = "✅" if version in applied else "⏳"
        mod = importlib.import_module(module_path)
        name = mod.__doc__ or version
        print(f"  {status} {version} — {name}")


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(message)s')
    db = get_database()
    db.connect()

    command = sys.argv[1] if len(sys.argv) > 1 else 'status'

    if command == 'up':
        count = run_up(db)
        print(f"Применено миграций: {count}")
    elif command == 'down':
        run_down(db)
    elif command == 'status':
        run_status(db)
    elif command == 'history':
        run_history(db)
    else:
        print(f"Неизвестная команда: {command}")
        print("Использование: python -m src.migrations.runner [up|down|status|history]")

    db.close()
