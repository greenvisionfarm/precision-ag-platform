from peewee import *
import os

# Определяем путь к файлу базы данных SQLite
DEFAULT_DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fields.db')
TEST_DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'test_fields.db')

def get_database():
    """Возвращает экземпляр SqliteDatabase в зависимости от окружения."""
    env = os.getenv('FIELD_MAPPER_ENV', 'development')
    if env == 'test':
        return SqliteDatabase(TEST_DB_FILE)
    return SqliteDatabase(DEFAULT_DB_FILE)

database = get_database()

class BaseModel(Model):
    class Meta:
        database = database

class Owner(BaseModel):
    name = CharField(unique=True)
    # Можно добавить другие поля, например contact_info = CharField(null=True)

    class Meta:
        table_name = 'owners'

class Field(BaseModel):
    name = CharField(null=True)
    geometry_wkt = TextField()
    properties_json = TextField(null=True)
    # Связь с владельцем
    owner = ForeignKeyField(Owner, backref='fields', null=True)
    
    # Новые поля для земельного учета
    land_status = CharField(null=True) # Собственность, Аренда, и т.д.
    parcel_number = CharField(null=True)
    lease_start = DateField(null=True)
    lease_end = DateField(null=True)

    class Meta:
        table_name = 'fields'

class FieldZone(BaseModel):
    field = ForeignKeyField(Field, backref='zones', on_delete='CASCADE')
    name = CharField() # Например: "Низкая продуктивность"
    geometry_wkt = TextField()
    avg_ndvi = FloatField(null=True)
    area_ha = FloatField(null=True)
    color = CharField(null=True) # Hex код для карты

    class Meta:
        table_name = 'field_zones'

def initialize_db():
    """Инициализирует базу данных и создает таблицы."""
    global database
    database = get_database()
    database.connect(reuse_if_open=True)
    database.create_tables([Owner, Field, FieldZone])
    database.close()

if __name__ == '__main__':
    # Если запустить db.py напрямую, он пересоздаст БД
    if os.path.exists(DEFAULT_DB_FILE):
        os.remove(DEFAULT_DB_FILE)
    initialize_db()
    print(f"База данных '{DEFAULT_DB_FILE}' пересоздана.")
