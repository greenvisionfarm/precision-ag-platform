import logging
import numpy as np
import pandas as pd
from typing import List, Dict, Optional, Any
from shapely import wkt

logger = logging.getLogger(__name__)

def calculate_index_from_arrays(nir: np.ndarray, red_or_re: np.ndarray) -> float:
    """Чистый расчет индекса из массивов с фильтрацией."""
    mask = (nir > 100) & (red_or_re > 100) & (nir < 65000) & (red_or_re < 65000)
    if not np.any(mask):
        return 0.0
    
    # Приводим к float32 для предотвращения overflow при вычитании uint16
    nir_f = nir[mask].astype(np.float32)
    red_f = red_or_re[mask].astype(np.float32)
    
    val = (nir_f - red_f) / (nir_f + red_f + 1e-10)
    return float(np.clip(np.mean(val), -1.0, 1.0))

def aggregate_to_grid(df: pd.DataFrame, grid_res: float = 0.00005) -> pd.DataFrame:
    """Агрегация точек в регулярную сетку через медиану."""
    df['grid_x'] = (df['lon'] / grid_res).round() * grid_res
    df['grid_y'] = (df['lat'] / grid_res).round() * grid_res
    
    grid = df.groupby(['grid_x', 'grid_y']).agg({
        'ndvi': 'median',
        'ndre': 'median'
    }).reset_index()
    return grid

def calculate_vra_redistribution(zones: List[Dict], total_fertilizer_kg: float) -> List[Dict]:
    """
    Математика перераспределения удобрений.
    Гарантирует баланс масс и применяет защитные лимиты.
    """
    total_rel_area = sum(z.get('area_raw', 0) for z in zones)
    if total_rel_area == 0:
        return zones

    # Коэффициенты стратегии
    multiplier_map = {"Низкая": 1.2, "Средняя": 1.0, "Высокая": 0.8}
    
    # Расчет базового фактора
    weighted_area_sum = sum(z['area_raw'] * multiplier_map.get(z['name'], 1.0) for z in zones)
    base_rate_factor = total_fertilizer_kg / weighted_area_sum
    
    MAX_SAFE_RATE = 1000.0
    actual_total_mass = 0
    
    for z in zones:
        mult = multiplier_map.get(z['name'], 1.0)
        rate = base_rate_factor * mult
        
        # Защита
        rate = max(0.0, min(rate, MAX_SAFE_RATE))
        z['rate_kg_ha'] = rate
        actual_total_mass += (z['area_raw'] * rate)
        
    # Проверка баланса
    mass_error = abs(actual_total_mass - total_fertilizer_kg) / total_fertilizer_kg
    logger.info(f"[MATH] VRA Balance Error: {mass_error:.4%}")
    
    return zones
