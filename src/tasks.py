"""
Фоновые задачи Huey для обработки данных.
"""
import logging
import os
from datetime import datetime
from typing import Any, Optional

from huey import RedisHuey

from src.utils.db_utils import db_connection

from src.services.drone_processing_service import DroneProcessingService

# Настройка Huey
redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
huey = RedisHuey('field-mapper', url=redis_url)


@huey.task()
def process_drone_fast_task(
    zip_path: str,
    field_id: int,
    total_fertilizer_kg: Optional[float] = None,
    scan_id: Optional[int] = None
) -> dict:
    """
    Быстрая обработка снимков с дрона без создания ортомозаики.
    """
    import tempfile
    import zipfile
    import shutil
    import numpy as np
    from db import Field, FieldScan, FieldZone, database
    from src.handlers.upload_handlers import UPLOAD_DIR
    
    logging.info(f"Запуск БЫСТРОЙ обработки дрона: {zip_path} для поля ID {field_id}")
    
    results = {"success": False, "error": None}
    service = DroneProcessingService()
    
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            # 1. Распаковка
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(tmpdir)
            
            # 2. Сбор точек (NDVI/NDRE)
            points = service.process_directory(tmpdir)
            if not points:
                raise ValueError("Не удалось найти валидные снимки с GPS и мультиспектром")
            
            with db_connection():
                field = Field.get_by_id(field_id)
                field_wkt = field.geometry_wkt
            
            # 3. Создание сетки и зонирование
            temp_tif = os.path.join(tmpdir, "grid_temp.tif")
            zones = service.create_grid_and_zone(points, field_wkt, temp_tif)
            
            # 4. Расчет VRA если нужно
            if total_fertilizer_kg:
                zones = service.calculate_vra_rates(zones, total_fertilizer_kg)
            
            # 5. Сохранение результатов
            final_tif_name = f"fast_drone_{field_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.tif"
            final_tif_path = os.path.join(UPLOAD_DIR, final_tif_name)
            os.makedirs(os.path.dirname(final_tif_path), exist_ok=True)
            shutil.copy2(temp_tif, final_tif_path)
            
            with db_connection():
                with database.atomic():
                    # Создаем/обновляем скан
                    scan = FieldScan.get_by_id(scan_id) if scan_id else None
                    if not scan:
                        scan = FieldScan.create(
                            field=field,
                            file_path=final_tif_path,
                            filename=final_tif_name,
                            uploaded_at=datetime.now(),
                            processed='true',
                            source='drone_fast'
                        )
                    else:
                        scan.file_path = final_tif_path
                        scan.filename = final_tif_name
                        scan.processed = 'true'
                        scan.source = 'drone_fast'

                    # Расчет общих метрик для скана
                    if points:
                        ndvi_vals = [p.ndvi for p in points]
                        scan.ndvi_min = float(np.min(ndvi_vals))
                        scan.ndvi_max = float(np.max(ndvi_vals))
                        scan.ndvi_avg = float(np.mean(ndvi_vals))
                    
                    scan.save()
                    
                    # Удаляем старые зоны этого скана
                    FieldZone.delete().where(FieldZone.scan == scan).execute()
                    
                    for z in zones:
                        zone_name = z['name']
                        if total_fertilizer_kg and 'rate_kg_ha' in z:
                            zone_name = f"{z['name']} ({z['rate_kg_ha']:.1f} кг/га)"

                        FieldZone.create(
                            field=field,
                            scan=scan,
                            name=zone_name,
                            geometry_wkt=z['geometry_wkt'],
                            avg_ndvi=z['avg_ndvi'],
                            color=z['color']
                        )
            
            results["success"] = True
            results["zones_count"] = len(zones)
            results["scan_id"] = scan.id
            
    except Exception as e:
        logging.error(f"Ошибка в задаче fast_drone: {str(e)}", exc_info=True)
        results["error"] = str(e)
        if scan_id:
            with db_connection():
                FieldScan.update(processed='false').where(FieldScan.id == scan_id).execute()
    
    # Удаляем временный ZIP
    if os.path.exists(zip_path):
        os.remove(zip_path)
        
    return results
