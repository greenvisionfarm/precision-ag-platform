import json

from db import Field, Owner, database, initialize_db


def seed():
    initialize_db()
    database.connect(reuse_if_open=True)

    # Сначала создаём auth-модели если их нет
    try:
        from src.models.auth import Company, User, UserRole
        default_company, _ = Company.get_or_create(
            slug='default',
            defaults={'name': 'Default Company'}
        )
    except Exception:
        default_company = None

    # 1. Создаем владельца
    owner, _ = Owner.get_or_create(name="Иван Фермеров")

    # 2. Создаем тестовое поле
    # Геометрия: простой квадрат где-то в Словакии
    geom = "POLYGON ((19.0 48.0, 19.01 48.0, 19.01 48.01, 19.0 48.01, 19.0 48.0))"
    props = json.dumps({"area_sq_m": 1000000, "description": "Тестовое поле 1"})

    field_data = {
        "name": "Поле Альфа",
        "geometry_wkt": geom,
        "properties_json": props,
        "owner": owner,
        "land_status": "Аренда",
        "parcel_number": "SK-12345/2026"
    }
    if default_company:
        field_data["company"] = default_company
    Field.create(**field_data)

    field_data2 = {
        "name": "Поле Бета",
        "geometry_wkt": geom,
        "properties_json": json.dumps({"area_sq_m": 500000}),
        "owner": None,
        "land_status": "Собственность",
        "parcel_number": "SK-999/A"
    }
    if default_company:
        field_data2["company"] = default_company
    Field.create(**field_data2)

    database.close()
    print("База наполнена тестовыми данными.")

if __name__ == "__main__":
    seed()
