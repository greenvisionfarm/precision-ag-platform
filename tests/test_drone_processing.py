"""
Тесты для сервисов обработки снимков с дрона.
"""
import os
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import numpy as np


class TestExtractGPSFromEXIF:
    """Тесты для извлечения GPS данных из EXIF."""

    def test_extract_gps_success(self):
        """Успешное извлечение GPS координат."""
        from src.services.orthomosaic_service import extract_gps_from_exif, ImageGPS
        
        # Мокаем данные EXIF
        mock_exif = {
            34853: {  # GPSInfo
                1: 'N',  # GPSLatitudeRef
                2: ((50, 1), (27, 1), (0, 1)),  # GPSLatitude: 50°27'0"
                3: 'E',  # GPSLongitudeRef
                4: ((30, 1), (30, 1), (0, 1)),  # GPSLongitude: 30°30'0"
                6: 100,  # GPSAltitude: 100m
            },
            36867: '2024:06:15 10:30:00',  # DateTimeOriginal
        }
        
        with patch('PIL.Image.open') as mock_open:
            mock_img = MagicMock()
            mock_img.__enter__ = Mock(return_value=mock_img)
            mock_img.__exit__ = Mock(return_value=None)
            mock_img._getexif = Mock(return_value=mock_exif)
            mock_open.return_value = mock_img
            
            result = extract_gps_from_exif("test.jpg")
            
            assert result is not None
            assert isinstance(result, ImageGPS)
            # Проверяем что timestamp извлечён
            assert result.timestamp is not None
            assert result.timestamp.year == 2024

    def test_extract_gps_no_exif(self):
        """Изображение без EXIF."""
        from src.services.orthomosaic_service import extract_gps_from_exif
        
        with patch('PIL.Image.open') as mock_open:
            mock_img = MagicMock()
            mock_img.__enter__ = Mock(return_value=mock_img)
            mock_img.__exit__ = Mock(return_value=None)
            mock_img._getexif = Mock(return_value=None)
            mock_open.return_value = mock_img
            
            result = extract_gps_from_exif("test.jpg")
            
            assert result is None

    def test_extract_gps_no_gps_info(self):
        """EXIF есть, но GPSInfo отсутствует."""
        from src.services.orthomosaic_service import extract_gps_from_exif
        
        mock_exif = {
            274: 1,  # Orientation
            36867: '2024:06:15 10:30:00',
        }
        
        with patch('PIL.Image.open') as mock_open:
            mock_img = MagicMock()
            mock_img.__enter__ = Mock(return_value=mock_img)
            mock_img.__exit__ = Mock(return_value=None)
            mock_img._getexif = Mock(return_value=mock_exif)
            mock_open.return_value = mock_img
            
            result = extract_gps_from_exif("test.jpg")
            
            assert result is None


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


class TestOrthomosaicService:
    """Тесты для сервиса ортомозаики."""

    def test_create_orthomosaic_no_images(self):
        """Нет изображений в архиве."""
        from src.services.orthomosaic_service import create_orthomosaic_from_zip
        
        with patch('tempfile.TemporaryDirectory'):
            with patch('zipfile.ZipFile') as mock_zip:
                mock_zip.return_value.__enter__ = Mock(return_value=Mock(namelist=[]))
                mock_zip.return_value.__exit__ = Mock(return_value=None)
                
                result = create_orthomosaic_from_zip("test.zip", "output.tif")
                
                assert result["orthomosaic_created"] is False
                assert result["error"] == "Нет изображений в архиве"

    def test_stitch_images_single(self):
        """Склейка одного изображения."""
        from src.services.orthomosaic_service import stitch_images, ImageGPS
        
        image = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
        gps = [ImageGPS(50.0, 30.0, 100)]
        
        result, transform = stitch_images([image], gps)
        
        assert result.shape == image.shape
        assert transform is None


@pytest.fixture
def sample_drone_images():
    """Фикстура с тестовыми изображениями."""
    images = []
    for i in range(5):
        img = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
        images.append(img)
    return images


class TestIntegration:
    """Интеграционные тесты."""

    @pytest.mark.skip(reason="Требует реальных файлов")
    def test_full_pipeline(self, tmp_path):
        """Полный пайплайн обработки."""
        from src.services.orthomosaic_service import process_drone_imagery
        
        # Создаём тестовый ZIP
        zip_path = tmp_path / "test.zip"
        # TODO: Добавить создание тестовых изображений
        
        result = process_drone_imagery(str(zip_path), field_id=1)
        
        assert result["error"] is None
        assert result["orthomosaic"] is not None
        assert result["zones"] is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
