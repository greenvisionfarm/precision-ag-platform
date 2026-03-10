import os
import zipfile
import io
import time
from shapely import wkt
from shapely.geometry import Polygon

def wkt_to_coords(wkt_str):
    """Преобразует WKT в список координат [lon, lat, alt] для KML."""
    geom = wkt.loads(wkt_str)
    if not isinstance(geom, Polygon):
        raise ValueError("Только Polygon поддерживается для миссий")
    
    # Координаты внешнего кольца
    coords = list(geom.exterior.coords)
    # DJI ожидает формат: lon,lat,alt (alt=0)
    return "\n".join([f"{c[0]},{c[1]},0" for c in coords])

def generate_template_kml(field_name, wkt_str, height=100, overlap_h=80, overlap_w=70):
    """Генерирует XML содержимое template.kml для DJI Pilot 2."""
    coords_str = wkt_to_coords(wkt_str)
    # Берем первую точку как точку взлета (упрощение)
    takeoff_point = wkt_to_coords(wkt_str).split('\n')[0]
    
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
      <wpml:takeOffSecurityHeight>20</wpml:takeOffSecurityHeight>
      <wpml:takeOffRefPoint>{takeoff_point}</wpml:takeOffRefPoint>
      <wpml:globalTransitionalSpeed>10</wpml:globalTransitionalSpeed>
      <wpml:droneInfo>
        <wpml:droneEnumValue>77</wpml:droneEnumValue>
        <wpml:droneSubEnumValue>0</wpml:droneSubEnumValue>
      </wpml:droneInfo>
    </wpml:missionConfig>
    <Folder>
      <wpml:templateType>mapping2d</wpml:templateType>
      <wpml:templateId>0</wpml:templateId>
      <wpml:autoFlightSpeed>5</wpml:autoFlightSpeed>
      <Placemark>
        <wpml:shootType>time</wpml:shootType>
        <wpml:overlap>
          <wpml:orthoCameraOverlapH>{overlap_h}</wpml:orthoCameraOverlapH>
          <wpml:orthoCameraOverlapW>{overlap_w}</wpml:orthoCameraOverlapW>
        </wpml:overlap>
        <wpml:globalShootHeight>{height}</wpml:globalShootHeight>
        <Polygon>
          <outerBoundaryIs>
            <LinearRing>
              <coordinates>
{coords_str}
              </coordinates>
            </LinearRing>
          </outerBoundaryIs>
        </Polygon>
      </Placemark>
    </Folder>
  </Document>
</kml>"""
    return xml_content

def create_kmz(field_id, field_name, wkt_str, height=100, overlap_h=80, overlap_w=70, speed=10):
    """Создает KMZ архив в памяти с учетом параметров миссии."""
    template_kml = generate_template_kml(field_name, wkt_str, height, overlap_h, overlap_w)
    
    # waypoint.kml может быть пустым для mapping2d шаблонов, но он должен быть в архиве
    waypoint_kml = """<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2" xmlns:wpml="http://www.dji.com/wpmz/1.0.6">
  <Document></Document>
</kml>"""

    kmz_io = io.BytesIO()
    with zipfile.ZipFile(kmz_io, 'w', zipfile.ZIP_DEFLATED) as kmz:
        kmz.writestr('wpmz/template.kml', template_kml)
        kmz.writestr('wpmz/waypoint.kml', waypoint_kml)
    
    kmz_io.seek(0)
    return kmz_io.getvalue()

if __name__ == "__main__":
    # Тестовый запуск
    test_wkt = "POLYGON((18.733 48.205, 18.733 48.206, 18.731 48.206, 18.731 48.205, 18.733 48.205))"
    kmz_data = create_kmz(1, "Test Field", test_wkt)
    with open("test_export.kmz", "wb") as f:
        f.write(kmz_data)
    print("Test KMZ 'test_export.kmz' created.")
