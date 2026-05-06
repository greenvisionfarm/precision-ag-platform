import re
import logging
from typing import Dict, Any, Optional
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS

logger = logging.getLogger(__name__)

class DJIMetadataExtractor:
    """
    Библиотека для извлечения метаданных из мультиспектральных снимков DJI.
    Поддерживает XMP (тег 700) и стандартный EXIF.
    """

    @staticmethod
    def extract(image_path: str) -> Dict[str, Any]:
        """
        Извлекает GPS и калибровочные данные DJI.
        """
        meta = {
            "lat": 0.0, "lon": 0.0, "alt": 0.0,
            "black_level": 3200, "exposure_time": 1.0, "sensor_gain": 1.0,
            "sensor_sunlight": 0.0, "calibrated": False
        }
        
        try:
            # 1. Читаем заголовок для поиска XMP (быстро)
            with open(image_path, 'rb') as f:
                header = f.read(512000).decode('latin-1', errors='ignore')
                
                # Поиск GPS (DJI XMP формат)
                gps_m = re.search(r'GpsLatitude="([^"]+)"', header)
                if gps_m: meta["lat"] = float(gps_m.group(1))
                
                gps_m = re.search(r'GpsLongitude="([^"]+)"', header)
                if gps_m: meta["lon"] = float(gps_m.group(1))
                
                gps_m = re.search(r'RelativeAltitude="([^"]+)"', header)
                if gps_m: meta["alt"] = float(gps_m.group(1))

                # Теги DJI Mavic 3M / P4M
                mapping = {
                    'BlackLevel': 'black_level',
                    'SensorGain': 'sensor_gain',
                    'ExposureTime': 'exposure_time',
                    'SensorSunlight': 'sensor_sunlight',
                    'DroneSensorRadiationCalibrated': 'calibrated'
                }
                
                for xmp_tag, meta_key in mapping.items():
                    m = re.search(f'{xmp_tag}="([^"]+)"', header)
                    if m: 
                        val = m.group(1)
                        if meta_key == 'calibrated':
                            meta[meta_key] = val.lower() == 'true'
                        else:
                            meta[meta_key] = float(val)

            # 2. Фолбэк на стандартный EXIF через PIL
            if meta["lat"] == 0.0:
                with Image.open(image_path) as img:
                    exif = img._getexif()
                    if exif:
                        gps_info = {}
                        for tag, value in exif.items():
                            decoded = TAGS.get(tag, tag)
                            if decoded == "GPSInfo":
                                for t in value:
                                    sub_decoded = GPSTAGS.get(t, t)
                                    gps_info[sub_decoded] = value[t]
                        
                        if gps_info:
                            def _to_deg(v): return float(v[0]) + (float(v[1]) / 60.0) + (float(v[2]) / 3600.0)
                            meta["lat"] = _to_deg(gps_info['GPSLatitude'])
                            if gps_info.get('GPSLatitudeRef') != 'N': meta["lat"] = -meta["lat"]
                            meta["lon"] = _to_deg(gps_info['GPSLongitude'])
                            if gps_info.get('GPSLongitudeRef') != 'E': meta["lon"] = -meta["lon"]
                            meta["alt"] = float(gps_info.get('GPSAltitude', 0.0))

        except Exception as e:
            logger.error(f"Error extracting DJI metadata: {e}")
            
        return meta
