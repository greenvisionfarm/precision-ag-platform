"""
Базовый пайплайн обработки дрон-снимков.
Устраняет дублирование между fast и orthomosaic задачами.
"""
import logging
import os
import shutil
import tempfile
import zipfile
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, Optional

import numpy as np

from src.services.crop_classifier import classify_from_raster
from src.utils.db_utils import db_connection

logger = logging.getLogger(__name__)


class DronePipeline(ABC):
    """Базовый класс пайплина обработки дрон-снимков."""

    source: str = "drone"

    def run(
        self,
        zip_path: str,
        field_id: int,
        total_fertilizer_kg: Optional[float] = None,
        scan_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Запуск полного пайплайна."""
        from db import Field, FieldScan, FieldZone, database
        from src.constants import UPLOAD_DIR

        results: Dict[str, Any] = {"success": False, "error": None}

        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                with zipfile.ZipFile(zip_path, 'r') as zf:
                    zf.extractall(tmpdir)

                with db_connection():
                    field = Field.get_by_id(field_id)
                    field_wkt = field.geometry_wkt

                processing_result = self.process(tmpdir, field_wkt, total_fertilizer_kg)

                zones = processing_result.get("zones", [])
                output_tif = processing_result["output_tif"]
                points = processing_result.get("points", [])

                ts = datetime.now().strftime('%Y%m%d_%H%M%S')
                final_name = f"{self.source}_{field_id}_{ts}.tif"
                final_path = os.path.join(UPLOAD_DIR, final_name)
                os.makedirs(os.path.dirname(final_path), exist_ok=True)
                shutil.copy2(output_tif, final_path)

                crop_result = classify_from_raster(output_tif)
                crop_type = crop_result.get("crop_type")
                crop_confidence = crop_result.get("confidence")

                with db_connection():
                    with database.atomic():
                        scan = FieldScan.get_by_id(scan_id) if scan_id else None
                        if not scan:
                            scan = FieldScan.create(
                                field=field,
                                file_path=final_path,
                                filename=final_name,
                                uploaded_at=datetime.now(),
                                processed='true',
                                source=self.source,
                            )
                        else:
                            scan.file_path = final_path
                            scan.filename = final_name
                            scan.processed = 'true'
                            scan.source = self.source

                        if points:
                            ndvi_vals = [p.ndvi for p in points]
                            scan.ndvi_min = float(np.min(ndvi_vals))
                            scan.ndvi_max = float(np.max(ndvi_vals))
                            scan.ndvi_avg = float(np.mean(ndvi_vals))

                        if crop_type:
                            scan.crop_type = crop_type
                        if crop_confidence is not None:
                            scan.crop_confidence = crop_confidence

                        scan.save()

                        FieldZone.delete().where(FieldZone.scan == scan).execute()
                        for z in zones:
                            FieldZone.create(
                                field=field,
                                scan=scan,
                                name=z['name'],
                                geometry_wkt=z['geometry_wkt'],
                                avg_ndvi=z['avg_ndvi'],
                                color=z['color'],
                                rate_kg_ha=z.get('rate_kg_ha'),
                            )

                results["success"] = True
                results["zones_count"] = len(zones)
                results["scan_id"] = scan.id
                results["crop_type"] = crop_type
                results["crop_confidence"] = crop_confidence
                self._extend_results(results, processing_result)

        except Exception as e:
            logger.error(f"Ошибка в пайплайне {self.source}: {e}", exc_info=True)
            results["error"] = str(e)
            if scan_id:
                self._mark_scan_failed(scan_id)

        if os.path.exists(zip_path):
            os.remove(zip_path)

        return results

    @abstractmethod
    def process(self, tmpdir: str, field_wkt: str, total_fertilizer_kg: Optional[float]) -> Dict[str, Any]:
        """
        Специфичная логика обработки.
        Returns: {"output_tif": str, "zones": list, "points": list, ...}
        """
        ...

    def _extend_results(self, results: Dict, processing_result: Dict) -> None:
        """Расширить results специфичными полями."""

    def _mark_scan_failed(self, scan_id: int):
        from db import FieldScan
        with db_connection():
            FieldScan.update(processed='false').where(FieldScan.id == scan_id).execute()
