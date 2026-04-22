import os
import re
import logging
import rasterio
import numpy as np
from PIL import Image
from typing import List, Dict, Optional, Any

logger = logging.getLogger(__name__)

class DJIProvider:
    """Провайдер для работы со снимками DJI (Mavic 3M и другие мультиспектральные модели)."""
    
    @staticmethod
    def extract_dji_meta(image_path: str) -> Dict[str, Any]:
        """
        Извлекает расширенные метаданные DJI из XMP (тег 700) и EXIF.
        Включает GPS, BlackLevel, ExposureTime, SensorGain и др.
        """
        meta = {
            "lat": 0.0, "lon": 0.0, "alt": 0.0,
            "BlackLevel": 3200, "ExposureTime": 1.0, "SensorGain": 1.0,
            "SensorSunlight": 0.0, "DroneSensorRadiationCalibrated": False
        }
        
        try:
            # 1. Читаем начало файла как текст для поиска XMP (быстрее чем полноценный парсинг)
            with open(image_path, 'rb') as f:
                header = f.read(256000).decode('latin-1', errors='ignore')
                
                # Поиск GPS (DJI XMP формат)
                gps_m = re.search(r'GpsLatitude="([^"]+)"', header)
                if gps_m: meta["lat"] = float(gps_m.group(1))
                
                gps_m = re.search(r'GpsLongitude="([^"]+)"', header)
                if gps_m: meta["lon"] = float(gps_m.group(1))
                
                gps_m = re.search(r'RelativeAltitude="([^"]+)"', header)
                if gps_m: meta["alt"] = float(gps_m.group(1))

                # Калибровочные теги DJI Mavic 3M
                for tag in ['BlackLevel', 'SensorGain', 'ExposureTime', 'SensorSunlight', 'DroneSensorRadiationCalibrated']:
                    m = re.search(f'{tag}="([^"]+)"', header)
                    if m: 
                        val = m.group(1)
                        if tag == 'DroneSensorRadiationCalibrated':
                            meta[tag] = val.lower() == 'true'
                        else:
                            meta[tag] = float(val)

            # 2. Если XMP пуст, пробуем стандартный EXIF (через PIL)
            if meta["lat"] == 0.0:
                img = Image.open(image_path)
                exif = img._getexif()
                if exif:
                    from PIL.ExifTags import TAGS, GPSTAGS
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
            logger.error(f"Error extracting metadata from {image_path}: {e}")
            
        return meta

    def group_files_by_prefix(self, dir_path: str) -> Dict[str, Dict[str, str]]:
        """
        Группирует файлы DJI по префиксу и каналу.
        Поддерживает форматы: DJI_0001_MS_NIR.TIF, DJI_..._RED.TIF и др.
        """
        file_groups = {}
        # Регулярка для выделения канала: ищем окончание _NIR, _R, _RED, _RE, _G, _GRN и т.д.
        # DJI Mavic 3M использует: _NIR, _R, _RE, _G
        channel_map = {
            'NIR': 'NIR',
            'R': 'RED', 'RED': 'RED',
            'RE': 'RE', 'REG': 'RE',
            'G': 'GRN', 'GRN': 'GRN'
        }
        
        for root, _, files in os.walk(dir_path):
            for file in files:
                if not file.lower().endswith(('.tif', '.tiff', '.jpg')):
                    continue
                
                base_name = file.rsplit('.', 1)[0]
                
                # Пытаемся найти суффикс канала
                found_channel = None
                for suffix, internal_key in channel_map.items():
                    if base_name.upper().endswith(f'_{suffix}'):
                        prefix = base_name[:-(len(suffix) + 1)] # Отрезаем _CHANNEL
                        found_channel = internal_key
                        break
                
                if found_channel:
                    if prefix not in file_groups:
                        file_groups[prefix] = {}
                    file_groups[prefix][found_channel] = os.path.join(root, file)
                else:
                    # Если канал не найден, сохраняем как MAIN (для RGB/JPEG)
                    if base_name not in file_groups:
                        file_groups[base_name] = {}
                    file_groups[base_name]['MAIN'] = os.path.join(root, file)
                    
        return file_groups

    def read_bands_decimated(self, path: str, factor: int = 8) -> np.ndarray:
        """Читает канал в низком разрешении для экономии памяти."""
        with rasterio.open(path) as src:
            return src.read(1, out_shape=(1, src.height // factor, src.width // factor)).astype(float)

    def get_normalized_band(self, path: str, factor: int = 8) -> np.ndarray:
        """
        Читает канал и нормализует его по метаданным DJI (Reflectance).
        Формула: (DN - BlackLevel) / (Exposure * Gain)
        """
        meta = self.extract_dji_meta(path)
        black_level = meta.get('BlackLevel', 3200)
        exposure = meta.get('ExposureTime', 1.0)
        gain = meta.get('SensorGain', 1.0)
        
        raw_data = self.read_bands_decimated(path, factor)
        
        # Нормализация
        normalized = (raw_data - black_level) / (exposure * gain)
        # Ограничиваем снизу 1.0 (epsilon) чтобы избежать нулей и отрицательных значений после вычитания шума
        return np.maximum(normalized, 1.0)
