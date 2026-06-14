"""
Генератор TaskData.zip по формату ISO 11783 TaskData v3.3.
Формат совместим с Agricon, John Deere TaskData, Claas.

Структура TaskData.zip:
  TASKDATA/
  ├── TASKDATA.xml    (задачи, зоны, гриды, продукты)
  ├── GRD00000.bin    (бинарный грид: 1 байт на ячейку = treatment zone index)
  └── ...
"""
import io
import logging
import math
import struct
import zipfile
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from shapely.geometry import box, Point
from shapely.ops import unary_union
from shapely import wkt as shapely_wkt

logger = logging.getLogger(__name__)

# Вторичная проекция для точных метрических расчетов
try:
    import pyproj
    from shapely.ops import transform as shapely_transform

    def _to_meters(geom, from_crs="EPSG:4326", to_crs="EPSG:3035"):
        proj = pyproj.Transformer.from_crs(from_crs, to_crs, always_xy=True).transform
        return shapely_transform(proj, geom)

    def _to_wgs84(geom, from_crs="EPSG:3035", to_crs="EPSG:4326"):
        proj = pyproj.Transformer.from_crs(from_crs, to_crs, always_xy=True).transform
        return shapely_transform(proj, geom)
except ImportError:
    _to_meters = None
    _to_wgs84 = None


def _generate_grid(
    zones: List[Dict[str, Any]],
    resolution_m: float = 2.0,
) -> Tuple[np.ndarray, Dict[str, float]]:
    """
    Генерирует бинарный грид из зон поля.

    Returns:
        grid: 2D numpy array (rows x cols) с индексами treatment zones
        meta: dict с ключами lat, lon, lat_res, lon_res, cols, rows
    """
    if not zones:
        return np.zeros((1, 1), dtype=np.uint8), {}

    # Собираем все геометрии зон в метрах
    zone_geoms_m = []
    for z in zones:
        geom = shapely_wkt.loads(z["geometry_wkt"])
        if _to_meters:
            geom = _to_meters(geom)
        zone_geoms_m.append(geom)

    # Общий bounding box
    all_geom = unary_union(zone_geoms_m)
    minx, miny, maxx, maxy = all_geom.bounds

    # Размеры грида
    width_m = maxx - minx
    height_m = maxy - miny
    cols = max(1, int(width_m / resolution_m))
    rows = max(1, int(height_m / resolution_m))

    # Создаем грид (0 = нет внесения)
    grid = np.zeros((rows, cols), dtype=np.uint8)

    # Для каждой ячейки определяем зону
    cell_w = (maxx - minx) / cols
    cell_h = (maxy - miny) / rows

    for zone_idx, geom_m in enumerate(zone_geoms_m, 1):
        if zone_idx > 255:
            break  # Ограничение: 1 байт = макс 255 зон

        # Создаем маску для этой зоны
        for row in range(rows):
            cy = maxy - (row + 0.5) * cell_h
            for col in range(cols):
                cx = minx + (col + 0.5) * cell_w
                if geom_m.contains(Point(cx, cy)):
                    grid[row, col] = zone_idx

    # Центр грида в WGS84
    center_x = (minx + maxx) / 2
    center_y = (miny + maxy) / 2
    if _to_wgs84:
        center_pt = _to_wgs84(Point(center_x, center_y))
        lat = center_pt.y
        lon = center_pt.x
    else:
        lat = center_y
        lon = center_x

    # Разрешение в градусах (приблизительно)
    lat_res = resolution_m / 111320.0
    lon_res = resolution_m / (111320.0 * math.cos(math.radians(lat)))

    meta = {
        "lat": lat,
        "lon": lon,
        "lat_res": lat_res,
        "lon_res": lon_res,
        "cols": cols,
        "rows": rows,
    }

    return grid, meta


def _build_taskdata_xml(
    field_name: str,
    field_id: int,
    zones: List[Dict[str, Any]],
    product_name: str,
    grid_meta: Dict[str, float],
    farm_name: str = "",
    timestamp: Optional[str] = None,
    nutrient: str = "nitrogen",
    product_group: str = "mineral",
) -> str:
    """Генерирует TASKDATA.xml по формату ISO 11783 TaskData v3.3."""

    if timestamp is None:
        timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

    task_id = f"TSK{field_id}"
    field_ref = f"PFD{field_id}"
    product_ref = "PDT1"
    farm_ref = "FRM1"
    vpn_ref = "VPN1"
    grid_file = "GRD00000"

    nutrient_labels = {
        "nitrogen": "Azote [kg N/ha]",
        "phosphorus": "Phosphore [kg P/ha]",
        "potassium": "Potassium [kg K/ha]",
    }

    xml_parts = [
        '<?xml version="1.0" encoding="utf-8"?>',
        '<ISO11783_TaskData VersionMajor="3" VersionMinor="3"',
        '  ManagementSoftwareManufacturer="FieldMapper"',
        '  ManagementSoftwareVersion="1.0"',
        '  TaskControllerManufacturer="-"',
        '  TaskControllerVersion="-"',
        '  DataTransferOrigin="1">',
        '',
        f'  <TSK A="{task_id}" B="{field_name}" D="{farm_ref}" E="{field_ref}" G="1">',
    ]

    # Treatment Zone 0 = нет внесения
    xml_parts.append('    <TZN A="0">')
    xml_parts.append(f'      <PDV B="0" C="{product_ref}" E="{vpn_ref}" A="0006" />')
    xml_parts.append('    </TZN>')

    # Остальные зоны
    for idx, zone in enumerate(zones, 1):
        rate = zone.get("rate", 0)
        xml_parts.append(f'    <TZN A="{idx}">')
        xml_parts.append(f'      <PDV B="{rate}" C="{product_ref}" E="{vpn_ref}" A="0006" />')
        xml_parts.append(f'    </TZN>')

    xml_parts.append(f'    <TIM D="1" A="{timestamp}" />')
    xml_parts.append(f'    <PAN A="{product_ref}">')
    xml_parts.append(f'      <ASP D="1" A="{timestamp}" />')
    xml_parts.append(f'    </PAN>')
    xml_parts.append(
        f'    <GRD E="{grid_meta["cols"]}" F="{grid_meta["rows"]}"'
        f' G="{grid_file}" I="1"'
        f' A="{grid_meta["lat"]:.7f}" B="{grid_meta["lon"]:.7f}"'
        f' C="{grid_meta["lat_res"]:.7f}" D="{grid_meta["lon_res"]:.7f}" />'
    )
    xml_parts.append(f'  </TSK>')
    xml_parts.append('')

    # Partfield
    xml_parts.append(f'  <PFD A="{field_ref}" C="{field_name}" D="0" />')

    # Product
    xml_parts.append(f'  <PDT A="{product_ref}" B="{product_name}" />')

    # Farm
    display_farm = farm_name or "My Farm"
    xml_parts.append(f'  <FRM A="{farm_ref}" B="{display_farm}" />')

    # Value Presentation (kg/ha)
    xml_parts.append(f'  <VPN A="{vpn_ref}" B="0" C="0.01" D="0" E="kg/ha" />')

    xml_parts.append('')
    xml_parts.append('</ISO11783_TaskData>')

    return '\n'.join(xml_parts)


def export_taskdata(
    field_id: int,
    output_path: str,
    product_name: Optional[str] = None,
    resolution_m: float = 2.0,
    farm_name: Optional[str] = None,
) -> str:
    """
    Экспортирует зоны поля в формате TaskData.zip (ISO 11783 TaskData v3.3).
    Совместим с Agricon, John Deere TaskData, Claas.

    Args:
        field_id: ID поля
        output_path: Путь для сохранения ZIP
        product_name: Название продукта
        resolution_m: Разрешение грида в метрах
        farm_name: Название фермы

    Returns:
        Путь к созданному ZIP файлу
    """
    from src.models.field import Field, FieldZone, FieldScan
    from src.services.crop_classifier import CROP_PROFILES, CropType

    field = Field.get_by_id(field_id)
    zones_query = list(FieldZone.select().where(FieldZone.field == field))

    if not zones_query:
        raise ValueError(f"Нет зон для поля {field_id}")

    # Определяем продукт
    if not product_name:
        for zone in zones_query:
            if zone.product_name:
                product_name = zone.product_name
                break
    if not product_name:
        product_name = "Аммиачная селитра"

    # Определяем ферму
    if not farm_name:
        farm_name = field.company.name if field.company else "My Farm"

    # Подготавливаем данные зон
    zones_data = []
    for zone in zones_query:
        rate = zone.rate_kg_ha
        if rate is None:
            default_rates = [150, 250, 350]
            if zone.scan and getattr(zone.scan, 'crop_type', None):
                try:
                    crop_enum = CropType(zone.scan.crop_type)
                    if crop_enum in CROP_PROFILES:
                        default_rates = CROP_PROFILES[crop_enum].default_rates
                except (ValueError, KeyError):
                    pass
            if zone.avg_ndvi:
                if zone.avg_ndvi < 0.4:
                    rate = default_rates[0]
                elif zone.avg_ndvi < 0.6:
                    rate = default_rates[1]
                else:
                    rate = default_rates[2]
            else:
                rate = default_rates[1]

        zones_data.append({
            "name": zone.name,
            "geometry_wkt": zone.geometry_wkt,
            "rate": rate,
            "color": zone.color,
        })

    # Генерируем грид
    grid, meta = _generate_grid(zones_data, resolution_m)

    # Генерируем XML
    timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    xml_content = _build_taskdata_xml(
        field_name=field.name or f"Field_{field_id}",
        field_id=field_id,
        zones=zones_data,
        product_name=product_name,
        grid_meta=meta,
        farm_name=farm_name,
        timestamp=timestamp,
    )

    # Упаковываем в ZIP
    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("TASKDATA/TASKDATA.xml", xml_content)
        zf.writestr("TASKDATA/GRD00000.bin", grid.tobytes())

    logger.info(
        f"TaskData экспортирован: {output_path} "
        f"(поле: {field.name}, зон: {len(zones_data)}, грид: {meta['cols']}x{meta['rows']})"
    )
    return output_path
