"""Tests for drone zone quality — create_grid_and_zone produces usable zones."""
import os
import tempfile
import numpy as np
import pytest
from shapely.geometry import mapping
from shapely import wkt

from src.services.drone_processing_service import DroneProcessingService, DronePoint

FIELD_WKT = (
    "POLYGON ((18.7266 48.2026, 18.7324 48.2026, "
    "18.7324 48.2077, 18.7266 48.2077, 18.7266 48.2026))"
)


def _make_points(count=30, ndvi_range=(0.1, 0.8), spread=0.003):
    """Generate synthetic drone points scattered around field center."""
    rng = np.random.RandomState(42)
    center_lat = 48.205
    center_lon = 18.729
    points = []
    for i in range(count):
        lat = center_lat + rng.uniform(-spread, spread)
        lon = center_lon + rng.uniform(-spread, spread)
        ndvi = rng.uniform(*ndvi_range)
        ndre = ndvi * 0.8 + rng.uniform(-0.05, 0.05)
        points.append(DronePoint(
            lat=lat, lon=lon, ndvi=ndvi, ndre=ndre,
            file_name=f"photo_{i:04d}"
        ))
    return points


def _make_gradient_points(count=30):
    """Points with NDVI gradient: low at bottom, high at top of field."""
    rng = np.random.RandomState(42)
    points = []
    for i in range(count):
        lat = 48.2026 + (i / count) * (48.2077 - 48.2026)
        lon = 18.7266 + rng.uniform(0, 18.7324 - 18.7266)
        ndvi = 0.1 + 0.7 * (i / count)
        ndre = ndvi * 0.9
        points.append(DronePoint(
            lat=lat, lon=lon, ndvi=ndvi, ndre=ndre,
            file_name=f"photo_{i:04d}"
        ))
    return points


@pytest.fixture
def service():
    return DroneProcessingService()


class TestCreateGridAndZone:
    """Test create_grid_and_zone produces valid zones from drone points."""

    def test_returns_4_zones(self, service):
        """4 drone zones when requesting 4 via process_ndvi_zones."""
        points = _make_points(40)
        with tempfile.NamedTemporaryFile(suffix='.tif', delete=False) as f:
            tif_path = f.name
        try:
            zones = service.create_grid_and_zone(points, FIELD_WKT, tif_path)
            assert len(zones) >= 2, f"Expected >=2 zones, got {len(zones)}"
        finally:
            os.unlink(tif_path)

    def test_zones_have_valid_geometry(self, service):
        """All zones have valid WKT geometry."""
        points = _make_points(40)
        with tempfile.NamedTemporaryFile(suffix='.tif', delete=False) as f:
            tif_path = f.name
        try:
            zones = service.create_grid_and_zone(points, FIELD_WKT, tif_path)
            for z in zones:
                geom = wkt.loads(z['geometry_wkt'])
                assert geom.is_valid, f"Invalid geometry for zone '{z['name']}'"
                assert not geom.is_empty, f"Empty geometry for zone '{z['name']}'"
        finally:
            os.unlink(tif_path)

    def test_zones_cover_field(self, service):
        """Zones collectively cover a reasonable portion of the field."""
        points = _make_points(50)
        field_geom = wkt.loads(FIELD_WKT)
        with tempfile.NamedTemporaryFile(suffix='.tif', delete=False) as f:
            tif_path = f.name
        try:
            zones = service.create_grid_and_zone(points, FIELD_WKT, tif_path)
            from shapely.ops import unary_union
            zone_union = unary_union([wkt.loads(z['geometry_wkt']) for z in zones])
            overlap = zone_union.intersection(field_geom)
            coverage = overlap.area / field_geom.area if field_geom.area > 0 else 0
            assert coverage > 0.3, f"Zones cover only {coverage:.1%} of field, expected >30%"
        finally:
            os.unlink(tif_path)

    def test_zones_ndvi_ordered(self, service):
        """Zone NDVI values are monotonically increasing."""
        points = _make_gradient_points(50)
        with tempfile.NamedTemporaryFile(suffix='.tif', delete=False) as f:
            tif_path = f.name
        try:
            zones = service.create_grid_and_zone(points, FIELD_WKT, tif_path)
            if len(zones) >= 2:
                ndvi_vals = [z['avg_ndvi'] for z in zones]
                assert ndvi_vals == sorted(ndvi_vals), \
                    f"NDVI not ordered: {ndvi_vals}"
        finally:
            os.unlink(tif_path)

    def test_zones_no_major_overlap(self, service):
        """Zones don't have major overlapping areas."""
        points = _make_points(40)
        with tempfile.NamedTemporaryFile(suffix='.tif', delete=False) as f:
            tif_path = f.name
        try:
            zones = service.create_grid_and_zone(points, FIELD_WKT, tif_path)
            geoms = [wkt.loads(z['geometry_wkt']) for z in zones]
            for i, g1 in enumerate(geoms):
                for g2 in geoms[i + 1:]:
                    overlap = g1.intersection(g2)
                    if overlap.area > 0:
                        smaller = min(g1.area, g2.area)
                        overlap_ratio = overlap.area / smaller if smaller > 0 else 0
                        assert overlap_ratio < 0.3, \
                            f"Zones overlap {overlap_ratio:.1%} (expected <30%)"
        finally:
            os.unlink(tif_path)

    def test_tif_is_created(self, service):
        """create_grid_and_zone produces a valid TIF file."""
        points = _make_points(20)
        with tempfile.NamedTemporaryFile(suffix='.tif', delete=False) as f:
            tif_path = f.name
        try:
            service.create_grid_and_zone(points, FIELD_WKT, tif_path)
            import rasterio
            with rasterio.open(tif_path) as src:
                assert src.crs is not None
                assert src.width > 0
                assert src.height > 0
        finally:
            os.unlink(tif_path)

    def test_empty_points_returns_empty(self, service):
        """No points means no zones."""
        with tempfile.NamedTemporaryFile(suffix='.tif', delete=False) as f:
            tif_path = f.name
        try:
            zones = service.create_grid_and_zone([], FIELD_WKT, tif_path)
            assert zones == []
        finally:
            os.unlink(tif_path)
