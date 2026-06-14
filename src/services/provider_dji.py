import os
import logging
import rasterio
import numpy as np
from typing import Dict, Any, List, Optional

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
        Пропускает превью _D.JPG — они не содержат мультиспектральных данных.
        """
        file_groups = {}
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

                if base_name.upper().endswith('_D'):
                    continue

                found_channel = None
                for suffix, internal_key in channel_map.items():
                    if base_name.upper().endswith(f'_{suffix}'):
                        prefix = base_name[:-(len(suffix) + 1)]
                        found_channel = internal_key
                        break

                if found_channel:
                    if prefix not in file_groups:
                        file_groups[prefix] = {}
                    file_groups[prefix][found_channel] = os.path.join(root, file)
                else:
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

    @staticmethod
    def parse_ppk_timestamps(mrk_path: str) -> List[Dict[str, Any]]:
        """
        Парсит файл .MRK (DJI Timestamp) с PPK-скорректированными координатами.

        Формат строк (табуляция-разделённые):
        1. shot_number
        2. gps_time (секунды недели)
        3. receiver_info [week]
        4. satellites_north
        5. satellites_east
        6. vdop
        7. lat,Lat
        8. lon,Lon
        9. ellh,Ellh
        10. sigma_north, sigma_east, sigma_up
        11. quality (Q=Fixed, F=Float)

        Возвращает список словарей с ключами: shot, lat, lon, alt, sigma_n, sigma_e, sigma_u, quality
        """
        results = []
        try:
            with open(mrk_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    parts = line.split('\t')
                    if len(parts) < 11:
                        continue

                    shot = int(parts[0])

                    lat = lon = alt = None
                    sigma_n = sigma_e = sigma_u = 0.0
                    quality = ''

                    for p in parts[1:]:
                        p = p.strip()
                        if p.endswith(',Lat'):
                            lat = float(p[:-4])
                        elif p.endswith(',Lon'):
                            lon = float(p[:-4])
                        elif p.endswith(',Ellh'):
                            alt = float(p[:-5])
                        elif ',' in p and p[0].isdigit():
                            sigmas = p.split(',')
                            if len(sigmas) == 3:
                                try:
                                    sigma_n = float(sigmas[0])
                                    sigma_e = float(sigmas[1])
                                    sigma_u = float(sigmas[2])
                                except ValueError:
                                    pass
                        elif p.endswith(',Q') or p.endswith(',F'):
                            quality = p[-1]

                    if lat is not None and lon is not None:
                        results.append({
                            'shot': shot,
                            'lat': lat,
                            'lon': lon,
                            'alt': alt or 0.0,
                            'sigma_n': sigma_n,
                            'sigma_e': sigma_e,
                            'sigma_u': sigma_u,
                            'quality': quality
                        })
        except Exception as e:
            logger.warning(f"Ошибка парсинга .MRK файла: {e}")

        return results

    @staticmethod
    def find_mrk_file(dir_path: str) -> Optional[str]:
        """Ищет файл .MRK (DJI Timestamp) в директории."""
        for root, _, files in os.walk(dir_path):
            for f in files:
                if f.lower().endswith('.mrk'):
                    return os.path.join(root, f)
        return None
