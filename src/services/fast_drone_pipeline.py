"""Быстрая обработка дрон-снимков (без ортомозаики)."""
import os
from typing import Any, Dict, Optional

from src.services.drone_pipeline import DronePipeline
from src.services.drone_processing_service import DroneProcessingService


class FastDronePipeline(DronePipeline):
    """Быстрая обработка: NDVI из мультиспектра без склейки."""

    source = "drone_fast"

    def process(self, tmpdir: str, field_wkt: str, total_fertilizer_kg: Optional[float]) -> Dict[str, Any]:
        service = DroneProcessingService()

        points = service.process_directory(tmpdir)
        if not points:
            raise ValueError("Не удалось найти валидные снимки с GPS и мультиспектром")

        temp_tif = os.path.join(tmpdir, "grid_temp.tif")
        zones = service.create_grid_and_zone(points, field_wkt, temp_tif)

        if total_fertilizer_kg:
            zones = service.calculate_vra_rates(zones, total_fertilizer_kg)

        return {
            "output_tif": temp_tif,
            "zones": zones,
            "points": points,
        }
