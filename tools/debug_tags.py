
import rasterio
from PIL import Image
from PIL.ExifTags import TAGS
import re

path = "/media/vladibuyanov/SD_Card/DCIM/DJI_202603251508_012_DJI-SmartFarm-Web/DJI_20260325151035_0001_MS_NIR.TIF"

print(f"--- Analyzing {path} ---")

print("\n1. PIL Tags:")
try:
    img = Image.open(path)
    if hasattr(img, 'tag'):
        for tag in img.tag:
            name = TAGS.get(tag, tag)
            print(f"  {name} ({tag}): {img.tag[tag][:1]}") # Print just first value to avoid clutter
except Exception as e:
    print(f"  Error: {e}")

print("\n2. Rasterio Meta:")
try:
    with rasterio.open(path) as src:
        print(f"  Tags: {src.tags()}")
        print(f"  Metadata: {src.meta}")
except Exception as e:
    print(f"  Error: {e}")

print("\n3. Raw XMP search:")
try:
    with open(path, 'rb') as f:
        data = f.read(128000).decode('latin-1', errors='ignore')
        # Find some DJI strings
        for word in ['drone-dji', 'GpsLatitude', 'GPS', 'Latitude', 'DateTime']:
            match = re.search(f'({word}[^=]*="[^"]*")', data)
            if match:
                print(f"  Found: {match.group(1)}")
except Exception as e:
    print(f"  Error: {e}")
