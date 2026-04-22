
import rasterio
import numpy as np
import re

path_nir = "/media/vladibuyanov/SD_Card/DCIM/DJI_202603251508_012_DJI-SmartFarm-Web/DJI_20260325151035_0001_MS_NIR.TIF"
path_red = "/media/vladibuyanov/SD_Card/DCIM/DJI_202603251508_012_DJI-SmartFarm-Web/DJI_20260325151035_0001_MS_R.TIF"

def get_calib(p):
    with open(p, 'rb') as f:
        data = f.read(256000).decode('latin-1', errors='ignore')
        tags = ['BlackLevel', 'SensorGain', 'ExposureTime', 'SensorGainAdjustment', 'VignettingCenter']
        res = {}
        for t in tags:
            m = re.search(f'{t}="([^"]+)"', data)
            if m: res[t] = m.group(1)
        return res

print("--- CALIBRATION METADATA ---")
print(f"NIR: {get_calib(path_nir)}")
print(f"RED: {get_calib(path_red)}")

with rasterio.open(path_nir) as s_nir, rasterio.open(path_red) as s_red:
    nir = s_nir.read(1).astype(float)
    red = s_red.read(1).astype(float)
    
    ndvi = (nir - red) / (nir + red + 1e-10)
    ndvi = ndvi[(ndvi > -1) & (ndvi < 1)]
    
    print("\n--- NDVI DISTRIBUTION (HISTOGRAM) ---")
    hist, bins = np.histogram(ndvi, bins=10, range=(0, 1))
    for i in range(len(hist)):
        bar = "#" * int(hist[i] / np.max(hist) * 40)
        print(f"{bins[i]:10.2f} | {bar} ({hist[i]})")

    print(f"\nPercentile 95 (Top vegetation): {np.percentile(ndvi, 95):.4f}")
    print(f"Percentile 5 (Soil/Shadows): {np.percentile(ndvi, 5):.4f}")
