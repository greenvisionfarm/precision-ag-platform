import io
import zipfile

from shapely.geometry import Polygon

from src.services.gis_service import calculate_accurate_area
from src.services.kmz_service import create_kmz


def test_calculate_area_unit():
    # Квадрат ~100x100 метров в Словакии
    coords = [(19.0, 48.0), (19.00135, 48.0), (19.00135, 48.0009), (19.0, 48.0009), (19.0, 48.0)]
    poly = Polygon(coords)
    area = calculate_accurate_area(poly)
    # 1.35 * 0.9 примерно соответствует ~1 га (10000 м2)
    assert 9000 < area < 11000

def test_kmz_generation_logic():
    field_id = 99
    name = "Test KMZ"
    wkt = "POLYGON ((19 48, 19.01 48, 19.01 48.01, 19 48.01, 19 48))"
    
    kmz_data = create_kmz(field_id, name, wkt, height=100, overlap_h=80, overlap_w=70)
    
    # Проверяем, что это валидный ZIP
    with zipfile.ZipFile(io.BytesIO(kmz_data)) as z:
        files = z.namelist()
        assert "wpmz/template.kml" in files
        assert "wpmz/waylines.wpml" in files
        
        # Проверяем содержимое template.kml на наличие параметров
        with z.open("wpmz/template.kml") as f:
            content = f.read().decode('utf-8')
            assert "<wpml:globalShootHeight>100</wpml:globalShootHeight>" in content
            assert name in content
            # Проверка порядка координат в takeOffRefPoint: должно быть lat,lon
            assert "<wpml:takeOffRefPoint>48.000000,19.000000,0.000000</wpml:takeOffRefPoint>" in content

            # Проверяем waylines.wpml
            with z.open("wpmz/waylines.wpml") as f:
                content = f.read().decode('utf-8')
                assert "<wpml:missionConfig>" in content
                assert "<wpml:takeOffRefPoint>48.000000,19.000000,0.000000</wpml:takeOffRefPoint>" in content
                # Проверяем наличие Folder и templateId
                assert "<Folder>" in content
                assert "<wpml:templateId>0</wpml:templateId>" in content


def test_kmz_auto_direction():
    """Проверяет, что угол полета оптимизируется автоматически."""
    field_id = 101
    name = "Horizontal Field"
    # Горизонтальный прямоугольник (вытянут по долготе) -> Ожидаем угол ~90
    wkt = "POLYGON ((19 48, 19.1 48, 19.1 48.01, 19 48.01, 19 48))"
    
    # Передаем direction=None (ожидаем авто-расчет)
    kmz_data = create_kmz(field_id, name, wkt, direction=None)
    
    with zipfile.ZipFile(io.BytesIO(kmz_data)) as z:
        with z.open("wpmz/template.kml") as f:
            content = f.read().decode('utf-8')
            # Ожидаем <wpml:direction>90</wpml:direction> или близко к 90/270/etc.
            # Наш алгоритм возвращает angle % 180, так что 90.
            assert "<wpml:direction>90</wpml:direction>" in content

    # Вертикальный прямоугольник -> Ожидаем угол 0
    name_v = "Vertical Field"
    wkt_v = "POLYGON ((19 48, 19.01 48, 19.01 48.1, 19 48.1, 19 48))"
    kmz_data_v = create_kmz(field_id, name_v, wkt_v, direction=None)
    
    with zipfile.ZipFile(io.BytesIO(kmz_data_v)) as z:
        with z.open("wpmz/template.kml") as f:
            content = f.read().decode('utf-8')
            assert "<wpml:direction>0</wpml:direction>" in content
