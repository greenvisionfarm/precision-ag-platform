"""
Модель владельца (устаревшая, для совместимости).
"""
from peewee import CharField, Model


class Owner(Model):
    """Модель владельца поля (устаревшая)."""
    name = CharField(unique=True)

    class Meta:
        table_name = 'owner'
