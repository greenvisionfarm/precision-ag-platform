"""
Экспорт зон в формате ISOXML для сельхозтехники.

ISOXML (ISO 11783) — стандарт для обмена данными между сельхозтехникой
и системами управления фермой. Поддерживается John Deere, Claas, Case IH и др.
"""
import logging
import os
from typing import List

from ag_isoxml import ISOXMLGenerator
from src.models.field import Field, FieldZone


def export_isoxml(field_id: int, output_path: str) -> str:
    """
    Экспортирует зоны поля в формате ISOXML TaskFile.
    Использует внешнюю библиотеку ag-isoxml для генерации XML.
    """
    try:
        field = Field.get_by_id(field_id)
        zones_query = list(FieldZone.select().where(FieldZone.field == field))
        
        if not zones_query:
            raise ValueError(f"Нет зон для поля {field_id}")
        
        # Подготавливаем данные для библиотеки
        lib_zones = []
        for zone in zones_query:
            # Получаем дефолтные нормы для культуры
            from src.services.crop_classifier import CROP_PROFILES, CropType
            default_rates = [150, 250, 350]
            
            if zone.scan and getattr(zone.scan, 'crop_type', None):
                try:
                    crop_enum = CropType(zone.scan.crop_type)
                    if crop_enum in CROP_PROFILES:
                        default_rates = CROP_PROFILES[crop_enum].default_rates
                except (ValueError, KeyError):
                    pass

            # Рассчитываем норму внесения на основе NDVI
            if zone.avg_ndvi:
                if zone.avg_ndvi < 0.4:
                    rate = default_rates[0]
                elif zone.avg_ndvi < 0.6:
                    rate = default_rates[1]
                else:
                    rate = default_rates[2]
            else:
                rate = default_rates[1]

            lib_zones.append({
                "name": zone.name,
                "geometry_wkt": zone.geometry_wkt,
                "rate": rate,
                "color": zone.color
            })
        
        # Генерируем XML через библиотеку
        generator = ISOXMLGenerator()
        xml_content = generator.generate_task_file(
            field_name=field.name,
            field_id=str(field.id),
            zones=lib_zones
        )
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(xml_content)
        
        logging.info(f"ISOXML экспортирован: {output_path}")
        return output_path
        
    except Exception as e:
        logging.error(f"Ошибка экспорта ISOXML: {str(e)}")
        raise


def export_all_fields_isoxml(output_dir: str) -> List[str]:
    """
    Экспортирует все поля с зонами в формате ISOXML.
    
    Args:
        output_dir: Директория для сохранения файлов
    
    Returns:
        Список созданных файлов
    """
    os.makedirs(output_dir, exist_ok=True)
    
    fields = Field.select()
    created_files = []
    
    for field in fields:
        zones_count = FieldZone.select().where(FieldZone.field == field).count()
        if zones_count > 0:
            output_path = os.path.join(output_dir, f'field_{field.id}_isoxml.xml')
            export_isoxml(field.id, output_path)
            created_files.append(output_path)
    
    return created_files
