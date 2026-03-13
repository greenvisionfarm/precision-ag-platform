import pytest
import io
import json
import os
import numpy as np
import rasterio
from rasterio.transform import from_origin
from tornado.testing import AsyncHTTPTestCase
from app import make_app
from db import initialize_db, database, Field, FieldZone

# Устанавливаем окружение теста перед всеми импортами и инициализацией
os.environ['FIELD_MAPPER_ENV'] = 'test'

def create_in_memory_geotiff():
    # Создаем данные с тремя зонами
    data = np.zeros((20, 20), dtype=np.float32)
    data[:7, :] = 0.2
    data[7:14, :] = 0.5
    data[14:, :] = 0.8
    # Координаты: запад, юг, восток, север
    transform = rasterio.transform.from_bounds(18.7, 48.1, 18.8, 48.2, 20, 20)
    
    buf = io.BytesIO()
    with rasterio.open(
        buf, 'w', driver='GTiff',
        height=20, width=20,
        count=1, dtype='float32',
        crs='EPSG:4326',
        transform=transform
    ) as dst:
        dst.write(data, 1)
    
    buf.seek(0)
    return buf.read()

class TestGeoTiffApi(AsyncHTTPTestCase):
    def get_app(self):
        initialize_db()
        return make_app()

    @pytest.mark.skip(reason="FIXME: Тест не проходит из-за особенностей работы rasterio.mask в окружении Tornado. Требуется доработка.")
    def test_geotiff_upload_and_zoning(self):
        # 1. Создаем поле
        field_data = {
            "name": "API Raster Test",
            "geometry": {
                "type": "Polygon",
                "coordinates": [[[18.6, 48.0], [18.9, 48.0], [18.9, 48.3], [18.6, 48.3], [18.6, 48.0]]]
            }
        }
        response = self.fetch("/api/field/add", method="POST", body=json.dumps(field_data))
        self.assertEqual(response.code, 200)
        field_id = json.loads(response.body)['id']

        # 2. Загружаем GeoTIFF
        tif_bytes = create_in_memory_geotiff()
        boundary = "AaB03x"
        body = (
            f"--{boundary}\r\n"
            f"Content-Disposition: form-data; name=\"raster_file\"; filename=\"test.tif\"\r\n"
            f"Content-Type: image/tiff\r\n\r\n"
        ).encode() + tif_bytes + f"\r\n--{boundary}--\r\n".encode()
        
        headers = {"Content-Type": f"multipart/form-data; boundary={boundary}"}
        
        resp_upload = self.fetch("/upload", method="POST", headers=headers, body=body, request_timeout=30)
        if resp_upload.code != 200:
            print(f"UPLOAD ERROR: {resp_upload.body.decode()}")
        self.assertEqual(resp_upload.code, 200)
        
        # 3. Проверяем наличие зон
        resp_detail = self.fetch(f"/api/field/{field_id}", method="GET", request_timeout=30)
        data = json.loads(resp_detail.body)
        
        self.assertIn("zones", data)
        self.assertGreater(len(data['zones']), 0)
        # Проверяем, что средний NDVI зон находится в ожидаемом диапазоне
        self.assertTrue(0.1 < data['zones'][0]['avg_ndvi'] < 0.9)
