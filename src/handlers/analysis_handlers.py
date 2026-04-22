
import tornado.web
import json
import os
import rasterio
import numpy as np

class FieldAnalysisHandler(tornado.web.RequestHandler):
    """
    Handler for field multispectral analysis data.
    Provides stats and URLs for NDVI/NDRE/VRA maps.
    """
    def get(self, field_id):
        # В реальной системе здесь был бы поиск путей в БД. 
        # Сейчас мы берем наши сгенерированные файлы из папки проекта.
        analysis_dir = "static/analysis"
        
        files = {
            "ndvi": "ndvi_final_corrected.tif",
            "ndre": "ndre_final_corrected.tif",
            "vra": "vra_prescription_200kg.tif"
        }
        
        # Проверяем наличие файлов
        results = {"field_id": field_id, "layers": {}}
        
        for key, filename in files.items():
            path = os.path.join(analysis_dir, filename)
            if os.path.exists(path):
                # Базовая статистика для UI
                with rasterio.open(path) as src:
                    data = src.read(1)
                    mask = data > 0
                    valid_data = data[mask]
                    
                    results["layers"][key] = {
                        "url": f"/static/analysis/{filename}",
                        "mean": float(np.mean(valid_data)) if len(valid_data) > 0 else 0,
                        "max": float(np.max(valid_data)) if len(valid_data) > 0 else 0,
                        "bounds": [[src.bounds.bottom, src.bounds.left], [src.bounds.top, src.bounds.right]]
                    }
        
        self.set_header("Content-Type", "application/json")
        self.write(json.dumps(results))
