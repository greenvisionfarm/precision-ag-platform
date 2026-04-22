
import rasterio
import numpy as np
import re
from PIL import Image

path = "/media/vladibuyanov/SD_Card/DCIM/DJI_202603251521_014_DJISmartFarmWeb-CankovskaHora/DJI_202603251521_014_0001_MS_NIR.TIF" # Using a known path
# Wait, the path from scan was DJI_202603251521_014_DJISmartFarmWeb-CankovskaHora/DJI_202603251521_014_0001_MS_NIR.TIF ? 
# Let me verify a real path from previous ls
# /media/vladibuyanov/SD_Card/DCIM/DJI_202603251508_012_DJI-SmartFarm-Web/DJI_20260325151035_0001_MS_NIR.TIF

def get_stats(p):
    with rasterio.open(p) as src:
        d = src.read(1).astype(float)
        return {
            'min': np.min(d),
            'max': np.max(d),
            'mean': np.mean(d),
            'median': np.median(d),
            'p95': np.percentile(d, 95)
        }

root = "/media/vladibuyanov/SD_Card/DCIM/DJI_202603251508_012_DJI-SmartFarm-Web/"
base = "DJI_20260325151035_0001_MS_"

bands = ['NIR', 'R', 'RE', 'G']
print(f"--- Raw Stats for {base} ---")
for b in bands:
    p = root + base + b + ".TIF"
    stats = get_stats(p)
    print(f"{b}: {stats}")

# Calculate manual NDVI from medians
nir_m = get_stats(root + base + "NIR.TIF")['median']
red_m = get_stats(root + base + "R.TIF")['median']
re_m = get_stats(root + base + "RE.TIF")['median']

ndvi_man = (nir_m - red_m) / (nir_m + red_m)
ndre_man = (nir_m - re_m) / (nir_m + re_m)

print(f"\nManual Median NDVI: {ndvi_man:.4f}")
print(f"Manual Median NDRE: {ndre_man:.4f}")

# Check Sunlight Sensor in XMP
def extract_sun(p):
    with open(p, 'rb') as f:
        data = f.read(256000).decode('latin-1', errors='ignore')
        m = re.search(r'SensorSunlight="([^"]+)"', data)
        return m.group(1) if m else "None"

print(f"\nNIR SensorSunlight: {extract_sun(root + base + 'NIR.TIF')}")
print(f"RED SensorSunlight: {extract_sun(root + base + 'R.TIF')}")
