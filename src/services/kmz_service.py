"""
Сервис для создания KMZ файлов для DJI Pilot 2.
"""
import io
import math
import time
import zipfile
from typing import Tuple, Optional, List

from shapely import wkt
from shapely.geometry import LineString, MultiLineString, Polygon, GeometryCollection, MultiPolygon, Point, MultiPoint


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
    direction: int = 0,
    current_time: int = None
) -> Tuple[str, str]:
    """Генерирует XML содержимое template.kml и takeoff_ref для DJI Pilot 2.
    
    Args:
        field_name: Имя поля.
        wkt_str: WKT строка геометрии поля.
        height: Высота полета в метрах.
        overlap_h: Фронтальное перекрытие в процентах.
        overlap_w: Боковое перекрытие в процентах.
        direction: Угол курса в градусах.
        current_time: Время создания (ms). Если None, берется текущее.
        
    Returns:
        Кортеж (строка KML, строка takeoff_ref).
    """
    coords_str = wkt_to_coords(wkt_str)

    # DJI WPML требует lat,lon,alt для takeOffRefPoint, 
    # но lon,lat,alt для обычных координат KML (Polygon)
    geom = wkt.loads(wkt_str)
    first_p = list(geom.exterior.coords)[0]
    takeoff_ref = f"{first_p[1]:.6f},{first_p[0]:.6f},0.000000"

    if current_time is None:
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


def _extract_coords(geometry) -> List[Tuple[float, float]]:
    """Извлекает координаты из любого типа геометрии."""
    if isinstance(geometry, LineString):
        return list(geometry.coords)
    elif isinstance(geometry, Polygon):
        return list(geometry.exterior.coords)
    elif isinstance(geometry, MultiLineString):
        coords = []
        for sub in geometry.geoms:
            coords.extend(_extract_coords(sub))
        return coords
    elif isinstance(geometry, MultiPolygon):
        coords = []
        for sub in geometry.geoms:
            coords.extend(_extract_coords(sub))
        return coords
    elif isinstance(geometry, GeometryCollection):
        coords = []
        for sub in geometry.geoms:
            coords.extend(_extract_coords(sub))
        return coords
    elif isinstance(geometry, (Point, MultiPoint)):
        return []
    return []


def generate_lawnmower_path(wkt_str: str, height: int, overlap_w: int, angle: int) -> List[Tuple[float, float]]:
    """Генерирует эффективный lawnmower путь внутри полигона."""
    from shapely import affinity
    geom = wkt.loads(wkt_str)
    
    # 1. Поворот полигона
    rotated_geom = affinity.rotate(geom, angle, origin='centroid')
    minx, miny, maxx, maxy = rotated_geom.bounds
    
    # Расчет шага на основе высоты и бокового перекрытия
    # DJI Mavic 3M multispectral: горизонтальный FOV ~47.2°
    camera_fov_rad = math.radians(47.2)
    coverage_m = 2 * height * math.tan(camera_fov_rad / 2)
    spacing_m = coverage_m * (1 - overlap_w / 100)
    
    # Конвертация метров в градусы (приблизительно, широта ~48°)
    # 1° широты ≈ 111км, 1° долготы ≈ 74км → среднее ~92км
    spacing_deg = spacing_m / 92000
    
    path = []
    x = minx
    direction = 1
    while x <= maxx:
        # Создаем линию (галс)
        line = affinity.rotate(
            wkt.loads(f"LINESTRING({x} {miny}, {x} {maxy})"), 
            -angle, origin='centroid'
        )
        
        # Пересечение с полем
        intersection = geom.intersection(line)
        if not intersection.is_empty:
            coords = _extract_coords(intersection)
                
            if coords:
                if direction == 1:
                    path.extend(coords)
                else:
                    path.extend(reversed(coords))
                direction *= -1
        x += spacing_deg
    return path

def _generate_kmz_inner(
    field_id: int,
    field_name: str,
    wkt_str: str,
    height: int,
    overlap_h: int,
    overlap_w: int,
    direction: Optional[int],
    current_time: int
) -> bytes:
    """Внутренняя функция генерации KMZ (без кэширования)."""
    actual_direction = direction
    if actual_direction is None:
        actual_direction = calculate_optimal_heading(wkt_str)
        
    template_kml, takeoff_ref = generate_template_kml(
        field_name, wkt_str, height, overlap_h, overlap_w, actual_direction, current_time
    )
    
    mission_config = generate_mission_config(takeoff_ref, current_time)

    # Генерация waypoints (lawnmower)
    waypoints = generate_lawnmower_path(wkt_str, height, overlap_w, actual_direction)
    
    placemarks = ""
    for i, (lon, lat) in enumerate(waypoints):
        placemarks += f"""
      <Placemark>
        <Point><coordinates>{lon},{lat},{height}</coordinates></Point>
        <wpml:index>{i}</wpml:index>
        <wpml:executeHeight>{height}</wpml:executeHeight>
        <wpml:waypointHeadingParam>
            <wpml:waypointHeadingMode>followWayline</wpml:waypointHeadingMode>
        </wpml:waypointHeadingParam>
      </Placemark>"""

    # Добавляем ActionGroup для запуска съемки (timeLapse)
    action_groups = """
      <wpml:actionGroup>
        <wpml:actionGroupId>0</wpml:actionGroupId>
        <wpml:actionGroupStartIndex>0</wpml:actionGroupStartIndex>
        <wpml:actionGroupEndIndex>999</wpml:actionGroupEndIndex>
        <wpml:actionGroupMode>sequence</wpml:actionGroupMode>
        <wpml:actionTrigger>
            <wpml:actionTriggerType>multipleTiming</wpml:actionTriggerType>
            <wpml:actionTriggerParam>2.0</wpml:actionTriggerParam>
        </wpml:actionTrigger>
        <wpml:action>
            <wpml:actionId>0</wpml:actionId>
            <wpml:actionActuatorFunc>startTimeLapse</wpml:actionActuatorFunc>
        </wpml:action>
      </wpml:actionGroup>"""

    # waylines.wpml должен содержать конфигурацию миссии, Folder и Placemarks (waypoints)
    waylines_wpml = f"""<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2" xmlns:wpml="http://www.dji.com/wpmz/1.0.6">
  <Document>
    {mission_config}
    <Folder>
      <wpml:templateId>0</wpml:templateId>
      <wpml:executeHeightMode>relativeToStartPoint</wpml:executeHeightMode>
      <wpml:waylineId>0</wpml:waylineId>
      <wpml:autoFlightSpeed>7</wpml:autoFlightSpeed>
      {placemarks}
      {action_groups}
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
    current_time = int(time.time() * 1000)
    
    return _generate_kmz_inner(
        field_id=field_id,
        field_name=field_name,
        wkt_str=wkt_str,
        height=height,
        overlap_h=overlap_h,
        overlap_w=overlap_w,
        direction=direction,
        current_time=current_time
    )


def clear_kmz_cache() -> None:
    """Очищает кэш KMZ (noop — кэш был убран из-за stale timestamp)."""
    pass


if __name__ == "__main__":
    # Тестовый запуск
    test_wkt = "POLYGON((18.733 48.205, 18.733 48.206, 18.731 48.206, 18.731 48.205, 18.733 48.205))"
    kmz_data = create_kmz(1, "Test Field", test_wkt)
    with open("test_export.kmz", "wb") as f:
        f.write(kmz_data)
    print("Test KMZ 'test_export.kmz' created.")
