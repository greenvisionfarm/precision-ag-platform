# DJI Drone Meta

Извлечение метаданных (XMP/EXIF) из мультиспектральных снимков DJI (Mavic 3M, Phantom 4 Multispectral).

## Использование

```python
from dji_drone_meta import DJIMetadataExtractor

meta = DJIMetadataExtractor.extract("DJI_0001_MS_NIR.TIF")
print(f"GPS: {meta['lat']}, {meta['lon']}")
print(f"BlackLevel: {meta['black_level']}")
```
