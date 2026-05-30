"""
Сервис для создания KMZ файлов для DJI Pilot 2.
"""
import hashlib
import io
import math
import time
import zipfile
from functools import lru_cache
from typing import Tuple, Optional

from shapely import wkt
from shapely.geometry import Polygon


def calculate_optimal_heading(wkt_str: str) -> int:
    """
    Рассчитывает оптимальный угол полета (в градусах) вдоль самой длинной стороны поля.
    
    Это минимизирует количество разворотов (U-turns), что повышает эффективность миссии.
    """
    try:
        geom = wkt.loads(wkt_str)
        if not isinstance(geom, Polygon):
            return 0
        
        # Находим минимальный ограничивающий прямоугольник (повернутый)
        mrr = geom.minimum_rotated_rectangle
        if not isinstance(mrr, Polygon):
            return 0
            
        coords = list(mrr.exterior.coords)
        max_dist = 0
        best_angle = 0
        
        for i in range(len(coords) - 1):
            p1 = coords[i]
            p2 = coords[i+1]
            dist = math.sqrt((p2[0] - p1[0])**2 + (p2[1] - p1[1])**2)
            
            if dist > max_dist:
                max_dist = dist
                dx = p2[0] - p1[0]
                dy = p2[1] - p1[1]
                
                # Угол от севера по часовой стрелке
                angle_rad = math.atan2(dx, dy)
                angle_deg = math.degrees(angle_rad)
                best_angle = (angle_deg + 360) % 360

        # Возвращаем угол в диапазоне [0, 180), так как для замейки 
        # направление вдоль линии одинаково эффективно в обе стороны.
        return int(best_angle % 180)
    except Exception:
        return 0


def wkt_to_coords(wkt_str: str) -> str:
    """Преобразует WKT в строку координат lon,lat,alt через новую строку.
    
    Args:
        wkt_str: Строка WKT.
        
    Returns:
        Строка координат в формате DJI.
        
    Raises:
        ValueError: Если геометрия не Polygon.
    """
    geom = wkt.loads(wkt_str)
    if not isinstance(geom, Polygon):
        raise ValueError("Только Polygon поддерживается для миссий")

    coords = list(geom.exterior.coords)
    if len(coords) < 4:
        raise ValueError("Некорректная геометрия: полигон должен иметь минимум 4 координаты")

    # Формат DJI: lon,lat,alt (одна точка на строку для лучшей читаемости)
    return "\n                ".join([f"{c[0]:.9f},{c[1]:.9f},0" for c in coords])


def generate_mission_config(takeoff_ref: str, current_time: int) -> str:
    """Генерирует общую конфигурацию миссии для обоих файлов."""
    return f"""<wpml:missionConfig>
      <wpml:flyToWaylineMode>safely</wpml:flyToWaylineMode>
      <wpml:finishAction>goHome</wpml:finishAction>
      <wpml:exitOnRCLost>executeLostAction</wpml:exitOnRCLost>
      <wpml:executeRCLostAction>goBack</wpml:executeRCLostAction>
      <wpml:takeOffSecurityHeight>20</wpml:takeOffSecurityHeight>
      <wpml:takeOffRefPoint>{takeoff_ref}</wpml:takeOffRefPoint>
      <wpml:globalTransitionalSpeed>10</wpml:globalTransitionalSpeed>
      <wpml:droneInfo>
        <wpml:droneEnumValue>77</wpml:droneEnumValue>
        <wpml:droneSubEnumValue>0</wpml:droneSubEnumValue>
      </wpml:droneInfo>
      <wpml:waylineAvoidLimitAreaMode>0</wpml:waylineAvoidLimitAreaMode>
      <wpml:payloadInfo>
        <wpml:payloadEnumValue>68</wpml:payloadEnumValue>
        <wpml:payloadSubEnumValue>3</wpml:payloadSubEnumValue>
        <wpml:payloadPositionIndex>0</wpml:payloadPositionIndex>
      </wpml:payloadInfo>
    </wpml:missionConfig>"""


def generate_template_kml(
    field_name: str, 
    wkt_str: str, 
    height: int = 100, 
    overlap_h: int = 80, 
    overlap_w: int = 70, 
    direction: int = 0
) -> Tuple[str, str]:
    """Генерирует XML содержимое template.kml и takeoff_ref для DJI Pilot 2.
    
    Args:
        field_name: Имя поля.
        wkt_str: WKT строка геометрии поля.
        height: Высота полета в метрах.
        overlap_h: Фронтальное перекрытие в процентах.
        overlap_w: Боковое перекрытие в процентах.
        direction: Угол курса в градусах.
        
    Returns:
        Кортеж (строка KML, строка takeoff_ref).
    """
    coords_str = wkt_to_coords(wkt_str)

    # DJI WPML требует lat,lon,alt для takeOffRefPoint, 
    # но lon,lat,alt для обычных координат KML (Polygon)
    geom = wkt.loads(wkt_str)
    first_p = list(geom.exterior.coords)[0]
    takeoff_ref = f"{first_p[1]:.6f},{first_p[0]:.6f},0.000000"

    current_time = int(time.time() * 1000)
    mission_config = generate_mission_config(takeoff_ref, current_time)

    xml_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2" xmlns:wpml="http://www.dji.com/wpmz/1.0.6">
  <Document>
    <name>{field_name}</name>
    <wpml:createTime>{current_time}</wpml:createTime>
    <wpml:updateTime>{current_time}</wpml:updateTime>
    {mission_config}
    <Folder>
      <wpml:templateType>mapping2d</wpml:templateType>
      <wpml:templateId>0</wpml:templateId>
      <wpml:waylineCoordinateSysParam>
        <wpml:coordinateMode>WGS84</wpml:coordinateMode>
        <wpml:heightMode>relativeToStartPoint</wpml:heightMode>
        <wpml:globalShootHeight>{height}</wpml:globalShootHeight>
      </wpml:waylineCoordinateSysParam>
      <wpml:autoFlightSpeed>7</wpml:autoFlightSpeed>
      <Placemark>
        <name>Waypoint Mission</name>
        <wpml:caliFlightEnable>0</wpml:caliFlightEnable>
        <wpml:elevationOptimizeEnable>1</wpml:elevationOptimizeEnable>
        <wpml:smartObliqueEnable>0</wpml:smartObliqueEnable>
        <wpml:quickOrthoMappingEnable>0</wpml:quickOrthoMappingEnable>
        <wpml:facadeWaylineEnable>0</wpml:facadeWaylineEnable>
        <wpml:isLookAtSceneSet>0</wpml:isLookAtSceneSet>
        <wpml:smartObliqueGimbalPitch>0</wpml:smartObliqueGimbalPitch>
        <wpml:shootType>time</wpml:shootType>
        <wpml:direction>{direction}</wpml:direction>
        <wpml:margin>0</wpml:margin>
        <wpml:efficiencyFlightModeEnable>0</wpml:efficiencyFlightModeEnable>
        <wpml:overlap>
          <wpml:orthoLidarOverlapH>{overlap_h}</wpml:orthoLidarOverlapH>
          <wpml:orthoLidarOverlapW>{overlap_w}</wpml:orthoLidarOverlapW>
          <wpml:orthoCameraOverlapH>{overlap_h}</wpml:orthoCameraOverlapH>
          <wpml:orthoCameraOverlapW>{overlap_w}</wpml:orthoCameraOverlapW>
        </wpml:overlap>
        <Polygon>
          <outerBoundaryIs>
            <LinearRing>
              <coordinates>
                {coords_str}
              </coordinates>
            </LinearRing>
          </outerBoundaryIs>
        </Polygon>
        <wpml:ellipsoidHeight>{height}</wpml:ellipsoidHeight>
        <wpml:height>{height}</wpml:height>
      </Placemark>
      <wpml:payloadParam>
        <wpml:payloadPositionIndex>0</wpml:payloadPositionIndex>
        <wpml:dewarpingEnable>0</wpml:dewarpingEnable>
        <wpml:returnMode>singleReturnFirst</wpml:returnMode>
        <wpml:samplingRate>240000</wpml:samplingRate>
        <wpml:scanningMode>nonRepetitive</wpml:scanningMode>
        <wpml:modelColoringEnable>0</wpml:modelColoringEnable>
        <wpml:imageFormat>visable,narrow_band</wpml:imageFormat>
      </wpml:payloadParam>
    </Folder>
  </Document>
</kml>"""
    return xml_content, takeoff_ref


def _get_cache_key(
    field_id: int, 
    wkt_str: str, 
    height: int, 
    overlap_h: int, 
    overlap_w: int, 
    direction: int
) -> str:
    """Генерирует ключ кэша для параметров KMZ.
    
    Args:
        field_id: ID поля.
        wkt_str: WKT строка геометрии.
        height: Высота полета.
        overlap_h: Фронтальное перекрытие.
        overlap_w: Боковое перекрытие.
        direction: Угол курса.
        
    Returns:
        MD5 хеш ключ кэша.
    """
    key_string = f"{field_id}:{wkt_str}:{height}:{overlap_h}:{overlap_w}:{direction}"
    return hashlib.md5(key_string.encode()).hexdigest()


@lru_cache(maxsize=128)
def _generate_kmz_cached(
    field_id: int,
    field_name: str,
    wkt_hash: str,
    wkt_str: str,
    height: int,
    overlap_h: int,
    overlap_w: int,
    direction: Optional[int]
) -> bytes:
    """Кэшируемая функция генерации KMZ."""
    # Если направление не задано (None), рассчитываем оптимальное
    actual_direction = direction
    if actual_direction is None:
        actual_direction = calculate_optimal_heading(wkt_str)
        
    template_kml, takeoff_ref = generate_template_kml(
        field_name, wkt_str, height, overlap_h, overlap_w, actual_direction
    )
    
    current_time = int(time.time() * 1000)
    mission_config = generate_mission_config(takeoff_ref, current_time)

    # waylines.wpml должен содержать ту же конфигурацию миссии и Folder
    waylines_wpml = f"""<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2" xmlns:wpml="http://www.dji.com/wpmz/1.0.6">
  <Document>
    {mission_config}
    <Folder>
      <wpml:templateId>0</wpml:templateId>
      <wpml:executeHeightMode>relativeToStartPoint</wpml:executeHeightMode>
      <wpml:waylineId>0</wpml:waylineId>
      <wpml:autoFlightSpeed>7</wpml:autoFlightSpeed>
    </Folder>
  </Document>
</kml>"""

    kmz_io = io.BytesIO()
    with zipfile.ZipFile(kmz_io, 'w', zipfile.ZIP_DEFLATED) as kmz:
        kmz.writestr('wpmz/template.kml', template_kml)
        kmz.writestr('wpmz/waylines.wpml', waylines_wpml)

    kmz_io.seek(0)
    return kmz_io.getvalue()


def create_kmz(
    field_id: int, 
    field_name: str, 
    wkt_str: str, 
    height: int = 100, 
    overlap_h: int = 80, 
    overlap_w: int = 70, 
    direction: Optional[int] = None
) -> bytes:
    """Создает KMZ архив в памяти с учетом параметров миссии.
    
    Использует кэширование для повторяющихся запросов.
    
    Args:
        field_id: ID поля.
        field_name: Имя поля.
        wkt_str: WKT строка геометрии поля.
        height: Высота полета в метрах (по умолчанию 100).
        overlap_h: Фронтальное перекрытие в % (по умолчанию 80).
        overlap_w: Боковое перекрытие в % (по умолчанию 70).
        direction: Угол курса в градусах. Если None, рассчитывается автоматически.
        
    Returns:
        Байты KMZ файла.
    """
    # Для кэширования используем хеш WKT + параметры
    wkt_hash = hashlib.md5(wkt_str.encode()).hexdigest()
    
    kmz_data = _generate_kmz_cached(
        field_id=field_id,
        field_name=field_name,
        wkt_hash=wkt_hash,
        wkt_str=wkt_str,
        height=height,
        overlap_h=overlap_h,
        overlap_w=overlap_w,
        direction=direction
    )
    
    return kmz_data


def clear_kmz_cache() -> None:
    """Очищает кэш KMZ. Полезно при обновлении геометрии поля."""
    _generate_kmz_cached.cache_clear()


if __name__ == "__main__":
    # Тестовый запуск
    test_wkt = "POLYGON((18.733 48.205, 18.733 48.206, 18.731 48.206, 18.731 48.205, 18.733 48.205))"
    kmz_data = create_kmz(1, "Test Field", test_wkt)
    with open("test_export.kmz", "wb") as f:
        f.write(kmz_data)
    print("Test KMZ 'test_export.kmz' created.")
