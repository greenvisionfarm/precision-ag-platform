
import os
import re
import math
import logging
import numpy as np
import rasterio
from datetime import datetime
from collections import defaultdict
from typing import Dict, List, Optional, Tuple

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

class Mavic3MAnalyzer:
    # DJI Mavic 3M band mapping (verified from DJI docs)
    BAND_MAP = {
        'G': 'Green',
        'R': 'Red',
        'RE': 'RedEdge',
        'NIR': 'NIR',
        'D': 'RGB'
    }

    def __init__(self, root_dir: str):
        self.root_dir = root_dir
        self.missions = defaultdict(list)
        self.all_sets = []

    def extract_dji_meta(self, file_path: str) -> Dict[str, any]:
        """Extracts GPS and other DJI meta using regex on file head (very robust)."""
        try:
            with open(file_path, 'rb') as f:
                # Read enough to cover XMP (DJI puts it at the beginning)
                data = f.read(256000).decode('latin-1', errors='ignore')
                
                meta = {}
                # Search for coordinates with various possible patterns
                lat_m = re.search(r'GpsLatitude="([^"]+)"', data) or re.search(r'Latitude="([^"]+)"', data)
                lon_m = re.search(r'GpsLongitude="([^"]+)"', data) or re.search(r'Longitude="([^"]+)"', data)
                alt_m = re.search(r'AbsoluteAltitude="([^"]+)"', data) or re.search(r'GpsAltitude="([^"]+)"', data)
                rel_alt_m = re.search(r'RelativeAltitude="([^"]+)"', data)
                time_m = re.search(r'CreateDate="([^"]+)"', data) or re.search(r'DateTimeOriginal="([^"]+)"', data)
                
                if lat_m: meta['lat'] = float(lat_m.group(1))
                if lon_m: meta['lon'] = float(lon_m.group(1))
                if alt_m: meta['alt'] = float(alt_m.group(1))
                if rel_alt_m: meta['rel_alt'] = float(rel_alt_m.group(1))
                
                if time_m:
                    ts_str = time_m.group(1).replace('T', ' ')
                    try:
                        meta['time'] = datetime.strptime(ts_str[:19], "%Y:%m:%d %H:%M:%S")
                    except:
                        try:
                            meta['time'] = datetime.strptime(ts_str[:19], "%Y-%m-%d %H:%M:%S")
                        except: pass
                
                # Calibration tags
                for tag in ['BlackLevel', 'SensorGain', 'ExposureTime', 'SensorSunlight', 'SensorSunlightYaw', 'SensorSunlightPitch', 'DroneSensorRadiationCalibrated']:
                    m = re.search(f'{tag}="([^"]+)"', data)
                    if m: meta[tag] = m.group(1)
                
                return meta
        except Exception as e:
            logger.debug(f"Meta error in {file_path}: {e}")
        return {}

    def scan(self):
        """Scans directory and groups files by mission and sequence index."""
        logger.info(f"Scanning {self.root_dir}...")
        for root, dirs, files in os.walk(self.root_dir):
            mission_name = os.path.basename(root)
            groups = defaultdict(dict)
            for f in files:
                if not f.lower().endswith(('.tif', '.tiff', '.jpg')): continue
                parts = f.split('_')
                if len(parts) < 4: continue
                idx = parts[2] 
                band_part = parts[-1].split('.')[0] 
                groups[idx][band_part] = os.path.join(root, f)

            for idx, bands in groups.items():
                if 'NIR' in bands or 'R' in bands:
                    self.missions[mission_name].append({
                        'id': idx,
                        'bands': bands,
                        'mission': mission_name
                    })

    def analyze_quality(self):
        """Checks for missing bands, GPS jumps, and metadata consistency."""
        report = []
        total_sets = 0
        valid_sets = 0
        all_coords = []
        
        for mission, sets in self.missions.items():
            sets.sort(key=lambda x: x['id'])
            mission_valid = 0
            mission_total = len(sets)
            prev_coords = None
            
            for s in sets:
                total_sets += 1
                missing = [b for b in ['NIR', 'R', 'RE', 'G'] if b not in s['bands']]
                if missing:
                    continue
                
                meta = self.extract_dji_meta(s['bands']['NIR'])
                if 'lat' not in meta:
                    # Try D.JPG if NIR fails
                    if 'D' in s['bands']:
                        meta = self.extract_dji_meta(s['bands']['D'])
                
                if 'lat' not in meta:
                    continue
                
                s['meta'] = meta
                all_coords.append((meta['lat'], meta['lon']))
                
                if prev_coords:
                    dist = math.sqrt((meta['lat']-prev_coords[0])**2 + (meta['lon']-prev_coords[1])**2) * 111320
                    if dist > 100: 
                        logger.warning(f"Large distance jump: {dist:.1f}m at {mission}/{s['id']}")
                
                prev_coords = (meta['lat'], meta['lon'])
                mission_valid += 1
                valid_sets += 1
                self.all_sets.append(s)

            report.append(f"Mission {mission}: {mission_valid}/{mission_total} valid sets")

        if not all_coords:
            return "No valid GPS data found."

        lats, lons = zip(*all_coords)
        return {
            "total_frames": total_sets,
            "valid_sets": valid_sets,
            "dropped": total_sets - valid_sets,
            "lat_range": (min(lats), max(lats)),
            "lon_range": (min(lons), max(lons)),
            "missions_report": report
        }

    def calculate_indices_metrics(self, max_samples=30):
        """Calculates NDVI/NDRE metrics on a subset of data."""
        ndvi_values = []
        ndre_values = []
        
        samples = self.all_sets
        if len(samples) > max_samples:
            indices = np.linspace(0, len(samples)-1, max_samples, dtype=int)
            samples = [samples[i] for i in indices]
            
        logger.info(f"Calculating metrics on {len(samples)} sample sets...")
        for s in samples:
            try:
                with rasterio.open(s['bands']['NIR']) as src:
                    nir = src.read(1, out_shape=(1, src.height // 8, src.width // 8)).astype(float)
                with rasterio.open(s['bands']['R']) as src:
                    red = src.read(1, out_shape=(1, src.height // 8, src.width // 8)).astype(float)
                with rasterio.open(s['bands']['RE']) as src:
                    re = src.read(1, out_shape=(1, src.height // 8, src.width // 8)).astype(float)
                
                ndvi = (nir - red) / (nir + red + 1e-10)
                ndvi_values.extend(ndvi[(ndvi > -1.0) & (ndvi < 1.0)].flatten())
                
                ndre = (nir - re) / (nir + re + 1e-10)
                ndre_values.extend(ndre[(ndre > -1.0) & (ndre < 1.0)].flatten())
            except Exception as e:
                logger.error(f"Error processing indices for {s['id']}: {e}")

        if not ndvi_values: return {}
        ndvi_values = np.array(ndvi_values)
        ndre_values = np.array(ndre_values)
        
        return {
            "NDVI": {
                "min": float(np.min(ndvi_values)),
                "max": float(np.max(ndvi_values)),
                "mean": float(np.mean(ndvi_values)),
                "p50": float(np.percentile(ndvi_values, 50))
            },
            "NDRE": {
                "min": float(np.min(ndre_values)),
                "max": float(np.max(ndre_values)),
                "mean": float(np.mean(ndre_values))
            }
        }

if __name__ == "__main__":
    analyzer = Mavic3MAnalyzer("/media/vladibuyanov/SD_Card/DCIM")
    analyzer.scan()
    diag = analyzer.analyze_quality()
    print("\n=== DIAGNOSTICS ===")
    import json
    if isinstance(diag, str):
        print(diag)
    else:
        print(json.dumps(diag, indent=2))
        metrics = analyzer.calculate_indices_metrics()
        print("\n=== METRICS (SAMPLED) ===")
        print(json.dumps(metrics, indent=2))
        
        print("\n=== CONCLUSION ===")
        if diag['dropped'] / diag['total_frames'] > 0.1:
            print("WARNING: More than 10% frames dropped.")
        elif metrics['NDVI']['max'] < 0.2:
            print("WARNING: Very low NDVI.")
        else:
            print("DATA LOOKS HEALTHY.")
