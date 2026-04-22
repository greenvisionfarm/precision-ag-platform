
import os
import numpy as np
from src.services.raster_service import process_ndvi_zones
from shapely.wkt import loads as wkt_loads
from shapely.geometry import MultiPolygon, Polygon

def debug_zoning():
    tif_path = "test_files/NDVI.tif"
    # Геометрия поля (примерная для этого файла)
    field_wkt = "POLYGON ((18.72 48.20, 18.74 48.20, 18.74 48.21, 18.72 48.21, 18.72 48.20))"
    
    print(f"--- Тестирование нового алгоритма на {tif_path} ---")
    
    zones = process_ndvi_zones(tif_path, field_wkt)
    
    total_fragments = 0
    print(f"\nИтого сформировано зон: {len(zones)}")
    
    for i, zone in enumerate(zones):
        geom = wkt_loads(zone['geometry_wkt'])
        
        # Считаем количество отдельных полигонов в каждой зоне
        if isinstance(geom, MultiPolygon):
            fragments = len(geom.geoms)
        elif isinstance(geom, Polygon):
            fragments = 1
        else:
            fragments = 0
            
        total_fragments += fragments
        print(f"Зона {i+1} ({zone['name']}): {fragments} фрагмент(ов), NDVI: {zone['avg_ndvi']:.3f}")

    print(f"\nОБЩЕЕ КОЛИЧЕСТВО ФРАГМЕНТОВ НА КАРТЕ: {total_fragments}")
    
    if total_fragments < 10:
        print("✅ Результат отличный! Карта пригодна для техники.")
    elif total_fragments < 30:
        print("⚠️ Карта допустимая, но есть небольшая фрагментация.")
    else:
        print("❌ Слишком много мелких клочков! Нужно еще усилить сглаживание.")

if __name__ == "__main__":
    debug_zoning()
