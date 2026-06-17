"""Обработка дрон-снимков с созданием ортомозаики."""
import os
from typing import Any, Dict, Optional

from src.services.drone_pipeline import DronePipeline
from src.services.drone_processing_service import DroneProcessingService
from src.services.orthomosaic_service import OrthomosaicService


class OrthomosaicPipeline(DronePipeline):
    """Ортомозаика: склейка RGB + NDVI из мультиспектра."""

    source = "drone_orthomosaic"

    def process(self, tmpdir: str, field_wkt: str, total_fertilizer_kg: Optional[float]) -> Dict[str, Any]:
        ortho_service = OrthomosaicService()
        drone_service = DroneProcessingService()

        ortho_tif = os.path.join(tmpdir, "orthomosaic.tif")
        stitch_result = ortho_service.process_directory(tmpdir, ortho_tif)

        if not stitch_result.success:
            raise ValueError(f"Ошибка склейки: {stitch_result.error}")

        points = drone_service.process_directory(tmpdir)

        zones = []
        if points:
            temp_tif = os.path.join(tmpdir, "ndvi_grid.tif")
            zones = drone_service.create_grid_and_zone(points, field_wkt, temp_tif)

            if total_fertilizer_kg:
                zones = drone_service.calculate_vra_rates(zones, total_fertilizer_kg)

        return {
            "output_tif": ortho_tif,
            "zones": zones,
            "points": points,
            "orthomosaic_path": ortho_tif,
        }

    def _extend_results(self, results: Dict, processing_result: Dict) -> None:
        if "orthomosaic_path" in processing_result:
            results["orthomosaic_path"] = processing_result["orthomosaic_path"]
