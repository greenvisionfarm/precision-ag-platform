"""
Общий модуль для расчёта нормы внесения (rate) по NDVI и культуре.
Используется в isoxml_service и taskdata_service.
"""
from typing import Optional


def resolve_zone_rate(
    rate_kg_ha: Optional[float],
    avg_ndvi: Optional[float],
    crop_type: Optional[str] = None,
    default_rates: Optional[list] = None,
) -> float:
    """
    Определяет норму внесения для зоны.

    Логика:
    1. Если rate_kg_ha задан — используем его.
    2. Иначе определяем default_rates по культуре.
    3. Выбираем rate по уровню NDVI (<0.4, <0.6, >=0.6).

    Args:
        rate_kg_ha: Явная норма из зоны (может быть None)
        avg_ndvi: Средний NDVI зоны
        crop_type: Тип культуры (строка, ключ из CropType enum)
        default_rates: Список из 3 значений [низкий, средний, высокий NDVI]

    Returns:
        Норма внесения в кг/га
    """
    if rate_kg_ha is not None:
        return rate_kg_ha

    if default_rates is None:
        default_rates = [150, 250, 350]

    if crop_type:
        try:
            from src.services.crop_classifier import CROP_PROFILES, CropType
            crop_enum = CropType(crop_type)
            if crop_enum in CROP_PROFILES:
                default_rates = CROP_PROFILES[crop_enum].default_rates
        except (ValueError, KeyError):
            pass

    if avg_ndvi is not None:
        if avg_ndvi < 0.4:
            return default_rates[0]
        elif avg_ndvi < 0.6:
            return default_rates[1]
        else:
            return default_rates[2]

    return default_rates[1]
