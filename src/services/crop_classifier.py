"""
Сервис классификации сельскохозяйственных культур.

Определяет тип культуры по:
- NDVI профилю (гистограмма значений)
- Дате съёмки (сезонность)
- Текстуре поля (рядность, паттерн)
"""
import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)


class CropType(Enum):
    """Типы сельскохозяйственных культур."""
    WHEAT = "wheat"  # Пшеница
    CORN = "corn"  # Кукуруза
    SUNFLOWER = "sunflower"  # Подсолнечник
    SOYBEAN = "soybean"  # Соя
    RAPESEED = "rapeseed"  # Рапс
    BARLEY = "barley"  # Ячмень
    OATS = "oats"  # Овёс
    SUGAR_BEET = "sugar_beet"  # Сахарная свёкла
    POTATO = "potato"  # Картофель
    VEGETABLES = "vegetables"  # Овощи
    GRASS = "grass"  # Трава/сено
    UNKNOWN = "unknown"  # Не определено


@dataclass
class CropSignature:
    """Сигнатура культуры для классификации."""
    crop_type: CropType
    ndvi_min: float  # Минимальный NDVI
    ndvi_max: float  # Максимальный NDVI
    ndvi_peak: float  # Пиковый NDVI (сезон)
    peak_month: int  # Месяц пика (1-12)
    texture_pattern: str  # "uniform", "rows", "patchy"
    planting_months: List[int]  # Месяцы посадки
    harvest_months: List[int]  # Месяцы уборки
    default_rates: List[int]  # Дефолтные нормы внесения [Low, Medium, High] в кг/га


# Профили культур (усреднённые данные)
CROP_PROFILES: Dict[CropType, CropSignature] = {
    CropType.WHEAT: CropSignature(
        crop_type=CropType.WHEAT,
        ndvi_min=0.2,
        ndvi_max=0.8,
        ndvi_peak=0.75,
        peak_month=6,
        texture_pattern="uniform",
        planting_months=[9, 10],  # Озимая
        harvest_months=[6, 7],
        default_rates=[120, 180, 240]
    ),
    CropType.CORN: CropSignature(
        crop_type=CropType.CORN,
        ndvi_min=0.3,
        ndvi_max=0.9,
        ndvi_peak=0.85,
        peak_month=7,
        texture_pattern="rows",  # Рядная посадка
        planting_months=[4, 5],
        harvest_months=[9, 10],
        default_rates=[150, 250, 350]
    ),
    CropType.SUNFLOWER: CropSignature(
        crop_type=CropType.SUNFLOWER,
        ndvi_min=0.3,
        ndvi_max=0.7,
        ndvi_peak=0.65,
        peak_month=7,
        texture_pattern="rows",
        planting_months=[4, 5],
        harvest_months=[8, 9],
        default_rates=[80, 120, 160]
    ),
    CropType.SOYBEAN: CropSignature(
        crop_type=CropType.SOYBEAN,
        ndvi_min=0.2,
        ndvi_max=0.6,
        ndvi_peak=0.55,
        peak_month=8,
        texture_pattern="rows",
        planting_months=[5, 6],
        harvest_months=[9, 10],
        default_rates=[40, 60, 80]  # Соя сама фиксирует азот, нормы ниже
    ),
    CropType.RAPESEED: CropSignature(
        crop_type=CropType.RAPESEED,
        ndvi_min=0.3,
        ndvi_max=0.85,
        ndvi_peak=0.8,
        peak_month=5,
        texture_pattern="uniform",
        planting_months=[8, 9],
        harvest_months=[6, 7],
        default_rates=[140, 200, 260]
    ),
    CropType.BARLEY: CropSignature(
        crop_type=CropType.BARLEY,
        ndvi_min=0.2,
        ndvi_max=0.75,
        ndvi_peak=0.7,
        peak_month=6,
        texture_pattern="uniform",
        planting_months=[3, 4],
        harvest_months=[7, 8],
        default_rates=[100, 150, 200]
    ),
    CropType.OATS: CropSignature(
        crop_type=CropType.OATS,
        ndvi_min=0.2,
        ndvi_max=0.7,
        ndvi_peak=0.65,
        peak_month=6,
        texture_pattern="uniform",
        planting_months=[3, 4],
        harvest_months=[7, 8],
        default_rates=[80, 120, 160]
    ),
    CropType.SUGAR_BEET: CropSignature(
        crop_type=CropType.SUGAR_BEET,
        ndvi_min=0.3,
        ndvi_max=0.75,
        ndvi_peak=0.7,
        peak_month=8,
        texture_pattern="rows",
        planting_months=[4, 5],
        harvest_months=[9, 10],
        default_rates=[120, 180, 240]
    ),
    CropType.POTATO: CropSignature(
        crop_type=CropType.POTATO,
        ndvi_min=0.3,
        ndvi_max=0.65,
        ndvi_peak=0.6,
        peak_month=7,
        texture_pattern="rows",
        planting_months=[4, 5],
        harvest_months=[8, 9],
        default_rates=[150, 220, 300]
    ),
    CropType.VEGETABLES: CropSignature(
        crop_type=CropType.VEGETABLES,
        ndvi_min=0.2,
        ndvi_max=0.6,
        ndvi_peak=0.5,
        peak_month=7,
        texture_pattern="patchy",  # Разнородное
        planting_months=[4, 5, 6],
        harvest_months=[7, 8, 9],
        default_rates=[100, 150, 200]
    ),
    CropType.GRASS: CropSignature(
        crop_type=CropType.GRASS,
        ndvi_min=0.3,
        ndvi_max=0.7,
        ndvi_peak=0.6,
        peak_month=6,
        texture_pattern="uniform",
        planting_months=[],  # Многолетняя
        harvest_months=[6, 7, 8],
        default_rates=[60, 100, 140]
    ),
}



def analyze_ndvi_histogram(
    ndvi_values: np.ndarray,
    num_bins: int = 50
) -> Dict[str, float]:
    """
    Анализирует гистограмму NDVI для выявления паттернов культуры.
    
    Args:
        ndvi_values: Массив значений NDVI
        num_bins: Количество бинов гистограммы
        
    Returns:
        Статистика гистограммы
    """
    # Фильтруем невалидные значения
    valid = ndvi_values[(ndvi_values > -1) & (ndvi_values <= 1)]
    
    if len(valid) < 100:
        logger.warning("Недостаточно данных для анализа гистограммы")
        return {"error": "insufficient_data"}
    
    # Гистограмма
    hist, bin_edges = np.histogram(valid, bins=num_bins, range=(-1, 1))
    
    # Статистика
    stats = {
        "mean": float(np.mean(valid)),
        "std": float(np.std(valid)),
        "median": float(np.median(valid)),
        "min": float(np.min(valid)),
        "max": float(np.max(valid)),
        "skewness": float(np.mean(((valid - np.mean(valid)) / np.std(valid)) ** 3)),
        "kurtosis": float(np.mean(((valid - np.mean(valid)) / np.std(valid)) ** 4) - 3),
        "p10": float(np.percentile(valid, 10)),
        "p50": float(np.percentile(valid, 50)),
        "p90": float(np.percentile(valid, 90)),
        "histogram": hist.tolist(),
        "bin_edges": bin_edges.tolist()
    }
    
    # Поиск пиков (модальность распределения)
    from scipy.signal import find_peaks
    
    peaks, properties = find_peaks(hist, height=hist.max() * 0.1, distance=5)
    stats["num_peaks"] = len(peaks)
    stats["peak_positions"] = [float(bin_edges[p]) for p in peaks]
    
    return stats


def analyze_texture(
    image: np.ndarray,
    method: str = "glcm"
) -> Dict[str, float]:
    """
    Анализирует текстуру изображения для определения паттерна посадки.
    
    Args:
        image: Изображение (RGB или NDVI)
        method: Метод анализа ("glcm", "lbp", "simple")
        
    Returns:
        Метрики текстуры
    """
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
    else:
        gray = image
    
    # Нормализуем
    gray = ((gray - gray.min()) / (gray.max() - gray.min()) * 255).astype(np.uint8)
    
    stats = {}
    
    if method == "simple":
        # Простой анализ через вариацию
        stats["variance"] = float(np.var(gray))
        stats["contrast"] = float(gray.max() - gray.min())
        
        # FFT анализ для выявления рядности
        f_transform = np.fft.fft2(gray)
        f_shift = np.fft.fftshift(f_transform)
        magnitude = np.abs(f_shift)
        
        # Анизотропия (направленность)
        h_proj = np.sum(magnitude, axis=0)
        v_proj = np.sum(magnitude, axis=1)
        
        stats["row_pattern"] = float(np.std(h_proj) / (np.std(v_proj) + 1e-6))
        # > 1: горизонтальные ряды, < 1: вертикальные ряды, ~1: нет паттерна
        
    elif method == "glcm":
        try:
            from skimage.feature import graycomatrix, graycoprops
            
            # GLCM матрица
            glcm = graycomatrix(
                gray,
                distances=[5],
                angles=[0, np.pi/4, np.pi/2],
                levels=256,
                symmetric=True,
                normed=True
            )
            
            stats["contrast"] = float(graycoprops(glcm, 'contrast').mean())
            stats["dissimilarity"] = float(graycoprops(glcm, 'dissimilarity').mean())
            stats["homogeneity"] = float(graycoprops(glcm, 'homogeneity').mean())
            stats["energy"] = float(graycoprops(glcm, 'energy').mean())
            stats["correlation"] = float(graycoprops(glcm, 'correlation').mean())
            stats["ASM"] = float(graycoprops(glcm, 'ASM').mean())
            
        except ImportError:
            logger.warning("scikit-image не установлен, используем простой анализ")
            return analyze_texture(image, method="simple")
    
    return stats


def classify_crop(
    ndvi_stats: Dict[str, float],
    texture_stats: Dict[str, float],
    acquisition_date: Optional[datetime] = None,
    region_lat: Optional[float] = None
) -> Tuple[CropType, float, Dict[str, Any]]:
    """
    Классифицирует культуру по NDVI, текстуре и дате.
    
    Args:
        ndvi_stats: Статистика NDVI гистограммы
        texture_stats: Метрики текстуры
        acquisition_date: Дата съёмки
        region_lat: Широта региона (для сезонности)
        
    Returns:
        (тип культуры, уверенность, детали)
    """
    scores: Dict[CropType, float] = {}
    details = {
        "ndvi_score": {},
        "texture_score": {},
        "season_score": {}
    }
    
    month = acquisition_date.month if acquisition_date else None
    
    # 1. Оценка по NDVI профилю
    for crop_type, profile in CROP_PROFILES.items():
        ndvi_score = 1.0
        
        # Проверяем диапазон NDVI
        if ndvi_stats.get("max", 0) < profile.ndvi_min:
            ndvi_score *= 0.3
        if ndvi_stats.get("max", 0) > profile.ndvi_max + 0.1:
            ndvi_score *= 0.5
        
        # Проверяем пиковое значение
        ndvi_peak = ndvi_stats.get("median", 0.5)
        ndvi_diff = abs(ndvi_peak - profile.ndvi_peak)
        ndvi_score *= max(0.1, 1.0 - ndvi_diff)
        
        # Проверяем модальность (uniform vs rows)
        if profile.texture_pattern == "uniform":
            if ndvi_stats.get("std", 0) < 0.15:
                ndvi_score *= 1.2
            else:
                ndvi_score *= 0.8
        elif profile.texture_pattern == "rows":
            if ndvi_stats.get("std", 0) > 0.1:
                ndvi_score *= 1.2
        
        scores[crop_type] = ndvi_score
        details["ndvi_score"][crop_type.value] = ndvi_score
    
    # 2. Оценка по текстуре
    row_pattern = texture_stats.get("row_pattern", 1.0)
    
    for crop_type, profile in CROP_PROFILES.items():
        texture_score = 1.0
        
        if profile.texture_pattern == "rows":
            # Ищем рядный паттерн
            if abs(row_pattern - 1.0) > 0.3:  # Есть направленность
                texture_score *= 1.3
            else:
                texture_score *= 0.7
        elif profile.texture_pattern == "uniform":
            # Ищем однородность
            if abs(row_pattern - 1.0) < 0.2:
                texture_score *= 1.3
            else:
                texture_score *= 0.7
        elif profile.texture_pattern == "patchy":
            # Разнородная текстура
            if texture_stats.get("variance", 0) > 1000:
                texture_score *= 1.3
        
        scores[crop_type] *= texture_score
        details["texture_score"][crop_type.value] = texture_score
    
    # 3. Оценка по сезонности
    if month:
        for crop_type, profile in CROP_PROFILES.items():
            season_score = 1.0
            
            # Пик сезона
            if month == profile.peak_month:
                season_score *= 1.5
            elif month in profile.peak_month + np.array([-1, 1]):
                season_score *= 1.2
            
            # Посадка/уборка
            if month in profile.planting_months or month in profile.harvest_months:
                season_score *= 1.1
            
            # Не в сезон
            months_growing = list(range(
                min(profile.planting_months or [1]),
                max(profile.harvest_months or [12]) + 1
            ))
            if month not in months_growing and months_growing:
                season_score *= 0.5
            
            scores[crop_type] *= season_score
            details["season_score"][crop_type.value] = season_score
    
    # Нормализуем_scores
    total = sum(scores.values())
    if total > 0:
        for crop_type in scores:
            scores[crop_type] /= total
    
    # Выбираем лучший
    best_crop = max(scores, key=scores.get)
    confidence = scores[best_crop]
    
    # Добавляем дефолтные нормы для лучшей культуры
    details["default_rates"] = CROP_PROFILES[best_crop].default_rates
    
    # Топ-3 кандидатов
    sorted_crops = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    details["top_candidates"] = [
        {"crop": c.value, "score": float(s)} for c, s in sorted_crops[:3]
    ]
    
    return best_crop, confidence, details


def classify_from_raster(
    raster_path: str,
    acquisition_date: Optional[datetime] = None,
    region_lat: float = 48.0
) -> Dict[str, Any]:
    """
    Классифицирует культуру по растровому файлу (NDVI или ортомозаика).

    Args:
        raster_path: Путь к файлу растра (.tif)
        acquisition_date: Дата съёмки
        region_lat: Широта региона

    Returns:
        Результаты классификации
    """
    import rasterio
    import os

    results = {
        "crop_type": None,
        "confidence": 0.0,
        "details": {},
        "error": None
    }

    try:
        if not os.path.exists(raster_path):
            results["error"] = f"Файл не найден: {raster_path}"
            return results

        # Читаем растр с использованием даунсемплинга для экономии памяти
        import rasterio
        from rasterio.enums import Resampling
        
        with rasterio.open(raster_path) as src:
            num_channels = src.count
            
            # Определяем размер для анализа (не более 1024 пикселей по большой стороне)
            scale_factor = max(src.width, src.height) / 1024.0
            if scale_factor < 1.0:
                scale_factor = 1.0
                
            out_width = int(src.width / scale_factor)
            out_height = int(src.height / scale_factor)
            out_shape = (out_height, out_width)

            # Читаем данные для NDVI анализа (уменьшенная копия)
            if num_channels == 1:
                # Обычный NDVI растр
                data = src.read(
                    1, 
                    out_shape=out_shape, 
                    resampling=Resampling.average
                )
                ndvi_values = data.flatten()
                texture_img = data
            elif num_channels >= 4:
                # RGBN ортомозаика
                try:
                    nir = src.read(4, out_shape=out_shape, resampling=Resampling.average)
                    red = src.read(1, out_shape=out_shape, resampling=Resampling.average)
                    ndvi = (nir.astype(float) - red.astype(float)) / (nir + red + 1e-6)
                    ndvi_values = ndvi.flatten()
                    texture_img = src.read([1, 2, 3], out_shape=(3, out_height, out_width), resampling=Resampling.average).transpose(1, 2, 0)
                except:
                    rgb = src.read([1, 2, 3], out_shape=(3, out_height, out_width), resampling=Resampling.average).transpose(1, 2, 0)
                    ndvi_values = rgb[:, :, 1].flatten() / 255.0
                    texture_img = rgb
            else:
                rgb = src.read([1, 2, 3], out_shape=(3, out_height, out_width), resampling=Resampling.average).transpose(1, 2, 0)
                ndvi_values = rgb[:, :, 1].flatten() / 255.0
                texture_img = rgb

        # 1. Анализируем гистограмму NDVI
        ndvi_stats = analyze_ndvi_histogram(ndvi_values)
        if "error" in ndvi_stats:
            results["error"] = ndvi_stats["error"]
            return results

        # 2. Анализируем текстуру
        texture_stats = analyze_texture(texture_img, method="simple")

        # 3. Классифицируем
        crop_type, confidence, details = classify_crop(
            ndvi_stats,
            texture_stats,
            acquisition_date,
            region_lat
        )

        results.update({
            "crop_type": crop_type.value,
            "confidence": float(confidence),
            "details": details,
            "ndvi_stats": {
                k: v for k, v in ndvi_stats.items()
                if k not in ["histogram", "bin_edges"]
            }
        })
        
        logger.info(f"Классификация растра: {crop_type.value} (уверенность: {confidence:.2%})")

    except Exception as e:
        logger.error(f"Ошибка классификации растра {raster_path}: {e}", exc_info=True)
        results["error"] = str(e)

    return results


def classify_from_orthomosaic(
    orthomosaic_path: str,
    acquisition_date: Optional[datetime] = None,
    region_lat: float = 48.0
) -> Dict[str, Any]:
    """
    Классифицирует культуру по ортомозаике (алиас для classify_from_raster).
    """
    return classify_from_raster(orthomosaic_path, acquisition_date, region_lat)


# Импорт для texture analysis
try:
    import cv2
except ImportError:
    logger.warning("OpenCV не установлен, анализ текстуры ограничен")
    cv2 = None
