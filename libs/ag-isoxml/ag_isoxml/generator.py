import xml.etree.ElementTree as ET
from xml.dom import minidom
from typing import List, Dict, Any, Optional

class ISOXMLGenerator:
    """
    Генератор ISOXML (ISO 11783) TaskFile для сельскохозяйственной техники.
    Декоплингован от моделей базы данных.
    """

    def __init__(self, version: str = "4.0"):
        self.version = version
        self.namespace = "http://www.isobus.net/isobus/TaskFile"

    def _prettify_xml(self, elem: ET.Element) -> str:
        """Возвращает отформатированную XML строку."""
        rough_string = ET.tostring(elem, encoding='utf-8')
        reparsed = minidom.parseString(rough_string)
        return reparsed.toprettyxml(indent="  ", encoding='utf-8').decode('utf-8')

    def generate_task_file(self, 
                           field_name: str, 
                           field_id: str,
                           zones: List[Dict[str, Any]], 
                           product_type: str = "1", 
                           rate_unit: str = "3") -> str:
        """
        Генерирует XML содержимое TaskFile.
        
        Args:
            field_name: Название поля
            field_id: Уникальный ID поля
            zones: Список словарей с ключами:
                   - name: название зоны
                   - geometry_wkt: WKT полигона (POLYGON)
                   - rate: норма внесения
                   - color: HEX цвет (опционально)
            product_type: Тип продукта (1 = Fertilizer, по умолчанию)
            rate_unit: Единица измерения (3 = kg/ha, по умолчанию)
        """
        taskfile = ET.Element('TASKFILE')
        taskfile.set('Version', self.version)
        taskfile.set('xmlns', self.namespace)
        
        # TASK
        task = ET.SubElement(taskfile, 'TASK')
        task.set('TaskId', f'T{field_id}')
        task.set('TaskDesignator', f'Field_{field_name}')
        task.set('TaskType', '1')  # 1 = Application
        
        # FIELD
        field_elem = ET.SubElement(task, 'FIELD')
        field_elem.set('FieldId', f'F{field_id}')
        field_elem.set('FieldDesignator', field_name)
        
        for idx, zone in enumerate(zones, 1):
            zone_elem = ET.SubElement(field_elem, 'ZONE')
            zone_elem.set('ZoneId', f'Z{field_id}_{idx}')
            zone_elem.set('ZoneDesignator', zone.get('name', f'Zone {idx}'))
            
            color = zone.get('color', 'FFFFFF').replace('#', '')
            zone_elem.set('ZoneColor', color)
            
            # PRESCRIPTION
            prescription = ET.SubElement(zone_elem, 'PRESCRIPTION')
            prescription.set('ProductType', product_type)
            prescription.set('Rate', str(zone.get('rate', 0)))
            prescription.set('RateUnit', rate_unit)
            
            # POLYGON
            polygon = ET.SubElement(zone_elem, 'POLYGON')
            polygon.set('PolygonType', '1')  # 1 = Treatment zone
            
            wkt = zone.get('geometry_wkt', '')
            if wkt.startswith('POLYGON'):
                # Упрощенный парсинг WKT для демонстрации. 
                # В продакшене лучше использовать shapely.wkt
                coords_str = wkt[wkt.find('(')+1:wkt.rfind(')')].replace('(', '').replace(')', '')
                coords = [c.strip().split() for c in coords_str.split(',')]
                
                for lon, lat in coords:
                    point = ET.SubElement(polygon, 'POINT')
                    point.set('A', lon)  # Longitude
                    point.set('B', lat)  # Latitude
                    
        return self._prettify_xml(taskfile)
