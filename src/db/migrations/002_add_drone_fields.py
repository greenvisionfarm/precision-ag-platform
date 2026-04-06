"""
Миграция: Добавление полей для обработки снимков с дрона.

Поля в таблице fieldscan:
- source: источник данных (satellite, drone, file)
- crop_type: тип культуры
- crop_confidence: уверенность классификации
"""
import logging
from peewee import SqliteDatabase, CharField, FloatField, DoesNotExist

logger = logging.getLogger(__name__)


def migrate(db: SqliteDatabase) -> None:
    """Выполняет миграцию."""
    logger.info("Миграция: Добавление полей обработки снимков с дрона...")
    
    with db.atomic():
        # Проверяем существование таблицы fieldscan
        try:
            db.execute_sql("SELECT 1 FROM fieldscan LIMIT 1")
        except Exception:
            logger.warning("Таблица fieldscan не существует, пропускаем миграцию")
            return
        
        # Добавляем поле source
        try:
            db.execute_sql("""
                ALTER TABLE fieldscan ADD COLUMN source VARCHAR DEFAULT 'satellite'
            """)
            logger.info("Добавлено поле: source")
        except Exception as e:
            if "duplicate column" in str(e).lower():
                logger.info("Поле source уже существует")
            else:
                logger.warning(f"Не удалось добавить поле source: {e}")
        
        # Добавляем поле crop_type
        try:
            db.execute_sql("""
                ALTER TABLE fieldscan ADD COLUMN crop_type VARCHAR
            """)
            logger.info("Добавлено поле: crop_type")
        except Exception as e:
            if "duplicate column" in str(e).lower():
                logger.info("Поле crop_type уже существует")
            else:
                logger.warning(f"Не удалось добавить поле crop_type: {e}")
        
        # Добавляем поле crop_confidence
        try:
            db.execute_sql("""
                ALTER TABLE fieldscan ADD COLUMN crop_confidence FLOAT
            """)
            logger.info("Добавлено поле: crop_confidence")
        except Exception as e:
            if "duplicate column" in str(e).lower():
                logger.info("Поле crop_confidence уже существует")
            else:
                logger.warning(f"Не удалось добавить поле crop_confidence: {e}")
    
    logger.info("Миграция завершена")


if __name__ == "__main__":
    import os
    import sys
    
    # Добавляем корень проекта в path
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    
    from db import database
    
    migrate(database)
    print("Миграция выполнена успешно")
