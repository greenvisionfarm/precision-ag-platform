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
