
import pytest
import os
import numpy as np
from src.services.analysis_service import compare_scans

def test_compare_scans_same_file():
    """Сравнение файла с самим собой должно давать нулевую дельту."""
    tif_path = "test_files/NDVI.tif"
    # Геометрия поля (примерная, покрывающая растр)
    # NDVI.tif обычно в UTM или WGS84. 
    # Для теста используем очень широкую геометрию.
    field_wkt = "POLYGON ((-180 -90, -180 90, 180 90, 180 -90, -180 -90))"
    
    if not os.path.exists(tif_path):
        pytest.skip("Test file NDVI.tif not found")
        
    result = compare_scans(tif_path, tif_path, field_wkt)
    
    assert "error" not in result
    assert pytest.approx(result["delta_avg"], abs=1e-5) == 0
    assert result["improvement_area_pct"] == 0
    assert result["degradation_area_pct"] == 0
    assert result["stable_area_pct"] == 100

def test_compare_scans_difference():
    """Проверка корректности расчета разницы (имитация изменений)."""
    # В реальном тесте мы бы создали два временных тифа, 
    # но здесь мы просто проверяем, что логика не падает на реальном файле
    tif1 = "test_files/NDVI.tif"
    tif2 = "test_files/gsddsm.tif" # Другой файл для создания разницы
    
    field_wkt = "POLYGON ((-180 -90, -180 90, 180 90, 180 -90, -180 -90))"
    
    if not os.path.exists(tif1) or not os.path.exists(tif2):
        pytest.skip("Test files not found")
        
    result = compare_scans(tif1, tif2, field_wkt)
    
    assert "delta_avg" in result
    assert isinstance(result["delta_avg"], float)
    assert "improvement_area_pct" in result
