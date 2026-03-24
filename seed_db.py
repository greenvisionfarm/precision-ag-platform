import json

from db import Field, Owner, database, initialize_db


def seed():
    initialize_db()
    database.connect(reuse_if_open=True)
    
    # 1. Создаем владельца
    owner, _ = Owner.get_or_create(name="Иван Фермеров")
    
    # 2. Создаем тестовое поле
    # Геометрия: простой квадрат где-то в Словакии
    geom = "POLYGON ((19.0 48.0, 19.01 48.0, 19.01 48.01, 19.0 48.01, 19.0 48.0))"
    props = json.dumps({"area_sq_m": 1000000, "description": "Тестовое поле 1"})
    
    Field.create(
        name="Поле Альфа",
        geometry_wkt=geom,
        properties_json=props,
        owner=owner,
        land_status="Аренда",
        parcel_number="SK-12345/2026"
    )
    
    Field.create(
        name="Поле Бета",
        geometry_wkt=geom, # Для простоты
        properties_json=json.dumps({"area_sq_m": 500000}),
        owner=None,
        land_status="Собственность",
        parcel_number="SK-999/A"
    )
    
    database.close()
    print("База наполнена тестовыми данными.")

if __name__ == "__main__":
    seed()
