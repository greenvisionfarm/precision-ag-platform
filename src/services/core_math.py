import logging
import numpy as np
import pandas as pd
from typing import List, Dict, Optional, Any
from shapely import wkt

logger = logging.getLogger(__name__)

def calculate_index_from_arrays(nir: np.ndarray, red_or_re: np.ndarray) -> float:
    """Чистый расчет индекса из массивов с фильтрацией."""
    # Для DJI Mavic 3M после нормализации значения обычно 0-1
    mask = (nir > 0.01) & (red_or_re > 0.01)
    if not np.any(mask):
        return 0.0
    
    nir_f = nir[mask].astype(np.float32)
    red_f = red_or_re[mask].astype(np.float32)
    
    val = (nir_f - red_f) / (nir_f + red_f + 1e-10)
    return float(np.clip(np.median(val), -1.0, 1.0))

def calculate_vra_redistribution(zones: List[Dict], total_fertilizer_kg: float) -> List[Dict]:
    """
    Математика перераспределения удобрений для 4-х зон.
    Зоны: Очень низкая, Низкая, Средняя, Высокая.
    """
    total_area = sum(z.get('area_raw', 0) for z in zones)
    if total_area == 0:
        return zones

    # Коэффициенты стратегии (Компенсаторная модель)
    multiplier_map = {
        "Очень низкая": 1.25, # +25% к средней норме
        "Низкая": 1.10,       # +10%
        "Средняя": 0.95,      # -5%
        "Высокая": 0.80       # -20% (экономия в зоне насыщения)
    }
    
    # 1. Считаем взвешенную сумму площадей
    weighted_area_sum = sum(z['area_raw'] * multiplier_map.get(z['name'], 1.0) for z in zones)
    
    # 2. Базовая доза на "идеальный" гектар
    base_rate_factor = total_fertilizer_kg / weighted_area_sum
    
    MAX_SAFE_RATE = 500.0 # Ограничение 500 кг/га для безопасности
    
    for z in zones:
        mult = multiplier_map.get(z['name'], 1.0)
        rate = base_rate_factor * mult
        
        # Лимитируем сверху и снизу
        rate = max(0.0, min(rate, MAX_SAFE_RATE))
        z['rate_kg_ha'] = float(rate)
        
    logger.info(f"[MATH] VRA redistribution completed for {len(zones)} zones")
    return zones
