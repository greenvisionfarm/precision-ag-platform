"""
Handlers для загрузки и обработки снимков с дрона.

Поддерживает:
- Загрузку ZIP архива со снимками (JPEG/TIFF)
- Быструю обработку NDVI на основе GPS-точек (grid-based)
- Автоматическое определение поля по координатам
"""
import json
import logging
import os
import shutil
import tempfile
import uuid
from datetime import datetime
from typing import Optional

from src.constants import UPLOAD_DIR
from src.middleware.auth import AuthenticatedRequestHandler
from src.models.field import Field, FieldScan
from src.tasks import process_drone_fast_task, process_orthomosaic_task
from src.utils.db_utils import db_connection

logger = logging.getLogger(__name__)

CHUNK_SIZE = 1024 * 1024


class DroneUploadHandler(AuthenticatedRequestHandler):
    """Handler для загрузки снимков с дрона (ZIP архив).

    Использует stream_request_body для потоковой загрузки больших файлов
    прямо на диск, избегая буферизации всего тела запроса в памяти.
    """

    _stream_request_body = True

    def initialize(self):
        super().initialize()
        self._upload_tmpfile = tempfile.NamedTemporaryFile(
            dir=UPLOAD_DIR, delete=False, suffix=".upload"
        )
        self._upload_size = 0

    def data_received(self, chunk: bytes) -> None:
        self._upload_tmpfile.write(chunk)
        self._upload_size += len(chunk)
        if self._upload_size % (50 * 1024 * 1024) < len(chunk):
            logger.info(f"Drone upload: {self._upload_size / 1024 / 1024:.0f} MB received")

    def _parse_multipart(self) -> tuple:
        """Парсит multipart/form-data из временного файла.

        Возвращает (uploaded_filename, form_data, drone_file_path).
        """
        self._upload_tmpfile.close()
        tmpfile_path = self._upload_tmpfile.name

        try:
            content_type = self.request.headers.get("Content-Type", "")
            if "boundary=" not in content_type:
                raise ValueError("Нет boundary в Content-Type")

            boundary = content_type.split("boundary=")[-1].strip().encode()
            boundary_marker = b"--" + boundary
            boundary_end = b"--" + boundary + b"--"

            uploaded_filename = None
            form_data = {}
            drone_body_start = None

            with open(tmpfile_path, "rb") as f:
                f.seek(0, 2)
                file_size = f.tell()

                # 1. Читаем начало файла для парсинга всех полей
                header_size = min(256 * 1024, file_size)
                f.seek(0)
                header_chunk = f.read(header_size)

                # Ищем все boundaries и парсим заголовки каждого поля
                pos = 0
                while True:
                    bpos = header_chunk.find(boundary_marker, pos)
                    if bpos == -1:
                        break

                    sep = header_chunk.find(b"\r\n\r\n", bpos)
                    if sep == -1:
                        break

                    headers_text = header_chunk[bpos:sep].decode("utf-8", errors="replace")
                    body_start = sep + 4

                    if 'name="data"' in headers_text:
                        # data поле — маленькое, ищем boundary после него
                        data_end = header_chunk.find(boundary_marker, body_start)
                        if data_end != -1:
                            data_body = header_chunk[body_start:data_end]
                            if data_body.endswith(b"\r\n"):
                                data_body = data_body[:-2]
                            try:
                                form_data = json.loads(data_body)
                            except Exception:
                                pass

                    elif 'name="drone_images"' in headers_text:
                        for line in headers_text.split("\r\n"):
                            if "filename=" in line:
                                for token in line.split(";"):
                                    token = token.strip()
                                    if token.startswith("filename="):
                                        uploaded_filename = token.split("=", 1)[1].strip().strip('"')
                                        break
                        drone_body_start = body_start

                    pos = sep + 4

                # 2. Читаем хвост файла для boundary_end
                tail_size = min(64 * 1024, file_size)
                f.seek(file_size - tail_size)
                tail = f.read()

                tail_end_pos = tail.rfind(boundary_end)
                if tail_end_pos == -1:
                    raise ValueError("Не найден boundary_end в multipart")

                drone_body_end = file_size - tail_size + tail_end_pos
                if drone_body_end > 0:
                    f.seek(drone_body_end - 2)
                    pre_end = f.read(2)
                    if pre_end == b"\r\n":
                        drone_body_end -= 2

                # 3. Копируем тело drone_images
                if drone_body_start is not None and uploaded_filename:
                    file_ext = os.path.splitext(uploaded_filename)[1] or ".zip"
                    unique_filename = f"drone_{uuid.uuid4()}{file_ext}"
                    drone_file_path = os.path.join(UPLOAD_DIR, unique_filename)

                    f.seek(drone_body_start)
                    bytes_to_copy = drone_body_end - drone_body_start
                    with open(drone_file_path, "wb") as out_f:
                        remaining = bytes_to_copy
                        while remaining > 0:
                            read_size = min(CHUNK_SIZE, remaining)
                            chunk = f.read(read_size)
                            if not chunk:
                                break
                            out_f.write(chunk)
                            remaining -= len(chunk)

            return uploaded_filename, form_data, drone_file_path

        except Exception:
            # Чистим temp file при ошибке
            try:
                os.unlink(tmpfile_path)
            except OSError:
                pass
            raise

    def post(self) -> None:
        """
        Загружает ZIP архив со снимками для обработки.

        Body параметры (в JSON поле 'data'):
            - field_id: ID поля (опционально, если не указано — авто-определение по GPS)
            - crop_type: Тип культуры (опционально)
            - total_fertilizer_kg: Общая масса удобрений для расчета VRA
            - processing_mode: 'fast' (по умолчанию) или 'orthomosaic'
        """
        tmpfile_path = self._upload_tmpfile.name
        try:
            logger.info(f"Drone upload post() started, total received: {self._upload_size / 1024 / 1024:.0f} MB")
            uploaded_filename, form_data, zip_path = self._parse_multipart()

            if zip_path is None:
                self.set_status(400)
                self.write({"error": "Нет файла. Используйте поле 'drone_images'"})
                return

            # Чистим temp file
            try:
                os.unlink(tmpfile_path)
            except OSError:
                pass

            field_id = form_data.get("field_id")
            crop_type = form_data.get("crop_type", "auto")
            total_fertilizer_kg = form_data.get("total_fertilizer_kg")
            processing_mode = form_data.get("processing_mode", "fast")

            file_size = os.path.getsize(zip_path)
            logger.info(f"Загружен архив для быстрой обработки: {uploaded_filename}, {file_size} байт")

            # Если field_id не указан — пытаемся определить по GPS из первого снимка
            if not field_id:
                field_id = self._detect_field_from_gps(zip_path)
                if not field_id:
                    # os.remove(zip_path)  # Временно отключено для отладки
                    self.set_status(400)
                    self.write({
                        "error": "Не удалось определить поле по GPS. Укажите field_id явно"
                    })
                    return
                logger.info(f"Поле определено по GPS: {field_id}")

            # Проверяем существование поля
            try:
                with db_connection():
                    field = Field.get_by_id(field_id)
            except Field.DoesNotExist:
                os.remove(zip_path)
                self.set_status(404)
                self.write({"error": f"Поле {field_id} не найдено"})
                return

            # 1. Создаём запись скана (status: pending)
            scan_source = 'drone_orthomosaic' if processing_mode == 'orthomosaic' else 'drone_fast'
            with db_connection():
                scan = FieldScan.create(
                    field=field,
                    file_path=zip_path,
                    filename=uploaded_filename,
                    uploaded_at=datetime.now(),
                    processed='pending',
                    source=scan_source,
                    crop_type=crop_type if crop_type != 'auto' else None
                )

            # 2. Запускаем фоновую задачу
            if processing_mode == 'orthomosaic':
                task = process_orthomosaic_task.delay(
                    zip_path=zip_path,
                    field_id=field_id,
                    total_fertilizer_kg=total_fertilizer_kg,
                    scan_id=scan.id
                )
            else:
                task = process_drone_fast_task.delay(
                    zip_path=zip_path,
                    field_id=field_id,
                    total_fertilizer_kg=total_fertilizer_kg,
                    scan_id=scan.id
                )

            # 3. Обновляем task_id у скана
            with db_connection():
                scan.task_id = str(task.id)
                scan.save()

            self.write({
                "message": f"Запущена обработка снимков ({processing_mode} mode).",
                "task_id": str(task.id),
                "field_id": field_id,
                "scan_id": scan.id,
                "processing_mode": processing_mode,
            })

        except Exception as e:
            # Чистим temp file при ошибке
            try:
                os.unlink(tmpfile_path)
            except OSError:
                pass
            logger.error(f"Ошибка в DroneUploadHandler: {e}")
            self.set_status(500)
            self.write({"error": str(e)})

    def _detect_field_from_gps(self, zip_path: str) -> Optional[int]:
        """
        Пытается определить поле по GPS координатам.
        Приоритет: PPK (.MRK) > EXIF/XMP из TIF.
        """
        import zipfile

        from shapely.geometry import Point
        from shapely.wkt import loads as wkt_loads

        from src.services.provider_dji import DJIProvider
        
        provider = DJIProvider()
        
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(tmpdir)

                    # Приоритет 1: PPK GPS из .MRK файла (точность ±2см)
                    mrk_path = provider.find_mrk_file(tmpdir)
                    if mrk_path:
                        ppk_data = provider.parse_ppk_timestamps(mrk_path)
                        if ppk_data:
                            first = ppk_data[0]
                            lat, lon = first['lat'], first['lon']
                            if lat != 0.0 and lon != 0.0:
                                logger.info(f"PPK GPS: lat={lat}, lon={lon}, quality={first['quality']}, sigma={first['sigma_n']:.2f}/{first['sigma_e']:.2f}/{first['sigma_u']:.2f}cm")
                                with db_connection():
                                    point = Point(lon, lat)
                                    for field in Field.select().where(Field.company == self.current_user.company):
                                        field_geom = wkt_loads(field.geometry_wkt)
                                        if field_geom.contains(point):
                                            return field.id

                    # Приоритет 2: EXIF/XMP из первого TIF файла
                    files = [f for f in zip_ref.namelist() 
                            if f.lower().endswith(('.tif', '.tiff'))]
                    
                    if not files:
                        return None
                    
                    first_file = files[0]
                    img_path = os.path.join(tmpdir, first_file)
                    
                    meta = provider.extract_dji_meta(img_path)
                    
                    if meta["lat"] == 0.0 or meta["lon"] == 0.0:
                        return None
                    
                    with db_connection():
                        point = Point(meta["lon"], meta["lat"])
                        for field in Field.select().where(Field.company == self.current_user.company):
                            field_geom = wkt_loads(field.geometry_wkt)
                            if field_geom.contains(point):
                                return field.id
                        
        except Exception as e:
            logger.error(f"Ошибка определения поля по GPS: {e}")
        
        return None
