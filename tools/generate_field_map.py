
import os
import re
import math
import logging
import numpy as np
import rasterio
from rasterio.transform import from_origin
from datetime import datetime
from collections import defaultdict
import geopandas as gpd
from shapely.geometry import Point
from scipy.interpolate import griddata
import pandas as pd

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Import from our analyzer
from multispectral_diag import Mavic3MAnalyzer

class FieldMapper:
    def __init__(self, analyzer: Mavic3MAnalyzer):
        self.analyzer = analyzer
        self.points = []

    def get_normalized_data(self, path, window=None):
        """Extracts and normalizes raw band data from DJI TIF."""
        meta = self.analyzer.extract_dji_meta(path)
        black_level = float(meta.get('BlackLevel', 3200))
        exposure = float(meta.get('ExposureTime', 1.0))
        gain = float(meta.get('SensorGain', 1.0))
        
        with rasterio.open(path) as src:
            if window:
                data = src.read(1, window=window).astype(float)
            else:
                # Fallback to downsampled full image if no window
                data = src.read(1, out_shape=(1, src.height // 8, src.width // 8)).astype(float)
            
            # Normalization formula for DJI Mavic 3M (simplified but robust)
            # (RawDN - BlackLevel) / (Exposure * Gain)
            normalized = (data - black_level) / (exposure * gain)
            return np.maximum(normalized, 1.0) # Ensure no zero or negative (1.0 as epsilon)

    def prepare_data(self, step=1):
        """Processes each set with normalization and calculates point indices."""
        logger.info(f"Normalizing and processing {len(self.analyzer.all_sets)} sets...")
        
        for s in self.analyzer.all_sets[::step]:
            try:
                # Use a central 200x200 window for better point representative
                with rasterio.open(s['bands']['NIR']) as src:
                    h, w = src.height, src.width
                    win = rasterio.windows.Window(w//2-100, h//2-100, 200, 200)
                
                # Get normalized bands
                nir = self.get_normalized_data(s['bands']['NIR'], window=win)
                red = self.get_normalized_data(s['bands']['R'], window=win)
                re = self.get_normalized_data(s['bands']['RE'], window=win)
                
                # NDVI = (NIR - Red) / (NIR + Red)
                ndvi_map = (nir - red) / (nir + red + 1e-10)
                ndvi_val = np.median(ndvi_map[(ndvi_map > -1) & (ndvi_map < 1)])
                
                # NDRE = (NIR - RE) / (NIR + RE)
                ndre_map = (nir - re) / (nir + re + 1e-10)
                ndre_val = np.median(ndre_map[(ndre_map > -1) & (ndre_map < 1)])
                
                if not np.isnan(ndvi_val):
                    self.points.append({
                        'lat': s['meta']['lat'],
                        'lon': s['meta']['lon'],
                        'ndvi': float(ndvi_val),
                        'ndre': float(ndre_val),
                        'alt': s['meta'].get('alt', 0)
                    })
            except Exception as e:
                logger.error(f"Error processing set {s['id']}: {e}")

    def generate_map(self, output_path="ndvi_corrected.tif", column='ndvi', res_m=2.0):
        """Generates a raster map using interpolation from corrected points."""
        if not self.points:
            logger.error("No points to map!")
            return

        df = pd.DataFrame(self.points)
        gdf = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df.lon, df.lat), crs="EPSG:4326")
        gdf_m = gdf.to_crs(epsg=3035)
        
        minx, miny, maxx, maxy = gdf_m.total_bounds
        minx -= 10; miny -= 10; maxx += 10; maxy += 10
        
        width = int((maxx - minx) / res_m)
        height = int((maxy - miny) / res_m)
        
        logger.info(f"Generating corrected grid {width}x{height} for {column}...")
        
        gx = np.linspace(minx, maxx, width)
        gy = np.linspace(maxy, miny, height)
        grid_x, grid_y = np.meshgrid(gx, gy)
        
        points_xy = np.column_stack((gdf_m.geometry.x, gdf_m.geometry.y))
        grid_values = griddata(points_xy, gdf_m[column], (grid_x, grid_y), method='linear')
        grid_values = np.nan_to_num(grid_values, nan=0.0)

        transform = from_origin(minx, maxy, res_m, res_m)
        with rasterio.open(output_path, 'w', driver='GTiff', height=height, width=width,
                           count=1, dtype=grid_values.dtype, crs='EPSG:3035', transform=transform) as dst:
            dst.write(grid_values, 1)
        
        logger.info(f"Corrected map saved to {output_path}")

if __name__ == "__main__":
    analyzer = Mavic3MAnalyzer("/media/vladibuyanov/SD_Card/DCIM")
    analyzer.scan()
    analyzer.analyze_quality()
    
    mapper = FieldMapper(analyzer)
    mapper.prepare_data(step=1)
    
    # Generate both NDVI and NDRE maps
    mapper.generate_map("ndvi_final_corrected.tif", column='ndvi', res_m=2.0)
    mapper.generate_map("ndre_final_corrected.tif", column='ndre', res_m=2.0)
    
    # Stats summary
    df = pd.DataFrame(mapper.points)
    print("\n=== FINAL CORRECTED STATS ===")
    print(df[['ndvi', 'ndre']].describe())
