import os

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
else:
    database = SqliteDatabase(DB_FILE)

class BaseModel(Model):
    class Meta:
        database = database

class Owner(BaseModel):
    name = CharField(unique=True)

class Field(BaseModel):
    name = CharField(null=True)
    geometry_wkt = TextField()  # Храним как WKT (Well-Known Text)
    properties_json = TextField(null=True)  # Доп. свойства (площадь и т.д.)
    
    owner = ForeignKeyField(Owner, backref='fields', null=True)

class FieldZone(BaseModel):
    field = ForeignKeyField(Field, backref='zones')
    name = CharField()
    geometry_wkt = TextField()
    min_value = FloatField()
    max_value = FloatField()
    color = CharField()

def initialize_db():
    if not database.is_closed():
        database.close()
    database.connect(reuse_if_open=True)
    # Удаляем и создаем заново, чтобы тесты были изолированы
    database.drop_tables([Field, Owner, FieldZone])
    database.create_tables([Field, Owner, FieldZone])
    database.close()
