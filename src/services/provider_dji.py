import os
import logging
import rasterio
import numpy as np
from typing import Dict, Any

from dji_drone_meta import DJIMetadataExtractor

logger = logging.getLogger(__name__)

class DJIProvider:
    """Провайдер для работы со снимками DJI (Mavic 3M и другие мультиспектральные модели)."""
    
    @staticmethod
    def extract_dji_meta(image_path: str) -> Dict[str, Any]:
        """
        Использует внешнюю библиотеку dji-drone-meta для извлечения метаданных DJI.
        """
        # Преобразуем ключи из библиотеки в формат, ожидаемый приложением, если нужно.
        # В данном случае библиотека возвращает: black_level, sensor_gain, exposure_time.
        # Приложение ожидало: BlackLevel, SensorGain, ExposureTime.
        raw_meta = DJIMetadataExtractor.extract(image_path)
        
        return {
            "lat": raw_meta["lat"],
            "lon": raw_meta["lon"],
            "alt": raw_meta["alt"],
            "BlackLevel": raw_meta["black_level"],
            "ExposureTime": raw_meta["exposure_time"],
            "SensorGain": raw_meta["sensor_gain"],
            "SensorSunlight": raw_meta["sensor_sunlight"],
            "DroneSensorRadiationCalibrated": raw_meta["calibrated"]
        }

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
