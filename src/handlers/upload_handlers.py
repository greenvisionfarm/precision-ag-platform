import tornado.web
import json
import tempfile
import zipfile
import os
import math
import geopandas as gpd
from db import database, Field

class UploadHandler(tornado.web.RequestHandler):
    def post(self):
        try:
            uploaded_file = self.request.files['shapefile_zip'][0]
            with tempfile.TemporaryDirectory() as tmpdir:
                zip_path = os.path.join(tmpdir, "up.zip")
                with open(zip_path, 'wb') as f: f.write(uploaded_file['body'])
                with zipfile.ZipFile(zip_path, 'r') as zip_ref: zip_ref.extractall(tmpdir)
                shp_file = next((os.path.join(r, f) for r, _, fs in os.walk(tmpdir) for f in fs if f.endswith('.shp')), None)
                if not shp_file: raise ValueError("No SHP")
                gdf = gpd.read_file(shp_file).to_crs(epsg=4326)
                gdf_proj = gdf.to_crs(epsg=3035)
                gdf['area_sq_m'] = gdf_proj.geometry.area
            if database.is_closed(): database.connect()
            with database.atomic():
                for _, row in gdf.iterrows():
                    props = row.drop('geometry').to_dict()
                    cleaned = {k: (None if isinstance(v, float) and math.isnan(v) else v) for k, v in props.items()}
                    field_name = cleaned.get('Field_Name') or cleaned.get('name') or \
                                 cleaned.get('NAME') or cleaned.get('Name') or \
                                 cleaned.get('id') or cleaned.get('ID') or "Поле"
                    Field.create(name=str(field_name), geometry_wkt=row.geometry.wkt, properties_json=json.dumps(cleaned))
            self.write({"message": "OK"})
        finally:
            if not database.is_closed(): database.close()
