"""
Тесты для ISOXML экспорта.
"""
import os
import tempfile
import xml.etree.ElementTree as ET

import pytest

from db import database
from src.models.field import Field, FieldZone
from src.models.auth import Company
from src.services.isoxml_service import export_isoxml

# Namespace для ISOXML
ISOXML_NS = '{http://www.isobus.net/isobus/TaskFile}'


@pytest.fixture
def setup_field_with_zones(test_db):
    """Создаёт тестовое поле с зонами."""
    company = Company.create(name='ISOXML Co', slug='isoxml-co')
    
    with database.atomic():
        field = Field.create(
            name="Тестовое поле для ISOXML",
            geometry_wkt="POLYGON ((18.72 48.12, 18.78 48.12, 18.78 48.18, 18.72 48.18, 18.72 48.12))",
            properties_json='{"area": 100}',
            company=company
        )
        
        # Создаём 3 зоны с разными NDVI
        zones_data = [
            {"name": "Низкая", "avg_ndvi": 0.25, "color": "#ff4d4d"},
            {"name": "Средняя", "avg_ndvi": 0.55, "color": "#ffcc00"},
            {"name": "Высокая", "avg_ndvi": 0.78, "color": "#2eb82e"},
        ]
        
        for z in zones_data:
            FieldZone.create(
                field=field,
                name=z['name'],
                geometry_wkt="POLYGON ((18.72 48.12, 18.78 48.12, 18.78 48.18, 18.72 48.18, 18.72 48.12))",
                avg_ndvi=z['avg_ndvi'],
                color=z['color']
            )
    
    yield field
    
    with database.atomic():
        FieldZone.delete().where(FieldZone.field == field).execute()
        Field.delete().where(Field.id == field.id).execute()


def test_isoxml_export_creates_valid_xml(setup_field_with_zones):
    """Тест: ISOXML экспорт создаёт валидный XML."""
    with tempfile.NamedTemporaryFile(suffix='.xml', delete=False) as tmp:
        output_path = tmp.name
    
    try:
        result_path = export_isoxml(setup_field_with_zones.id, output_path)
        
        assert result_path == output_path
        assert os.path.exists(output_path)
        
        # Проверяем что XML валидный
        tree = ET.parse(output_path)
        root = tree.getroot()
        
        # Проверяем корневой элемент (с учётом namespace)
        assert root.tag == f'{ISOXML_NS}TASKFILE'
        assert root.get('Version') == '4.0'
        
        # Проверяем задачу
        task = root.find(f'{ISOXML_NS}TASK')
        assert task is not None
        assert task.get('TaskDesignator') == 'Field_Тестовое поле для ISOXML'
        
        # Проверяем поле
        field_elem = task.find(f'{ISOXML_NS}FIELD')
        assert field_elem is not None
        
        # Проверяем зоны
        zones = field_elem.findall(f'{ISOXML_NS}ZONE')
        assert len(zones) == 3
        
    finally:
        if os.path.exists(output_path):
            os.remove(output_path)


def test_isoxml_export_includes_prescription_rates(setup_field_with_zones):
    """Тест: ISOXML экспортирует рекомендации по нормам внесения."""
    with tempfile.NamedTemporaryFile(suffix='.xml', delete=False) as tmp:
        output_path = tmp.name
    
    try:
        export_isoxml(setup_field_with_zones.id, output_path)
        
        tree = ET.parse(output_path)
        root = tree.getroot()
        
        zones = root.findall(f'.//{ISOXML_NS}ZONE')
        
        # Проверяем что у каждой зоны есть PRESCRIPTION с Rate
        rates = []
        for zone in zones:
            prescription = zone.find(f'{ISOXML_NS}PRESCRIPTION')
            assert prescription is not None, f"Зона {zone.get('ZoneDesignator')} не имеет PRESCRIPTION"
            
            rate = prescription.get('Rate')
            assert rate is not None
            rates.append(int(rate))
        
        # Проверяем что нормы разные для разных зон
        # Низкая (0.25) -> 150, Средняя (0.55) -> 250, Высокая (0.78) -> 350
        assert 150 in rates, "Низкая зона должна иметь норму 150 кг/га"
        assert 250 in rates, "Средняя зона должна иметь норму 250 кг/га"
        assert 350 in rates, "Высокая зона должна иметь норму 350 кг/га"
        
    finally:
        if os.path.exists(output_path):
            os.remove(output_path)


def test_isoxml_export_includes_polygon_geometry(setup_field_with_zones):
    """Тест: ISOXML экспортирует геометрию полигонов."""
    with tempfile.NamedTemporaryFile(suffix='.xml', delete=False) as tmp:
        output_path = tmp.name
    
    try:
        export_isoxml(setup_field_with_zones.id, output_path)
        
        tree = ET.parse(output_path)
        root = tree.getroot()
        
        polygons = root.findall(f'.//{ISOXML_NS}POLYGON')
        
        assert len(polygons) > 0, "Должен быть хотя бы один POLYGON"
        
        # Проверяем что у полигона есть точки
        for polygon in polygons:
            points = polygon.findall(f'{ISOXML_NS}POINT')
            assert len(points) > 0, "POLYGON должен иметь хотя бы одну POINT"
            
            # Проверяем что у точки есть координаты
            for point in points:
                assert 'A' in point.attrib, "POINT должна иметь координату A (долгота)"
                assert 'B' in point.attrib, "POINT должна иметь координату B (широта)"
                
    finally:
        if os.path.exists(output_path):
            os.remove(output_path)
