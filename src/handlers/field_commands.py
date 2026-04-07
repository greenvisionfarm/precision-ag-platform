"""
Команды для обновления полей (паттерн Command).
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from shapely.geometry import shape

from db import Field, Owner
from src.services.gis_service import calculate_accurate_area


class FieldCommand(ABC):
    """Базовый класс для команд обновления поля."""
    
    @abstractmethod
    def execute(self, field: Field, data: Dict[str, Any]) -> None:
        """Выполняет команду над полем.
        
        Args:
            field: Экземпляр поля для обновления.
            data: Данные для обновления.
        """
        pass


class RenameCommand(FieldCommand):
    """Команда для переименования поля."""
    
    def execute(self, field: Field, data: Dict[str, Any]) -> None:
        field.name = data.get('new_name')


class AssignOwnerCommand(FieldCommand):
    """Команда для назначения владельца полю."""

    def execute(self, field: Field, data: Dict[str, Any]) -> None:
        owner_id = data.get('owner_id')
        # Важно: сохраняем owner_id а не объект для корректной работы с Peewee
        field.owner_id = owner_id if owner_id else None


class UpdateDetailsCommand(FieldCommand):
    """Команда для обновления деталей поля (статус, кадастровый номер)."""
    
    def execute(self, field: Field, data: Dict[str, Any]) -> None:
        props = self._get_properties(field)
        props['land_status'] = data.get('land_status', props.get('land_status'))
        props['parcel_number'] = data.get('parcel_number', props.get('parcel_number'))
        field.properties_json = self._serialize_properties(props)
    
    def _get_properties(self, field: Field) -> Dict[str, Any]:
        """Получает свойства поля, десериализуя JSON."""
        import json
        return json.loads(field.properties_json or '{}')
    
    def _serialize_properties(self, props: Dict[str, Any]) -> str:
        """Сериализует свойства в JSON."""
        import json
        return json.dumps(props)


class UpdateGeometryCommand(FieldCommand):
    """Команда для обновления геометрии поля."""
    
    def execute(self, field: Field, data: Dict[str, Any]) -> None:
        if 'geometry' not in data:
            return
        
        poly = shape(data['geometry'])
        area = calculate_accurate_area(poly)
        field.geometry_wkt = poly.wkt
        
        props = self._get_properties(field)
        props['area_sq_m'] = area
        field.properties_json = self._serialize_properties(props)
    
    def _get_properties(self, field: Field) -> Dict[str, Any]:
        """Получает свойства поля, десериализуя JSON."""
        import json
        return json.loads(field.properties_json or '{}')
    
    def _serialize_properties(self, props: Dict[str, Any]) -> str:
        """Сериализует свойства в JSON."""
        import json
        return json.dumps(props)


# Реестр команд
FIELD_COMMANDS: Dict[str, FieldCommand] = {
    'rename': RenameCommand(),
    'assign_owner': AssignOwnerCommand(),
    'update_details': UpdateDetailsCommand(),
    'update_geometry': UpdateGeometryCommand(),
}


def get_command(action: str) -> Optional[FieldCommand]:
    """Получает команду по имени действия.
    
    Args:
        action: Имя действия (rename, assign_owner, update_details, update_geometry).
        
    Returns:
        Экземпляр команды или None если действие не найдено.
    """
    return FIELD_COMMANDS.get(action)


def get_available_actions() -> list:
    """Получает список доступных действий.
    
    Returns:
        Список имен доступных действий.
    """
    return list(FIELD_COMMANDS.keys())
