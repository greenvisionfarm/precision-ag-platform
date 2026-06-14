"""
TDD tests for orthomosaic service.
cv2.Stitcher-based stitching of drone RGB photos + georeferencing.
"""
import os
import tempfile
import numpy as np
import pytest
from unittest.mock import patch, MagicMock, PropertyMock
from dataclasses import dataclass


class TestOrthomosaicService:
    """Tests for OrthomosaicService."""

    def test_import(self):
        """Module can be imported."""
        from src.services.orthomosaic_service import OrthomosaicService
        assert OrthomosaicService is not None

    def test_filter_rgb_jpgs(self):
        """Only RGB JPGs are selected for stitching, not MS TIFs."""
        from src.services.orthomosaic_service import OrthomosaicService
        svc = OrthomosaicService.__new__(OrthomosaicService)
        
        files = [
            "DJI_20260524_001_D.JPG",
            "DJI_20260524_001_MS_NIR.TIF",
            "DJI_20260524_001_MS_R.TIF",
            "DJI_20260524_002_D.JPG",
            "random_file.txt",
            "_PPKNAV.nav",
        ]
        
        rgb_files = svc._filter_rgb_jpgs(files)
        assert len(rgb_files) == 2
        assert all(f.endswith("_D.JPG") for f in rgb_files)

    def test_extract_gps_from_images(self):
        """GPS coordinates are extracted from DJI image metadata."""
        from src.services.orthomosaic_service import OrthomosaicService, ImageGPS
        
        svc = OrthomosaicService.__new__(OrthomosaicService)
        
        mock_gps = [
            ImageGPS(path="img1.jpg", lat=48.858, lon=2.294, alt=120.0),
            ImageGPS(path="img2.jpg", lat=48.859, lon=2.295, alt=121.0),
            ImageGPS(path="img3.jpg", lat=48.860, lon=2.296, alt=119.0),
        ]
        
        bounds = svc._compute_bounds(mock_gps)
        assert bounds is not None
        assert bounds["min_lat"] == pytest.approx(48.858, abs=0.001)
        assert bounds["max_lat"] == pytest.approx(48.860, abs=0.001)
        assert bounds["min_lon"] == pytest.approx(2.294, abs=0.001)
        assert bounds["max_lon"] == pytest.approx(2.296, abs=0.001)

    def test_compute_bounds_empty(self):
        """Empty GPS list returns None."""
        from src.services.orthomosaic_service import OrthomosaicService
        
        svc = OrthomosaicService.__new__(OrthomosaicService)
        bounds = svc._compute_bounds([])
        assert bounds is None

    def test_build_geotiff_transform(self):
        """Computes rasterio Affine transform from GPS bounds and image dimensions."""
        from src.services.orthomosaic_service import OrthomosaicService
        
        svc = OrthomosaicService.__new__(OrthomosaicService)
        bounds = {
            "min_lat": 48.858,
            "max_lat": 48.860,
            "min_lon": 2.294,
            "max_lon": 2.296,
        }
        width, height = 4000, 3000
        
        transform, crs = svc._build_geotransform(bounds, width, height)
        assert transform is not None
        assert crs is not None
        # Pixel size should be roughly (lon_range/width, lat_range/height)
        pixel_x = abs(transform.a)
        pixel_y = abs(transform.e)
        assert pixel_x > 0
        assert pixel_y > 0

    def test_stitch_success(self):
        """Successful stitching returns stitched image and GPS data."""
        from src.services.orthomosaic_service import OrthomosaicService, StitchResult
        
        svc = OrthomosaicService.__new__(OrthomosaicService)
        svc.provider = MagicMock()
        svc.logger = MagicMock()
        
        mock_img = np.zeros((100, 100, 3), dtype=np.uint8)
        
        mock_stitcher = MagicMock()
        mock_stitcher.stitch.return_value = (0, np.zeros((3000, 4000, 3), dtype=np.uint8))
        
        with patch('cv2.Stitcher_create', return_value=mock_stitcher):
            with patch('cv2.imread', return_value=mock_img):
                with patch.object(svc, '_extract_gps_for_images') as mock_gps:
                    mock_gps.return_value = [
                        MagicMock(lat=48.858, lon=2.294, alt=120.0),
                        MagicMock(lat=48.859, lon=2.295, alt=121.0),
                        MagicMock(lat=48.860, lon=2.296, alt=119.0),
                    ]
                    result = svc.stitch_images(["img1.jpg", "img2.jpg", "img3.jpg"])
                    
                    assert isinstance(result, StitchResult)
                    assert result.success is True
                    assert result.stitched_image is not None
                    assert result.image_width == 4000
                    assert result.image_height == 3000

    def test_stitch_few_images(self):
        """Stitching fails with fewer than 2 images."""
        from src.services.orthomosaic_service import OrthomosaicService, StitchResult
        
        svc = OrthomosaicService.__new__(OrthomosaicService)
        svc.logger = MagicMock()
        
        result = svc.stitch_images(["img1.jpg"])
        assert isinstance(result, StitchResult)
        assert result.success is False
        assert "недостаточно" in result.error.lower() or "minimum" in result.error.lower()

    def test_save_geotiff(self):
        """Stitched image is saved as georeferenced GeoTIFF."""
        from src.services.orthomosaic_service import OrthomosaicService
        
        svc = OrthomosaicService.__new__(OrthomosaicService)
        svc.logger = MagicMock()
        
        with tempfile.NamedTemporaryFile(suffix='.tif', delete=False) as tmp:
            output_path = tmp.name
        
        try:
            image = np.random.randint(0, 255, (100, 200, 3), dtype=np.uint8)
            bounds = {
                "min_lat": 48.858,
                "max_lat": 48.860,
                "min_lon": 2.294,
                "max_lon": 2.296,
            }
            
            svc._save_geotiff(image, bounds, output_path)
            
            import rasterio
            with rasterio.open(output_path) as src:
                assert src.crs is not None
                assert src.width == 200
                assert src.height == 100
                assert src.count == 3
                assert src.driver == 'GTiff'
        finally:
            if os.path.exists(output_path):
                os.remove(output_path)

    def test_full_pipeline_mock(self):
        """Full pipeline: extract RGBs → stitch → georeference → save GeoTIFF."""
        from src.services.orthomosaic_service import OrthomosaicService
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create fake DJI RGB JPG files
            for i in range(3):
                path = os.path.join(tmpdir, f"DJI_20260524_{i:03d}_D.JPG")
                with open(path, 'wb') as f:
                    f.write(b'\xff\xd8\xff\xe0')
                    f.write(b'\x00' * 100)
            
            svc = OrthomosaicService.__new__(OrthomosaicService)
            svc.provider = MagicMock()
            svc.logger = MagicMock()
            
            mock_gps_list = [
                MagicMock(lat=48.858, lon=2.294, alt=120.0),
                MagicMock(lat=48.859, lon=2.295, alt=121.0),
                MagicMock(lat=48.860, lon=2.296, alt=119.0),
            ]
            
            stitched_img = np.random.randint(0, 255, (600, 800, 3), dtype=np.uint8)
            
            mock_stitcher = MagicMock()
            mock_stitcher.stitch.return_value = (0, stitched_img)
            
            mock_img = np.zeros((100, 100, 3), dtype=np.uint8)
            
            with patch('cv2.Stitcher_create', return_value=mock_stitcher):
                with patch('cv2.imread', return_value=mock_img):
                    with patch.object(svc, '_extract_gps_for_images', return_value=mock_gps_list):
                        output_tif = os.path.join(tmpdir, "orthomosaic.tif")
                        result = svc.process_directory(tmpdir, output_tif)
                        
                        assert result.success is True
                        assert os.path.exists(output_tif)
                        assert os.path.getsize(output_tif) > 0

    def test_stitch_cv2_error(self):
        """Stitching failure returns error result."""
        from src.services.orthomosaic_service import OrthomosaicService, StitchResult
        
        svc = OrthomosaicService.__new__(OrthomosaicService)
        svc.logger = MagicMock()
        
        mock_img = np.zeros((100, 100, 3), dtype=np.uint8)
        
        mock_stitcher = MagicMock()
        mock_stitcher.stitch.return_value = (1, None)  # ERR_NEED_MORE_IMGS
        
        with patch('cv2.Stitcher_create', return_value=mock_stitcher):
            with patch('cv2.imread', return_value=mock_img):
                with patch.object(svc, '_extract_gps_for_images') as mock_gps:
                    mock_gps.return_value = [
                        MagicMock(lat=48.858, lon=2.294, alt=120.0),
                        MagicMock(lat=48.859, lon=2.295, alt=121.0),
                    ]
                    result = svc.stitch_images(["img1.jpg", "img2.jpg"])
                    
                    assert result.success is False
                    assert result.error is not None

    def test_min_images_constant(self):
        """MIN_IMAGES constant is defined and >= 2."""
        from src.services.orthomosaic_service import MIN_IMAGES
        assert MIN_IMAGES >= 2


class TestImageGPS:
    """Tests for ImageGPS dataclass."""

    def test_creation(self):
        from src.services.orthomosaic_service import ImageGPS
        gps = ImageGPS(path="test.jpg", lat=48.858, lon=2.294, alt=120.0)
        assert gps.path == "test.jpg"
        assert gps.lat == 48.858


class TestStitchResult:
    """Tests for StitchResult dataclass."""

    def test_success_result(self):
        from src.services.orthomosaic_service import StitchResult
        import numpy as np
        img = np.zeros((100, 100, 3), dtype=np.uint8)
        result = StitchResult(success=True, stitched_image=img, image_width=100, image_height=100)
        assert result.success is True
        assert result.error is None

    def test_failure_result(self):
        from src.services.orthomosaic_service import StitchResult
        result = StitchResult(success=False, error="Not enough images")
        assert result.success is False
        assert result.error == "Not enough images"


class TestOrthomosaicTask:
    """Tests for the orthomosaic Huey task."""

    def test_task_function_exists(self):
        """_process_orthomosaic_impl is importable."""
        from src.tasks import _process_orthomosaic_impl
        assert callable(_process_orthomosaic_impl)

    def test_task_huey_decorator(self):
        """process_orthomosaic_task is a Huey task."""
        from src.tasks import process_orthomosaic_task
        assert hasattr(process_orthomosaic_task, 'func')
        assert callable(process_orthomosaic_task.func)

    def test_impl_stitch_failure(self):
        """Task returns error when stitching fails."""
        from src.tasks import _process_orthomosaic_impl

        mock_ortho_svc = MagicMock()
        mock_ortho_svc.process_directory.return_value = MagicMock(
            success=False, error="Not enough images"
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            zip_path = os.path.join(tmpdir, "test.zip")
            import zipfile
            with zipfile.ZipFile(zip_path, 'w') as zf:
                zf.writestr("dummy.txt", "data")

            with patch('src.services.orthomosaic_service.OrthomosaicService', return_value=mock_ortho_svc):
                results = _process_orthomosaic_impl(zip_path, field_id=1)

                assert results["success"] is False
                assert "Ошибка склейки" in results["error"]
                assert not os.path.exists(zip_path)

    def test_impl_success(self):
        """Task completes successfully with stitching and zones."""
        from src.tasks import _process_orthomosaic_impl
        import zipfile

        mock_ortho_svc = MagicMock()
        mock_ortho_svc.process_directory.return_value = MagicMock(
            success=True, stitched_image=MagicMock(),
            image_width=100, image_height=100,
            gps_data=[], error=None,
        )

        mock_drone_svc = MagicMock()
        mock_point = MagicMock(ndvi=0.6, ndre=0.4, lat=48.85, lon=2.29, alt=100.0, file_name="test")
        mock_drone_svc.process_directory.return_value = [mock_point]
        mock_drone_svc.create_grid_and_zone.return_value = [
            {"name": "Zone 1", "geometry_wkt": "POLYGON((0 0,1 0,1 1,0 1,0 0))", "avg_ndvi": 0.6, "color": "#00ff00"}
        ]

        mock_field_inst = MagicMock()
        mock_field_inst.geometry_wkt = "POLYGON((0 0,1 0,1 1,0 1,0 0))"

        mock_scan = MagicMock()
        mock_scan.id = 42

        mock_database = MagicMock()
        mock_database.atomic.return_value.__enter__ = MagicMock()
        mock_database.atomic.return_value.__exit__ = MagicMock(return_value=False)

        mock_field_zone = MagicMock()

        with tempfile.TemporaryDirectory() as tmpdir:
            zip_path = os.path.join(tmpdir, "test.zip")
            with zipfile.ZipFile(zip_path, 'w') as zf:
                zf.writestr("dummy.txt", "data")

            with patch('src.services.orthomosaic_service.OrthomosaicService', return_value=mock_ortho_svc), \
                 patch('src.services.drone_processing_service.DroneProcessingService', return_value=mock_drone_svc), \
                 patch('db.Field') as mock_field, \
                 patch('db.FieldScan') as mock_field_scan, \
                 patch('db.FieldZone', mock_field_zone), \
                 patch('db.database', mock_database), \
                 patch('src.tasks.db_connection'), \
                 patch('src.constants.UPLOAD_DIR', '/tmp/uploads'), \
                 patch('src.services.crop_classifier.classify_from_raster', return_value={"crop_type": "wheat", "confidence": 0.8}), \
                 patch('shutil.copy2'):

                mock_field.get_by_id.return_value = mock_field_inst
                mock_field_scan.get_by_id.return_value = mock_scan
                mock_field_scan.create.return_value = mock_scan

                results = _process_orthomosaic_impl(zip_path, field_id=1)

                assert results["success"] is True
                assert results["scan_id"] == 42
                assert results["crop_type"] == "wheat"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
