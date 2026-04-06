"""
Экспорт зон в формате ISOXML для сельхозтехники.

ISOXML (ISO 11783) — стандарт для обмена данными между сельхозтехникой
и системами управления фермой. Поддерживается John Deere, Claas, Case IH и др.
"""
import logging
import os
import xml.etree.ElementTree as ET
from typing import List
from xml.dom import minidom

from db import Field, FieldZone


def prettify_xml(elem: ET.Element) -> str:
    """Возвращает отформатированную XML строку."""
    rough_string = ET.tostring(elem, encoding='utf-8')
    reparsed = minidom.parseString(rough_string)
    return reparsed.toprettyxml(indent="  ", encoding='utf-8').decode('utf-8')


def export_isoxml(field_id: int, output_path: str) -> str:
    """
    Экспортирует зоны поля в формате ISOXML TaskFile.
    
    Args:
        field_id: ID поля для экспорта
        output_path: Путь для сохранения XML файла
    
    Returns:
        Путь к созданному файлу
    
    Формат ISOXML TaskFile включает:
    - TASK: задача внесения
    - ZONE: зоны с рекомендациями по нормам
    - POLYGON: геометрия зон
    """
    try:
        field = Field.get_by_id(field_id)
        zones = list(FieldZone.select().where(FieldZone.field == field))
        
        if not zones:
            raise ValueError(f"Нет зон для поля {field_id}")
        
        # Создаём корневой элемент TaskFile
        taskfile = ET.Element('TASKFILE')
        taskfile.set('Version', '4.0')
        taskfile.set('xmlns', 'http://www.isobus.net/isobus/TaskFile')
        
        # Добавляем задачу
        task = ET.SubElement(taskfile, 'TASK')
        task.set('TaskId', f'T{field_id}')
        task.set('TaskDesignator', f'Field_{field.name}')
        task.set('TaskType', '1')  # 1 = Application
        
        # Добавляем информацию о поле
        field_elem = ET.SubElement(task, 'FIELD')
        field_elem.set('FieldId', f'F{field_id}')
        field_elem.set('FieldDesignator', field.name)
        
        # Добавляем зоны как POLYGON с рекомендациями
        for idx, zone in enumerate(zones, 1):
            zone_elem = ET.SubElement(field_elem, 'ZONE')
            zone_elem.set('ZoneId', f'Z{field_id}_{idx}')
            zone_elem.set('ZoneDesignator', zone.name)
            zone_elem.set('ZoneColor', zone.color.replace('#', ''))
            
            # Добавляем рекомендации по внесению
            prescription = ET.SubElement(zone_elem, 'PRESCRIPTION')
            prescription.set('ProductType', '1')  # 1 = Fertilizer
            
            # Рассчитываем норму внесения на основе NDVI
            # Низкая зона: 150 кг/га, Средняя: 250 кг/га, Высокая: 350 кг/га
            if zone.avg_ndvi:
                if zone.avg_ndvi < 0.4:
                    rate = 150  # Низкая зона
                elif zone.avg_ndvi < 0.6:
                    rate = 250  # Средняя зона
                else:
                    rate = 350  # Высокая зона
            else:
                rate = 250  # По умолчанию
            
            prescription.set('Rate', str(rate))
            prescription.set('RateUnit', '3')  # 3 = kg/ha
            
            # Добавляем геометрию зоны
            polygon = ET.SubElement(zone_elem, 'POLYGON')
            polygon.set('PolygonType', '1')  # 1 = Treatment zone
            
            # Парсим WKT геометрию
            wkt = zone.geometry_wkt
            if wkt.startswith('POLYGON'):
                # Извлекаем координаты из WKT
                coords_str = wkt[wkt.find('(')+1:wkt.rfind(')')]
                coords = [c.strip().split() for c in coords_str.split(',')]
                
                # Добавляем точки полигона
                for lon, lat in coords:
                    point = ET.SubElement(polygon, 'POINT')
                    point.set('A', lon)  # Долгота
                    point.set('B', lat)  # Широта
        
        # Сохраняем XML
        xml_string = prettify_xml(taskfile)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(xml_string)
        
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
