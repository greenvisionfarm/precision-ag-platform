"""Модуль валидации входных данных."""
from typing import Any, Dict, List, Optional


class ValidationError(Exception):
    """Исключение валидации."""
    pass


def validate_field_data(data: Dict[str, Any]) -> List[str]:
    """Валидация данных поля.
    
    Args:
        data: Словарь с данными поля.
        
    Returns:
        Список ошибок валидации. Пустой список если данных валидны.
    """
    errors = []
    
    # Geometry обязательна
    if 'geometry' not in data:
        errors.append("Geometry is required")
    else:
        geometry = data['geometry']
        if not isinstance(geometry, dict):
            errors.append("Geometry must be an object")
        elif 'type' not in geometry:
            errors.append("Geometry must have a 'type' field")
        elif geometry['type'] not in ('Polygon', 'MultiPolygon'):
            errors.append("Geometry type must be Polygon or MultiPolygon")
    
    # Name опционален, но с ограничениями
    if 'name' in data:
        name = data['name']
        if not isinstance(name, str):
            errors.append("Name must be a string")
        elif len(name) > 255:
            errors.append("Name must be up to 255 characters")
        elif not name.strip():
            errors.append("Name cannot be empty")
    
    # Owner опционален
    if 'owner_id' in data and data['owner_id'] is not None:
        if not isinstance(data['owner_id'], int) or data['owner_id'] <= 0:
            errors.append("Owner ID must be a positive integer")
    
    return errors


def validate_owner_data(data: Dict[str, Any]) -> List[str]:
    """Валидация данных владельца.
    
    Args:
        data: Словарь с данными владельца.
        
    Returns:
        Список ошибок валидации.
    """
    errors = []
    
    if 'name' not in data:
        errors.append("Name is required")
    elif not isinstance(data['name'], str):
        errors.append("Name must be a string")
    elif len(data['name']) > 255:
        errors.append("Name must be up to 255 characters")
    elif not data['name'].strip():
        errors.append("Name cannot be empty")
    
    return errors


def validate_file_upload(file_info: Optional[Dict[str, Any]], 
                         allowed_extensions: List[str],
                         max_size_mb: int = 100) -> List[str]:
    """Валидация загружаемого файла.
    
    Args:
        file_info: Информация о файле из request.files.
        allowed_extensions: Разрешённые расширения (например, ['.tif', '.tiff']).
        max_size_mb: Максимальный размер файла в МБ.
        
    Returns:
        Список ошибок валидации.
    """
    errors = []
    
    if not file_info:
        errors.append("No file provided")
        return errors
    
    if 'filename' not in file_info:
        errors.append("File has no name")
        return errors
    
    filename = file_info['filename']
    ext = '.' + filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
    
    if ext not in allowed_extensions:
        errors.append(f"File type {ext} not allowed. Allowed: {', '.join(allowed_extensions)}")
    
    # Проверка размера
    if 'body' in file_info:
        size_mb = len(file_info['body']) / (1024 * 1024)
        if size_mb > max_size_mb:
            errors.append(f"File size ({size_mb:.1f} MB) exceeds limit ({max_size_mb} MB)")
    
    return errors
