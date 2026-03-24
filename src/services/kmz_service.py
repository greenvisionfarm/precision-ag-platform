"""
Сервис для создания KMZ файлов для DJI Pilot 2.
"""
import hashlib
import io
import time
import zipfile
from functools import lru_cache
from typing import Tuple

from shapely import wkt
from shapely.geometry import Polygon


def wkt_to_coords(wkt_str: str) -> str:
    """Преобразует WKT в строку координат lon,lat,alt через пробел.
    
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

    # Формат DJI: lon,lat,alt lon,lat,alt ...
    return " ".join([f"{c[0]},{c[1]},0" for c in coords])


def generate_template_kml(
    field_name: str, 
    wkt_str: str, 
    height: int = 100, 
    overlap_h: int = 80, 
    overlap_w: int = 70, 
    direction: int = 0
) -> str:
    """Генерирует XML содержимое template.kml для DJI Pilot 2.
    
    Args:
        field_name: Имя поля.
        wkt_str: WKT строка геометрии поля.
        height: Высота полета в метрах.
        overlap_h: Фронтальное перекрытие в процентах.
        overlap_w: Боковое перекрытие в процентах.
        direction: Угол курса в градусах.
        
    Returns:
        Строка KML.
    """
    coords_str = wkt_to_coords(wkt_str)

    # Первая точка для TakeOffRefPoint
    coords_list = coords_str.split(' ')
    if not coords_list or not coords_list[0]:
        raise ValueError("Не удалось получить координаты из геометрии поля")
    first_coord = coords_list[0]

    current_time = int(time.time() * 1000)

    xml_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2" xmlns:wpml="http://www.dji.com/wpmz/1.0.6">
  <Document>
    <name>{field_name}</name>
    <wpml:createTime>{current_time}</wpml:createTime>
    <wpml:updateTime>{current_time}</wpml:updateTime>
    <wpml:missionConfig>
      <wpml:flyToWaylineMode>safely</wpml:flyToWaylineMode>
      <wpml:finishAction>goHome</wpml:finishAction>
      <wpml:exitOnRCLost>executeLostAction</wpml:exitOnRCLost>
      <wpml:executeRCLostAction>goBack</wpml:executeRCLostAction>
      <wpml:takeOffSecurityHeight>20</wpml:takeOffSecurityHeight>
      <wpml:takeOffRefPoint>{first_coord}</wpml:takeOffRefPoint>
      <wpml:globalTransitionalSpeed>10</wpml:globalTransitionalSpeed>
      <wpml:droneInfo>
        <wpml:droneEnumValue>77</wpml:droneEnumValue>
        <wpml:droneSubEnumValue>0</wpml:droneSubEnumValue>
      </wpml:droneInfo>
      <wpml:payloadInfo>
        <wpml:payloadEnumValue>68</wpml:payloadEnumValue>
        <wpml:payloadSubEnumValue>3</wpml:payloadSubEnumValue>
        <wpml:payloadPositionIndex>0</wpml:payloadPositionIndex>
      </wpml:payloadInfo>
    </wpml:missionConfig>
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
        <wpml:elevationOptimizeEnable>1</wpml:elevationOptimizeEnable>
        <wpml:shootType>time</wpml:shootType>
        <wpml:direction>{direction}</wpml:direction>
        <wpml:overlap>
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
        <wpml:height>{height}</wpml:height>
      </Placemark>
      <wpml:payloadParam>
        <wpml:payloadPositionIndex>0</wpml:payloadPositionIndex>
        <wpml:imageFormat>visable,narrow_band</wpml:imageFormat>
      </wpml:payloadParam>
    </Folder>
  </Document>
</kml>"""
    return xml_content


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
    direction: int
) -> bytes:
    """Кэшируемая функция генерации KMZ.
    
    Args:
        field_id: ID поля.
        field_name: Имя поля.
        wkt_hash: Хеш WKT для кэширования.
        wkt_str: WKT строка геометрии.
        height: Высота полета.
        overlap_h: Фронтальное перекрытие.
        overlap_w: Боковое перекрытие.
        direction: Угол курса.
        
    Returns:
        Байты KMZ файла.
    """
    template_kml = generate_template_kml(field_name, wkt_str, height, overlap_h, overlap_w, direction)

    # waylines.wpml нужен для DJI Pilot 2
    waylines_wpml = """<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2" xmlns:wpml="http://www.dji.com/wpmz/1.0.6">
  <Document></Document>
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
    direction: int = 0
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
        direction: Угол курса в градусах (по умолчанию 0).
        
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
