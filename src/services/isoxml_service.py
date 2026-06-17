"""
Экспорт зон в формате ISOXML для сельхозтехники.

ISOXML (ISO 11783) — стандарт для обмена данными между сельхозтехникой
и системами управления фермой. Поддерживается John Deere, Claas, Case IH и др.
"""
import logging
import os
from typing import List, Optional

from ag_isoxml import ISOXMLGenerator
from src.models.field import Field, FieldZone
from src.services.rate_resolver import resolve_zone_rate


# Маппинг типов продуктов на ISOXML ProductType (ISO 11783-10)
# Значения: 1=generic, 2=herbicide, 3=fertilizer, 4=fuel
PRODUCT_TYPE_MAP = {
    "nitrogen": "3",
    "npk": "3",
    "phosphorus": "3",
    "potassium": "3",
    "organic": "3",
    "lime": "3",
    "sulfur": "3",
    "herbicide": "2",
    "fuel": "4",
}


def export_isoxml(
    field_id: int,
    output_path: str,
    product_name: Optional[str] = None,
    product_type: Optional[str] = None
) -> str:
    """
    Экспортирует зоны поля в формате ISOXML TaskFile.
    Использует внешнюю библиотеку ag-isoxml для генерации XML.
    
    Args:
        field_id: ID поля
        output_path: Путь для сохранения XML
        product_name: Название продукта (переопределяет product_name из зон)
        product_type: Тип продукта (переопределяет product_type из зон)
    """
    try:
        field = Field.get_by_id(field_id)
        zones_query = list(FieldZone.select().where(FieldZone.field == field))
        
        if not zones_query:
            raise ValueError(f"Нет зон для поля {field_id}")
        
        # Определяем продукт из зон или параметров
        zone_product_name = product_name
        zone_product_type = product_type
        
        if not zone_product_name:
            # Берем product_name из первой зоны, где он задан
            for zone in zones_query:
                if zone.product_name:
                    zone_product_name = zone.product_name
                    zone_product_type = zone.product_type or "nitrogen"
                    break
        
        # Если всё ещё нет продукта, используем дефолт
        if not zone_product_name:
            zone_product_name = "Аммиачная селитра"
            zone_product_type = "nitrogen"
        
        # Подготавливаем данные для библиотеки
        lib_zones = []
        for zone in zones_query:
            rate = resolve_zone_rate(
                rate_kg_ha=zone.rate_kg_ha,
                avg_ndvi=zone.avg_ndvi,
                crop_type=getattr(zone.scan, 'crop_type', None) if zone.scan else None,
            )

            # Используем продукт из зоны или общий
            z_product_name = zone.product_name or zone_product_name
            z_product_type = zone.product_type or zone_product_type

            lib_zones.append({
                "name": zone.name,
                "geometry_wkt": zone.geometry_wkt,
                "rate": rate,
                "color": zone.color,
                "product_name": z_product_name,
                "product_type": PRODUCT_TYPE_MAP.get(z_product_type, z_product_type)
            })
        
        # Генерируем XML через библиотеку
        generator = ISOXMLGenerator()
        xml_content = generator.generate_task_file(
            field_name=field.name,
            field_id=str(field.id),
            zones=lib_zones,
            product_type=PRODUCT_TYPE_MAP.get(zone_product_type, '1')
        )
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(xml_content)
        
        logging.info(f"ISOXML экспортирован: {output_path} (продукт: {zone_product_name})")
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
