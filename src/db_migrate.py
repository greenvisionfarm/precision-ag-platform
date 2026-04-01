"""
Скрипт миграции базы данных для добавления мульти-тенантности.
Создаёт таблицы Company и User, обновляет существующие таблицы.
"""
import logging
from datetime import datetime

from peewee import SqliteDatabase

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def migrate_db(db_path: str = 'fields.db') -> None:
    """
    Выполняет миграцию базы данных.
    
    Args:
        db_path: Путь к файлу базы данных
    """
    database = SqliteDatabase(db_path)
    database.connect()
    
    cursor = database.cursor()
    
    try:
        # 1. Создаём таблицу company
        logger.info("Создание таблицы company...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS company (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR(255) UNIQUE NOT NULL,
                slug VARCHAR(255) UNIQUE NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                is_active INTEGER DEFAULT 1,
                settings_json TEXT
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_company_slug ON company(slug)")
        
        # 2. Создаём таблицу user
        logger.info("Создание таблицы user...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email VARCHAR(255) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                password_salt VARCHAR(255) NOT NULL,
                first_name VARCHAR(255),
                last_name VARCHAR(255),
                company_id INTEGER NOT NULL,
                role VARCHAR(50) DEFAULT 'operator',
                is_active INTEGER DEFAULT 1,
                is_verified INTEGER DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                last_login DATETIME,
                language VARCHAR(10) DEFAULT 'ru',
                settings_json TEXT,
                FOREIGN KEY (company_id) REFERENCES company(id) ON DELETE CASCADE
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_email ON user(email)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_company ON user(company_id)")
        
        # 3. Добавляем company_id в таблицу owner
        logger.info("Обновление таблицы owner...")
        cursor.execute("PRAGMA table_info(owner)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if columns:  # Таблица существует
            if 'company_id' not in columns:
                cursor.execute("""
                    ALTER TABLE owner ADD COLUMN company_id INTEGER
                    REFERENCES company(id) ON DELETE CASCADE
                """)
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_owner_company ON owner(company_id)")
        else:
            # Таблицы нет, создаём её с company_id
            cursor.execute("""
                CREATE TABLE owner (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name VARCHAR(255) UNIQUE NOT NULL,
                    company_id INTEGER,
                    FOREIGN KEY (company_id) REFERENCES company(id) ON DELETE CASCADE
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_owner_company ON owner(company_id)")
        
        # 4. Добавляем company_id в таблицу field
        logger.info("Обновление таблицы field...")
        cursor.execute("PRAGMA table_info(field)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if columns:  # Таблица существует
            if 'company_id' not in columns:
                # Сначала добавляем колонку
                cursor.execute("""
                    ALTER TABLE field ADD COLUMN company_id INTEGER
                    REFERENCES company(id) ON DELETE CASCADE
                """)
                
                # Если есть компания по умолчанию, устанавливаем её
                cursor.execute("SELECT id FROM company LIMIT 1")
                default_company = cursor.fetchone()
                if default_company:
                    cursor.execute(f"""
                        UPDATE field SET company_id = {default_company[0]} WHERE company_id IS NULL
                    """)
                
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_field_company ON field(company_id)")
            
            # Добавляем updated_at в field
            if 'updated_at' not in columns:
                cursor.execute("""
                    ALTER TABLE field ADD COLUMN updated_at DATETIME
                """)
        else:
            # Таблицы нет, создаём её со всеми колонками
            cursor.execute("""
                CREATE TABLE field (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name VARCHAR(255),
                    geometry_wkt TEXT NOT NULL,
                    properties_json TEXT,
                    owner_id INTEGER,
                    company_id INTEGER NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME,
                    FOREIGN KEY (owner_id) REFERENCES owner(id) ON DELETE SET NULL,
                    FOREIGN KEY (company_id) REFERENCES company(id) ON DELETE CASCADE
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_field_company ON field(company_id)")
        
        # 5. Добавляем company_id в fieldscan (через связь с field)
        logger.info("Обновление таблицы fieldscan...")
        # FieldScan не нуждается в company_id, так как связан с Field
        
        # 6. Добавляем company_id в fieldzone (через связь с field)
        logger.info("Обновление таблицы fieldzone...")
        # FieldZone не нуждается в company_id, так как связан с Field
        
        logger.info("Миграция успешно завершена!")
        
    except Exception as e:
        logger.error(f"Ошибка миграции: {e}")
        raise
    finally:
        database.close()
    
    # Создаём компанию по умолчанию если её нет (вне транзакции)
    try:
        database.connect()
        cursor = database.cursor()
        cursor.execute("SELECT COUNT(*) FROM company")
        if cursor.fetchone()[0] == 0:
            logger.info("Создание компании по умолчанию...")
            cursor.execute("""
                INSERT INTO company (name, slug, created_at, is_active)
                VALUES (?, ?, ?, ?)
            """, ('Default Company', 'default', datetime.now().isoformat(), 1))
            database.commit()
            logger.info("Компания по умолчанию создана!")
        else:
            logger.info("Компания уже существует.")
    except Exception as e:
        logger.error(f"Ошибка создания компании по умолчанию: {e}")
    finally:
        database.close()


if __name__ == '__main__':
    import sys
    db_path = sys.argv[1] if len(sys.argv) > 1 else 'fields.db'
    migrate_db(db_path)
