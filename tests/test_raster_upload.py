"""
Тесты для эндпоинта загрузки растровых файлов /api/raster/upload
"""
import os
import tempfile
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
import rasterio
from peewee import SqliteDatabase

from db import Field, FieldScan, FieldZone, database
from src.handlers.upload_handlers import RasterUploadHandler, process_geotiff_file
from src.models.auth import Company, User, UserRole


@pytest.fixture
def mock_geotiff_file():
    """Создает временный GeoTIFF файл с тестовыми данными NDVI."""
    with tempfile.NamedTemporaryFile(suffix=".tif", delete=False) as tmp:
        path = tmp.name

    # Создаем данные NDVI (диапазон -1.0 до 1.0)
    data = np.zeros((50, 50), dtype=np.float32)
    data[:, :] = 0.5  # Средний NDVI

    # Добавляем немного шума
    data += np.random.normal(0, 0.02, (50, 50))

    # Координаты: запад, юг, восток, север
    transform = rasterio.transform.from_bounds(18.7, 48.1, 18.8, 48.2, 50, 50)

    with rasterio.open(
        path, 'w', driver='GTiff',
        height=50, width=50,
        count=1, dtype='float32',
        crs='EPSG:4326',
        transform=transform
    ) as dst:
        dst.write(data, 1)

    yield path
    
    # Cleanup
    if os.path.exists(path):
        os.remove(path)


@pytest.fixture
def mock_geotiff_bytes(mock_geotiff_file):
    """Возвращает GeoTIFF файл как байты."""
    with open(mock_geotiff_file, 'rb') as f:
        return f.read()


@pytest.fixture
def test_company(test_db):
    """Создает тестовую компанию."""
    company = Company.create(name='Raster Test Co', slug='raster-test-co')
    yield company
    # Cleanup
    with database.atomic():
        User.delete().where(User.company == company).execute()
        Company.delete().where(Company.id == company.id).execute()


@pytest.fixture
def test_user(test_db, test_company):
    """Создает тестового пользователя."""
    user = User.create_user(
        email='raster-test@test.com',
        password='testpassword123',
        company=test_company,
        role=UserRole.OWNER
    )
    yield user
    # Cleanup выполняется автоматически через test_company


@pytest.fixture
def test_field(test_db, test_company):
    """Создает тестовое поле с координатами, пересекающимися с растром."""
    with database.atomic():
        field = Field.create(
            name="Тестовое поле для растра",
            geometry_wkt="POLYGON ((18.72 48.12, 18.78 48.12, 18.78 48.18, 18.72 48.18, 18.72 48.12))",
            properties_json='{"area": 100}',
            company=test_company
        )
    yield field
    # Cleanup
    with database.atomic():
        FieldScan.delete().where(FieldScan.field == field).execute()
        FieldZone.delete().where(FieldZone.field == field).execute()
        Field.delete().where(Field.id == field.id).execute()


class TestProcessGeotiffFile:
    """Тесты для функции process_geotiff_file."""

    def test_process_geotiff_creates_scan_and_task(self, test_db, test_field, mock_geotiff_file):
        """Тест: process_geotiff_file создаёт FieldScan и запускает задачу."""
        import tempfile
        import shutil
        
        # Создаем временную директорию для uploads
        with tempfile.TemporaryDirectory() as upload_dir:
            # Читаем файл как байты
            with open(mock_geotiff_file, 'rb') as f:
                file_bytes = f.read()
            
            # Имитируем request.files
            request_files = {
                'raster_file': [{
                    'filename': 'test_ndvi.tif',
                    'body': file_bytes
                }]
            }
            
            # Мокаем process_geotiff_task чтобы не требовался Redis
            with patch('src.handlers.upload_handlers.process_geotiff_task') as mock_task:
                # Возвращаем мок задачи с ID
                mock_task_instance = MagicMock()
                mock_task_instance.id = 'mock-task-id-123'
                mock_task.return_value = mock_task_instance
                
                # Вызываем функцию
                result = process_geotiff_file(request_files, upload_dir)
            
            # Проверяем результат
            assert 'message' in result
            assert 'task_id' in result
            assert 'field_id' in result
            assert 'scan_id' in result
            assert result['field_id'] == test_field.id
            assert result['task_id'] == 'mock-task-id-123'
            assert 'test_ndvi.tif' in result['message'] or 'NDVI' in result['message']
            
            # Проверяем что FieldScan создан
            scan = FieldScan.get_or_none(FieldScan.id == result['scan_id'])
            assert scan is not None
            assert scan.field.id == test_field.id
            assert scan.filename == 'test_ndvi.tif'
            assert scan.ndvi_min is not None
            assert scan.ndvi_max is not None
            assert scan.ndvi_avg is not None
            assert scan.task_id == 'mock-task-id-123'
            
            # Проверяем что файл сохранен в upload_dir
            assert scan.file_path is not None
            assert os.path.exists(scan.file_path)

    def test_process_geotiff_no_matching_field(self, test_db, mock_geotiff_file):
        """Тест: process_geotiff_file выбрасывает ошибку если нет подходящего поля."""
        import tempfile
        
        # Создаем растр с координатами которые не пересекаются с существующими полями
        with tempfile.NamedTemporaryFile(suffix=".tif", delete=False) as tmp:
            path = tmp.name
        
        # Координаты далеко от существующих полей (например, Москва)
        transform = rasterio.transform.from_bounds(37.5, 55.7, 37.6, 55.8, 50, 50)
        data = np.zeros((50, 50), dtype=np.float32)
        
        with rasterio.open(
            path, 'w', driver='GTiff',
            height=50, width=50,
            count=1, dtype='float32',
            crs='EPSG:4326',
            transform=transform
        ) as dst:
            dst.write(data, 1)
        
        with tempfile.TemporaryDirectory() as upload_dir:
            with open(path, 'rb') as f:
                file_bytes = f.read()
            
            request_files = {
                'raster_file': [{
                    'filename': 'moscow_ndvi.tif',
                    'body': file_bytes
                }]
            }
            
            # Должна быть ошибка что поле не найдено
            with pytest.raises(ValueError, match="Не найдено поле"):
                process_geotiff_file(request_files, upload_dir)
        
        # Cleanup
        if os.path.exists(path):
            os.remove(path)

    def test_process_geotiff_invalid_file(self, test_db, test_field):
        """Тест: process_geotiff_file выбрасывает ошибку для невалидного файла."""
        import tempfile
        
        with tempfile.TemporaryDirectory() as upload_dir:
            # Создаем невалидный файл (не GeoTIFF)
            invalid_content = b"This is not a valid GeoTIFF file"
            
            request_files = {
                'raster_file': [{
                    'filename': 'invalid.txt',
                    'body': invalid_content
                }]
            }
            
            # Должна быть ошибка при открытии файла
            with pytest.raises(Exception):
                process_geotiff_file(request_files, upload_dir)


class TestRasterUploadHandler:
    """Тесты для RasterUploadHandler."""

    def test_raster_upload_requires_auth(self, test_db):
        """Тест: RasterUploadHandler требует авторизацию."""
        import tempfile
        
        # Создаем мок запроса без авторизации
        handler = RasterUploadHandler.__new__(RasterUploadHandler)
        handler.application = MagicMock()
        handler.request = MagicMock()
        handler.request.files = {}
        handler.get_secure_cookie = MagicMock(return_value=None)
        handler.write = MagicMock()
        handler.set_status = MagicMock()
        
        # Вызываем post
        handler.post()
        
        # Проверяем что вернулся 401
        handler.set_status.assert_called_with(401)
        handler.write.assert_called_with({"error": "Требуется авторизация"})

    def test_raster_upload_requires_file(self, test_db, test_user):
        """Тест: RasterUploadHandler требует наличие файла."""
        from src.utils.auth import session_manager
        
        # Создаем токен
        token = session_manager.create_token(test_user)
        
        # Создаем мок запроса с авторизацией но без файла
        handler = RasterUploadHandler.__new__(RasterUploadHandler)
        handler.application = MagicMock()
        handler.request = MagicMock()
        handler.request.files = {}
        handler.get_secure_cookie = MagicMock(return_value=token.encode())
        handler.write = MagicMock()
        handler.set_status = MagicMock()
        
        # Мокаем get_current_user_from_token
        with patch('src.handlers.upload_handlers.get_current_user_from_token', return_value=test_user):
            handler.post()
        
        # Проверяем что вернулся 400
        handler.set_status.assert_called_with(400)
        handler.write.assert_called_with({"error": "Отсутствует файл"})

    def test_raster_upload_success(self, test_db, test_field, test_user, mock_geotiff_bytes):
        """Тест: успешная загрузка растрового файла."""
        import tempfile
        from src.utils.auth import session_manager
        
        # Создаем токен
        token = session_manager.create_token(test_user)
        
        with tempfile.TemporaryDirectory() as upload_dir:
            # Создаем мок запроса
            handler = RasterUploadHandler.__new__(RasterUploadHandler)
            handler.application = MagicMock()
            handler.request = MagicMock()
            handler.request.files = {
                'raster_file': [{
                    'filename': 'success_test.tif',
                    'body': mock_geotiff_bytes
                }]
            }
            handler.get_secure_cookie = MagicMock(return_value=token.encode())
            
            written_data = []
            status_code = []
            
            def mock_write(data):
                written_data.append(data)
            
            def mock_set_status(status):
                status_code.append(status)
            
            handler.write = mock_write
            handler.set_status = mock_set_status
            
            # Мокаем UPLOAD_DIR, get_current_user_from_token и process_geotiff_task
            with patch('src.handlers.upload_handlers.get_current_user_from_token', return_value=test_user):
                with patch('src.handlers.upload_handlers.UPLOAD_DIR', upload_dir):
                    with patch('src.handlers.upload_handlers.process_geotiff_task') as mock_task:
                        mock_task_instance = MagicMock()
                        mock_task_instance.id = 'mock-upload-task-456'
                        mock_task.return_value = mock_task_instance
                        
                        handler.post()
            
            # Проверяем что всё прошло успешно
            assert len(written_data) > 0
            result = written_data[0]
            
            assert 'message' in result
            assert 'task_id' in result
            assert 'field_id' in result
            assert 'scan_id' in result
            assert result['field_id'] == test_field.id
            assert result['task_id'] == 'mock-upload-task-456'
            
            # Проверяем что FieldScan создан
            scan = FieldScan.get_or_none(FieldScan.id == result['scan_id'])
            assert scan is not None
            assert scan.field.id == test_field.id
