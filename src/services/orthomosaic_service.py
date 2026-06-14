"""
Orthomosaic service — склейка дрон-фото в ортомозаику.

Pipeline: DJI RGB JPGs → cv2.Stitcher → georeferencing via EXIF GPS → GeoTIFF
"""
import logging
import os
from dataclasses import dataclass, field
from typing import List, Optional

import cv2
import numpy as np
import rasterio
from rasterio.transform import from_bounds

from src.services.provider_dji import DJIProvider

logger = logging.getLogger(__name__)

MIN_IMAGES = 2

CV2_STITCHER_STATUS = {
    0: "OK",
    1: "ERR_NEED_MORE_IMGS",
    2: "ERR_HOMOGRAPHY_EST_FAIL",
    3: "ERR_CAMERA_PARAMS_ADJUST_FAIL",
}


@dataclass
class ImageGPS:
    path: str
    lat: float
    lon: float
    alt: float


@dataclass
class StitchResult:
    success: bool
    stitched_image: Optional[np.ndarray] = None
    image_width: int = 0
    image_height: int = 0
    gps_data: List[ImageGPS] = field(default_factory=list)
    error: Optional[str] = None


class OrthomosaicService:
    """Сервис склейки дрон-фото в ортомозаику с геореференсированием."""

    def __init__(self):
        self.provider = DJIProvider()
        self.logger = logger

    def _filter_rgb_jpgs(self, file_list: List[str]) -> List[str]:
        """Фильтрует только RGB JPG файлы (_D.JPG), исключая MS TIF."""
        return sorted([
            f for f in file_list
            if f.upper().endswith("_D.JPG") or f.upper().endswith("_D.JPEG")
        ])

    def _extract_gps_for_images(self, image_paths: List[str]) -> List[ImageGPS]:
        """Извлекает GPS координаты из EXIF/DJI метаданных каждого изображения."""
        gps_data = []
        for path in image_paths:
            try:
                meta = self.provider.extract_dji_meta(path)
                if meta["lat"] != 0.0 and meta["lon"] != 0.0:
                    gps_data.append(ImageGPS(
                        path=path,
                        lat=meta["lat"],
                        lon=meta["lon"],
                        alt=meta.get("alt", 0.0),
                    ))
            except Exception as e:
                self.logger.warning(f"Не удалось извлечь GPS из {path}: {e}")
        return gps_data

    def _compute_bounds(self, gps_data: List[ImageGPS]) -> Optional[dict]:
        """Вычисляет географические границы по GPS данным."""
        if not gps_data:
            return None
        lats = [g.lat for g in gps_data]
        lons = [g.lon for g in gps_data]
        return {
            "min_lat": min(lats),
            "max_lat": max(lats),
            "min_lon": min(lons),
            "max_lon": max(lons),
        }

    def _build_geotransform(
        self, bounds: dict, width: int, height: int
    ):
        """Affine transform и CRS из GPS границ и размеров."""
        from pyproj import CRS

        west = bounds["min_lon"]
        south = bounds["min_lat"]
        east = bounds["max_lon"]
        north = bounds["max_lat"]

        transform = from_bounds(west, south, east, north, width, height)
        crs = CRS.from_epsg(4326)
        return transform, crs

    def _save_geotiff(self, image: np.ndarray, bounds: dict, output_path: str) -> None:
        """Сохраняет RGB изображение как геореференсированный GeoTIFF."""
        height, width = image.shape[:2]
        transform, crs = self._build_geotransform(bounds, width, height)

        if image.ndim == 2:
            count = 1
            bands = [image]
        else:
            count = image.shape[2]
            bands = np.moveaxis(image, -1, 0)

        os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)

        with rasterio.open(
            output_path, 'w',
            driver='GTiff',
            height=height,
            width=width,
            count=count,
            dtype='uint8',
            crs=crs,
            transform=transform,
        ) as dst:
            for i, band in enumerate(bands, 1):
                dst.write(band, i)

        self.logger.info(
            f"GeoTIFF сохранён: {output_path} ({width}x{height}, {count} bands)"
        )

    def stitch_images(self, image_paths: List[str]) -> StitchResult:
        """Склеивает изображения через cv2.Stitcher."""
        if len(image_paths) < MIN_IMAGES:
            return StitchResult(
                success=False,
                error=f"Недостаточно изображений для склейки: "
                      f"{len(image_paths)} (минимум {MIN_IMAGES})",
            )

        gps_data = self._extract_gps_for_images(image_paths)
        if len(gps_data) < MIN_IMAGES:
            return StitchResult(
                success=False,
                error=f"Недостаточно изображений с GPS: "
                      f"{len(gps_data)} из {len(image_paths)}",
            )

        self.logger.info(f"Загрузка {len(image_paths)} изображений для склейки...")
        images = []
        for path in image_paths:
            img = cv2.imread(path)
            if img is not None:
                images.append(img)
            else:
                self.logger.warning(f"Не удалось загрузить: {path}")

        if len(images) < MIN_IMAGES:
            return StitchResult(
                success=False,
                error=f"Не удалось загрузить достаточно изображений: {len(images)}",
            )

        self.logger.info(f"Запуск cv2.Stitcher на {len(images)} изображениях...")
        stitcher = cv2.Stitcher_create(cv2.Stitcher_SCANS)
        status, stitched = stitcher.stitch(images)

        if status != 0:
            status_text = CV2_STITCHER_STATUS.get(status, f"UNKNOWN({status})")
            self.logger.error(f"cv2.Stitcher ошибка: {status_text}")
            return StitchResult(
                success=False,
                error=f"Ошибка склейки: {status_text}",
            )

        self.logger.info(f"Склейка успешна: {stitched.shape[1]}x{stitched.shape[0]}")

        return StitchResult(
            success=True,
            stitched_image=stitched,
            image_width=stitched.shape[1],
            image_height=stitched.shape[0],
            gps_data=gps_data,
        )

    def process_directory(self, dir_path: str, output_tif: str) -> StitchResult:
        """
        Полный пайплайн: найти RGB JPGs → склейка → геореференсирование → GeoTIFF.
        """
        all_files = []
        for root, _, files in os.walk(dir_path):
            for f in files:
                all_files.append(f)

        rgb_jpgs = self._filter_rgb_jpgs(all_files)
        self.logger.info(f"Найдено RGB JPG: {len(rgb_jpgs)} из {len(all_files)} файлов")

        if len(rgb_jpgs) < MIN_IMAGES:
            return StitchResult(
                success=False,
                error=f"Недостаточно RGB JPG для склейки: {len(rgb_jpgs)}",
            )

        full_paths = []
        for jpg in rgb_jpgs:
            for root, _, files in os.walk(dir_path):
                if jpg in files:
                    full_paths.append(os.path.join(root, jpg))
                    break

        stitch_result = self.stitch_images(full_paths)
        if not stitch_result.success:
            return stitch_result

        bounds = self._compute_bounds(stitch_result.gps_data)
        if not bounds:
            return StitchResult(
                success=False,
                error="Не удалось определить географические границы",
            )

        self._save_geotiff(stitch_result.stitched_image, bounds, output_tif)

        return stitch_result
