from peewee import *
import os

# Определяем путь к файлу базы данных SQLite
# Он будет создан в корневой директории проекта
DEFAULT_DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fields.db')

def get_database(db_path=None):
    """Возвращает экземпляр SqliteDatabase. Если db_path не указан, использует DEFAULT_DB_FILE."""
    return SqliteDatabase(db_path if db_path else DEFAULT_DB_FILE)

database = get_database() # Используем функцию для получения экземпляра БД

class BaseModel(Model):
    class Meta:
        database = database

class Field(BaseModel):
    # Название поля, если оно есть в исходных данных
    name = CharField(null=True)
    # Геометрия поля в формате Well-Known Text (WKT)
    geometry_wkt = TextField()
    # Дополнительные свойства поля в формате JSON
    properties_json = TextField(null=True)

    class Meta:
        table_name = 'fields'

# Функция для инициализации базы данных и создания таблиц
def initialize_db(db_path=None):
    """Инициализирует базу данных и создает таблицы. Если db_path указан, использует его."""
    global database # Объявляем database как глобальную, чтобы можно было ее переопределить
    database = get_database(db_path) # Получаем экземпляр БД для инициализации
    database.connect()
    database.create_tables([Field])
    database.close()

if __name__ == '__main__':
    # Если запустить db.py напрямую, он инициализирует БД по умолчанию
    initialize_db()
    print(f"База данных '{DEFAULT_DB_FILE}' инициализирована и таблица 'fields' создана.")