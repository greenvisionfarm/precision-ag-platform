"""
Tests for playhouse.migrate migration system.
"""
import os
import pytest
from unittest.mock import patch, MagicMock
from peewee import SqliteDatabase


@pytest.fixture
def test_db():
    """Создаёт тестовую БД и очищает после теста."""
    db = SqliteDatabase(':memory:')
    db.connect()
    yield db
    db.close()


class TestMigrationRunner:
    """Tests for src/migrations/runner.py."""

    def test_ensure_version_table(self, test_db):
        """ensure_version_table создаёт таблицу версий."""
        from src.migrations.runner import ensure_version_table, VERSION_TABLE

        ensure_version_table(test_db)
        cursor = test_db.execute_sql(
            f"SELECT name FROM sqlite_master WHERE type='table' AND name='{VERSION_TABLE}'"
        )
        assert cursor.fetchone() is not None

    def test_get_current_version_empty(self, test_db):
        """get_current_version возвращает '000' если нет миграций."""
        from src.migrations.runner import get_current_version

        version = get_current_version(test_db)
        assert version == '000'

    def test_get_current_version_after_apply(self, test_db):
        """get_current_version возвращает последнюю применённую версию."""
        from src.migrations.runner import (
            ensure_version_table, get_current_version, VERSION_TABLE
        )

        ensure_version_table(test_db)
        test_db.execute_sql(
            f"INSERT INTO {VERSION_TABLE} (version, name) VALUES (?, ?)",
            ('001', 'test')
        )
        test_db.execute_sql(
            f"INSERT INTO {VERSION_TABLE} (version, name) VALUES (?, ?)",
            ('003', 'test')
        )

        version = get_current_version(test_db)
        assert version == '003'

    def test_get_applied_versions(self, test_db):
        """get_applied_versions возвращает список применённых версий."""
        from src.migrations.runner import (
            ensure_version_table, get_applied_versions, VERSION_TABLE
        )

        ensure_version_table(test_db)
        for v in ['001', '002', '003']:
            test_db.execute_sql(
                f"INSERT INTO {VERSION_TABLE} (version, name) VALUES (?, ?)",
                (v, f'migration {v}')
            )

        versions = get_applied_versions(test_db)
        assert versions == ['001', '002', '003']

    def test_discover_migrations(self):
        """discover_migrations находит файлы миграций."""
        from src.migrations.runner import discover_migrations

        migrations = discover_migrations()
        assert len(migrations) >= 1
        assert migrations[0][0] == '001'

    def test_apply_migration(self, test_db):
        """apply_migration применяет миграцию и записывает версию."""
        from src.migrations.runner import apply_migration

        apply_migration(test_db, '001', 'src.migrations.001_initial')

        cursor = test_db.execute_sql(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
        tables = {row[0] for row in cursor.fetchall()}
        assert 'company' in tables
        assert 'user' in tables
        assert 'field' in tables

    def test_run_up(self, test_db):
        """run_up применяет все неприменённые миграции."""
        from src.migrations.runner import run_up

        count = run_up(test_db)
        assert count >= 1

        cursor = test_db.execute_sql(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
        tables = {row[0] for row in cursor.fetchall()}
        assert 'schema_version' in tables

    def test_run_up_idempotent(self, test_db):
        """run_up не применяет миграции повторно."""
        from src.migrations.runner import run_up

        run_up(test_db)
        count第二次 = run_up(test_db)
        assert count第二次 == 0

    def test_run_down(self, test_db):
        """run_down откатывает последнюю миграцию."""
        from src.migrations.runner import run_up, run_down, get_current_version

        run_up(test_db)
        assert get_current_version(test_db) == '001'

        run_down(test_db)
        assert get_current_version(test_db) == '000'

    def test_run_history(self, test_db, capsys):
        """run_history печатает список миграций."""
        from src.migrations.runner import run_history

        run_history(test_db)
        captured = capsys.readouterr()
        assert '001' in captured.out


class TestMigrationSchema:
    """Tests that the initial migration creates correct schema."""

    def test_company_table(self, test_db):
        """001_initial creates company table with correct columns."""
        from src.migrations.runner import run_up

        run_up(test_db)
        cursor = test_db.execute_sql("PRAGMA table_info(company)")
        columns = {row[1] for row in cursor.fetchall()}
        assert 'id' in columns
        assert 'name' in columns
        assert 'slug' in columns
        assert 'is_active' in columns

    def test_user_table(self, test_db):
        """001_initial creates user table."""
        from src.migrations.runner import run_up

        run_up(test_db)
        cursor = test_db.execute_sql("PRAGMA table_info(user)")
        columns = {row[1] for row in cursor.fetchall()}
        assert 'email' in columns
        assert 'password_hash' in columns
        assert 'company_id' in columns
        assert 'role' in columns

    def test_field_table(self, test_db):
        """001_initial creates field table."""
        from src.migrations.runner import run_up

        run_up(test_db)
        cursor = test_db.execute_sql("PRAGMA table_info(field)")
        columns = {row[1] for row in cursor.fetchall()}
        assert 'geometry_wkt' in columns
        assert 'company_id' in columns

    def test_fieldzone_table(self, test_db):
        """001_initial creates fieldzone table."""
        from src.migrations.runner import run_up

        run_up(test_db)
        cursor = test_db.execute_sql("PRAGMA table_info(fieldzone)")
        columns = {row[1] for row in cursor.fetchall()}
        assert 'rate_kg_ha' in columns
        assert 'scan_id' in columns

    def test_all_seven_tables(self, test_db):
        """001_initial creates all 7 tables."""
        from src.migrations.runner import run_up

        run_up(test_db)
        cursor = test_db.execute_sql(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        tables = {row[0] for row in cursor.fetchall()}
        expected = {'company', 'user', 'owner', 'field', 'fieldscan', 'fieldzone', 'fieldjournal', 'schema_version'}
        assert expected.issubset(tables)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
