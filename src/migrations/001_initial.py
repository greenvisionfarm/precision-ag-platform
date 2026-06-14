"""Начальная схема: Company, User, Field, FieldScan, FieldZone, Owner, FieldJournal"""
from playhouse.migrate import SchemaMigrator


def upgrade(migrator: SchemaMigrator) -> None:
    db = migrator.database
    db.execute_sql("""
        CREATE TABLE IF NOT EXISTS company (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name VARCHAR(255) UNIQUE NOT NULL,
            slug VARCHAR(255) UNIQUE NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            is_active INTEGER DEFAULT 1,
            settings_json TEXT
        )
    """)
    db.execute_sql("CREATE INDEX IF NOT EXISTS idx_company_slug ON company(slug)")

    db.execute_sql("""
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
    db.execute_sql("CREATE INDEX IF NOT EXISTS idx_user_email ON user(email)")
    db.execute_sql("CREATE INDEX IF NOT EXISTS idx_user_company ON user(company_id)")

    db.execute_sql("""
        CREATE TABLE IF NOT EXISTS owner (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name VARCHAR(255) UNIQUE NOT NULL,
            company_id INTEGER,
            FOREIGN KEY (company_id) REFERENCES company(id) ON DELETE CASCADE
        )
    """)
    db.execute_sql("CREATE INDEX IF NOT EXISTS idx_owner_company ON owner(company_id)")

    db.execute_sql("""
        CREATE TABLE IF NOT EXISTS field (
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
    db.execute_sql("CREATE INDEX IF NOT EXISTS idx_field_company ON field(company_id)")

    db.execute_sql("""
        CREATE TABLE IF NOT EXISTS fieldscan (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            field_id INTEGER NOT NULL,
            file_path VARCHAR(500),
            filename VARCHAR(255),
            uploaded_at DATETIME,
            processed TEXT,
            task_id VARCHAR(255),
            source VARCHAR(50) DEFAULT 'satellite',
            crop_type VARCHAR(100),
            crop_confidence REAL,
            ndvi_min REAL,
            ndvi_max REAL,
            ndvi_avg REAL,
            FOREIGN KEY (field_id) REFERENCES field(id) ON DELETE CASCADE
        )
    """)

    db.execute_sql("""
        CREATE TABLE IF NOT EXISTS fieldzone (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            field_id INTEGER NOT NULL,
            scan_id INTEGER,
            name VARCHAR(255) NOT NULL,
            geometry_wkt TEXT NOT NULL,
            avg_ndvi REAL,
            color VARCHAR(20),
            rate_kg_ha REAL,
            product_name VARCHAR(255),
            product_type VARCHAR(255),
            FOREIGN KEY (field_id) REFERENCES field(id) ON DELETE CASCADE,
            FOREIGN KEY (scan_id) REFERENCES fieldscan(id) ON DELETE SET NULL
        )
    """)

    db.execute_sql("""
        CREATE TABLE IF NOT EXISTS fieldjournal (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            field_id INTEGER NOT NULL,
            company_id INTEGER NOT NULL,
            crop_type VARCHAR NOT NULL,
            crop_variety VARCHAR(255),
            planting_date DATETIME,
            harvest_date DATETIME,
            product_name VARCHAR(255),
            product_type VARCHAR(255),
            application_rate REAL,
            application_date DATETIME,
            application_method VARCHAR(255),
            scan_id INTEGER,
            yield_amount REAL,
            yield_date DATETIME,
            notes TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME,
            FOREIGN KEY (field_id) REFERENCES field(id) ON DELETE CASCADE,
            FOREIGN KEY (company_id) REFERENCES company(id) ON DELETE CASCADE,
            FOREIGN KEY (scan_id) REFERENCES fieldscan(id) ON DELETE SET NULL
        )
    """)
    db.execute_sql("CREATE INDEX IF NOT EXISTS idx_journal_field ON fieldjournal(field_id)")
    db.execute_sql("CREATE INDEX IF NOT EXISTS idx_journal_company ON fieldjournal(company_id)")


def downgrade(migrator: SchemaMigrator) -> None:
    db = migrator.database
    db.execute_sql("DROP TABLE IF EXISTS fieldjournal")
    db.execute_sql("DROP TABLE IF EXISTS fieldzone")
    db.execute_sql("DROP TABLE IF EXISTS fieldscan")
    db.execute_sql("DROP TABLE IF EXISTS field")
    db.execute_sql("DROP TABLE IF EXISTS owner")
    db.execute_sql("DROP TABLE IF EXISTS user")
    db.execute_sql("DROP TABLE IF EXISTS company")
