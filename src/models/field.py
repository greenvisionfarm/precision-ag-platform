"""
Модели полей и связанных данных.
"""
from datetime import datetime
from typing import Optional

from peewee import (
    CharField,
    DateTimeField,
    FloatField,
    ForeignKeyField,
    IntegerField,
    TextField,
)

from db import BaseModel, database
from src.models.auth import Company


class Owner(BaseModel):
    """Модель владельца поля (устаревшая, оставлена для совместимости)."""

    name = CharField(unique=True, help_text="Имя владельца")
    company = ForeignKeyField(
        Company,
        backref='owners',
        on_delete='CASCADE',
        null=True,
        help_text="Компания владельца"
    )

    class Meta:
        table_name = 'owner'
        db_table = 'owner'

    def __str__(self) -> str:
        return self.name


class Field(BaseModel):
    """Модель сельскохозяйственного поля."""

    name = CharField(null=True, help_text="Название поля")
    geometry_wkt = TextField(help_text="Геометрия в формате WKT")
    properties_json = TextField(null=True, help_text="Дополнительные свойства (площадь и т.д.)")
    
    # Связи
    owner = ForeignKeyField(
        Owner,
        backref='fields',
        null=True,
        on_delete='SET NULL',
        help_text="Владелец поля"
    )
    company = ForeignKeyField(
        Company,
        backref='fields',
        on_delete='CASCADE',
        help_text="Компания, которой принадлежит поле"
    )

    # Метаданные
    created_at = DateTimeField(default=datetime.now, help_text="Дата создания")
    updated_at = DateTimeField(null=True, help_text="Дата обновления")

    class Meta:
        table_name = 'field'
        db_table = 'field'

    def __str__(self) -> str:
        return self.name or f"Field {self.id}"

    @classmethod
    def for_company(cls, company):
        """Возвращает выборку полей для компании."""
        return cls.select().where(cls.company == company)


class FieldScan(BaseModel):
    """Модель скана поля (NDVI TIFF файл с датой загрузки)."""

    field = ForeignKeyField(
        Field,
        backref='scans',
        on_delete='CASCADE',
        help_text="Поле, к которому принадлежит скан"
    )
    file_path = CharField(help_text="Путь к TIFF файлу")
    filename = CharField(help_text="Оригинальное имя файла")
    uploaded_at = DateTimeField(help_text="Дата загрузки")

    # Метрики NDVI
    ndvi_min = FloatField(null=True, help_text="Минимальный NDVI в скане")
    ndvi_max = FloatField(null=True, help_text="Максимальный NDVI в скане")
    ndvi_avg = FloatField(null=True, help_text="Средний NDVI в скане")

    # Статус обработки
    processed = TextField(null=True, help_text="'true'/'false' — обработан ли файл")
    task_id = CharField(null=True, help_text="ID задачи обработки")

    # Источник данных
    source = CharField(
        default='satellite',
        help_text="Источник: 'satellite', 'drone', 'file'"
    )

    # Информация о культуре
    crop_type = CharField(null=True, help_text="Тип культуры (wheat, corn, etc.)")
    crop_confidence = FloatField(
        null=True,
        help_text="Уверенность классификации культуры (0-1)"
    )

    class Meta:
        table_name = 'fieldscan'
        db_table = 'fieldscan'

    def __str__(self) -> str:
        return f"{self.field.name} - {self.filename}"


class FieldZone(BaseModel):
    """Модель зоны поля (для дифференцированного внесения)."""

    field = ForeignKeyField(
        Field,
        backref='zones',
        on_delete='CASCADE',
        help_text="Поле, к которому принадлежит зона"
    )
    scan = ForeignKeyField(
        FieldScan,
        backref='zones',
        null=True,
        on_delete='CASCADE',
        help_text="Скан, к которому принадлежит зона"
    )
    name = CharField(help_text="Название зоны")
    geometry_wkt = TextField(help_text="Геометрия зоны в формате WKT")
    
    # Метрики зоны
    min_value = FloatField(null=True, help_text="Минимальное значение в зоне")
    max_value = FloatField(null=True, help_text="Максимальное значение в зоне")
    avg_ndvi = FloatField(null=True, help_text="Средний NDVI в зоне")
    color = CharField(help_text="Цвет зоны для отображения")

    # Норма внесения (VRA)
    rate_kg_ha = FloatField(null=True, help_text="Норма внесения удобрений (кг/га)")

    # Продукт для внесения
    product_name = CharField(null=True, help_text="Название продукта (Аммиачная селитра, Мочевина, ...)")
    product_type = CharField(null=True, help_text="Тип продукта: nitrogen, npk, phosphorus, potassium, organic")

    class Meta:
        table_name = 'fieldzone'
        db_table = 'fieldzone'

    def __str__(self) -> str:
        return f"{self.field.name} - {self.name}"


class Mission(BaseModel):
    """Модель миссии дрона (план полёта)."""

    field = ForeignKeyField(
        Field,
        backref='missions',
        on_delete='CASCADE',
        help_text="Поле, для которого создана миссия"
    )
    company = ForeignKeyField(
        Company,
        backref='missions',
        on_delete='CASCADE',
        help_text="Компания"
    )

    # Параметры полёта
    name = CharField(null=True, help_text="Название миссии")
    height = FloatField(default=100, help_text="Высота полёта (м)")
    overlap_h = FloatField(default=80, help_text="Фронтальное перекрытие (%)")
    overlap_w = FloatField(default=70, help_text="Боковое перекрытие (%)")
    direction = IntegerField(null=True, help_text="Угол курса (градусы, null = авто)")

    # Метаданные
    created_at = DateTimeField(default=datetime.now, help_text="Дата создания")
    notes = TextField(null=True, help_text="Заметки к миссии")

    class Meta:
        table_name = 'mission'
        db_table = 'mission'

    def __str__(self) -> str:
        return f"Mission {self.id} - {self.name or 'Unnamed'}"


class AuditLog(BaseModel):
    """Аудит-журнал изменений в системе."""

    company = ForeignKeyField(
        Company,
        backref='audit_logs',
        null=True,
        on_delete='CASCADE',
        help_text="Компания"
    )
    user_email = CharField(null=True, help_text="Email пользователя")
    action = CharField(help_text="Действие: rename, assign_owner, update_details, delete_field и т.д.")
    entity_type = CharField(help_text="Тип объекта: field, owner, scan и т.д.")
    entity_id = IntegerField(null=True, help_text="ID объекта")
    entity_name = CharField(null=True, help_text="Название объекта для читаемости")
    details = TextField(null=True, help_text="JSON с деталями изменения (старое/новое значение)")
    created_at = DateTimeField(default=datetime.now, help_text="Время записи")

    class Meta:
        table_name = 'auditlog'
        db_table = 'auditlog'

    def __str__(self) -> str:
        return f"[{self.action}] {self.entity_type} #{self.entity_id} by {self.user_email}"


class FieldJournal(BaseModel):
    """Журнал полевых работ — история посевов и внесений."""

    field = ForeignKeyField(
        Field,
        backref='journal_entries',
        on_delete='CASCADE',
        help_text="Поле"
    )
    company = ForeignKeyField(
        Company,
        backref='journal_entries',
        on_delete='CASCADE',
        help_text="Компания"
    )

    # Что посажено
    crop_type = CharField(help_text="Тип культуры: wheat, corn, sunflower, soybean, ...")
    crop_variety = CharField(null=True, help_text="Сорт культуры (опционально)")
    planting_date = DateTimeField(null=True, help_text="Дата посадки")
    harvest_date = DateTimeField(null=True, help_text="Дата уборки")

    # Что внесено
    product_name = CharField(null=True, help_text="Название продукта (Аммиачная селитра, ...)")
    product_type = CharField(null=True, help_text="Тип: nitrogen, npk, phosphorus, potassium, organic")
    application_rate = FloatField(null=True, help_text="Норма внесения (кг/га)")
    application_date = DateTimeField(null=True, help_text="Дата внесения")
    application_method = CharField(null=True, help_text="Способ: foliar, soil, seed")

    # Связь с NDVI сканом
    scan = ForeignKeyField(
        FieldScan,
        backref='journal_entries',
        null=True,
        on_delete='SET NULL',
        help_text="Скан, привязанный к записи (NDVI)"
    )

    # Урожай
    yield_amount = FloatField(null=True, help_text="Урожайность (ц/га)")
    yield_date = DateTimeField(null=True, help_text="Дата замера урожайности")

    # Заметки
    notes = TextField(null=True, help_text="Дополнительные заметки")

    # Метаданные
    created_at = DateTimeField(default=datetime.now, help_text="Дата создания записи")
    updated_at = DateTimeField(null=True, help_text="Дата обновления записи")

    class Meta:
        table_name = 'fieldjournal'
        db_table = 'fieldjournal'

    def __str__(self) -> str:
        return f"{self.field.name} - {self.crop_type} ({self.planting_date})"
