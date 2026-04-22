"""
Тесты для сервисов обработки снимков с дрона.
"""
import os
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import numpy as np


class TestCropClassification:
    """Тесты для классификации культур."""

    def test_classify_wheat(self):
        """Классификация пшеницы."""
        from src.services.crop_classifier import classify_crop, CropType
        
        # NDVI статистика для пшеницы (пик в июне)
        ndvi_stats = {
            "mean": 0.65,
            "median": 0.7,
            "std": 0.12,
            "max": 0.8,
            "min": 0.3,
        }
        
        texture_stats = {
            "variance": 500,
            "row_pattern": 1.05,  # Однородное поле
        }
        
        acquisition_date = datetime(2024, 6, 15)
        
        crop_type, confidence, details = classify_crop(
            ndvi_stats, texture_stats, acquisition_date
        )
        
        # Пшеница должна быть в топ-кандидатах
        assert crop_type == CropType.WHEAT
        top_candidates = [c["crop"] for c in details.get("top_candidates", [])]
        assert "wheat" in top_candidates

    def test_classify_corn(self):
        """Классификация кукурузы."""
        from src.services.crop_classifier import classify_crop, CropType
        
        # NDVI статистика для кукурузы (высокий NDVI)
        ndvi_stats = {
            "mean": 0.75,
            "median": 0.8,
            "std": 0.15,
            "max": 0.9,
            "min": 0.4,
        }
        
        texture_stats = {
            "variance": 1200,
            "row_pattern": 1.5,  # Выраженная рядность
        }
        
        acquisition_date = datetime(2024, 7, 20)
        
        crop_type, confidence, details = classify_crop(
            ndvi_stats, texture_stats, acquisition_date
        )
        
        # Кукуруза должна быть в топ-кандидатах
        assert crop_type == CropType.CORN
        top_candidates = [c["crop"] for c in details.get("top_candidates", [])]
        assert "corn" in top_candidates

    def test_classify_soybean(self):
        """Классификация сои (низкий NDVI)."""
        from src.services.crop_classifier import classify_crop, CropType
        
        ndvi_stats = {
            "mean": 0.45,
            "median": 0.5,
            "std": 0.1,
            "max": 0.6,
            "min": 0.2,
        }
        
        texture_stats = {
            "variance": 800,
            "row_pattern": 1.3,
        }
        
        acquisition_date = datetime(2024, 8, 10)
        
        crop_type, confidence, details = classify_crop(
            ndvi_stats, texture_stats, acquisition_date
        )
        
        assert crop_type == CropType.SOYBEAN


class TestNDVIHistogramAnalysis:
    """Тесты для анализа гистограммы NDVI."""

    def test_histogram_stats(self):
        """Статистика гистограммы."""
        from src.services.crop_classifier import analyze_ndvi_histogram
        
        # Генерируем нормальное распределение NDVI
        np.random.seed(42)
        ndvi_values = np.random.normal(0.6, 0.15, 10000)
        ndvi_values = np.clip(ndvi_values, -1, 1)
        
        stats = analyze_ndvi_histogram(ndvi_values)
        
        assert "mean" in stats
        assert "std" in stats
        assert "median" in stats
        assert "skewness" in stats
        assert abs(stats["mean"] - 0.6) < 0.05
        assert abs(stats["median"] - 0.6) < 0.05

    def test_histogram_insufficient_data(self):
        """Недостаточно данных."""
        from src.services.crop_classifier import analyze_ndvi_histogram
        
        ndvi_values = np.array([0.5, 0.6, 0.7])
        
        stats = analyze_ndvi_histogram(ndvi_values)
        
        assert "error" in stats
        assert stats["error"] == "insufficient_data"


class TestTextureAnalysis:
    """Тесты для анализа текстуры."""

    def test_texture_simple(self):
        """Простой анализ текстуры."""
        from src.services.crop_classifier import analyze_texture
        
        # Создаём тестовое изображение с рядным паттерном
        image = np.zeros((100, 100, 3), dtype=np.uint8)
        image[::10, :] = [255, 0, 0]  # Горизонтальные ряды
        
        stats = analyze_texture(image, method="simple")
        
        assert "variance" in stats
        assert "contrast" in stats
        assert "row_pattern" in stats


class TestDJIProvider:
    """Тесты для DJIProvider."""

    def test_extract_dji_meta_mock(self):
        """Тест извлечения метаданных DJI через моки."""
        from src.services.provider_dji import DJIProvider
        
        provider = DJIProvider()
        mock_content = (
            'DroneSensorRadiationCalibrated="true" '
            'BlackLevel="3200" '
            'ExposureTime="0.005" '
            'SensorGain="2.5" '
            'GpsLatitude="48.8584" '
            'GpsLongitude="2.2945" '
            'RelativeAltitude="120.5"'
        ).encode('latin-1')
        
        with patch('builtins.open', MagicMock(return_value=MagicMock(__enter__=MagicMock(return_value=MagicMock(read=Mock(return_value=mock_content)))))):
            meta = provider.extract_dji_meta("fake_path.tif")
            
            assert meta["DroneSensorRadiationCalibrated"] is True
            assert meta["BlackLevel"] == 3200.0
            assert meta["ExposureTime"] == 0.005
            assert meta["SensorGain"] == 2.5
            assert meta["lat"] == 48.8584
            assert meta["lon"] == 2.2945
            assert meta["alt"] == 120.5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
