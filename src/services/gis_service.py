import geopandas as gpd


def calculate_accurate_area(poly):
    """
    Расчет точной площади в квадратных метрах.
    Используется EPSG:3035 (ETRS89-extended / LAEA Europe).
    """
    temp_gdf = gpd.GeoDataFrame([{'geometry': poly}], crs="EPSG:4326")
    temp_gdf_projected = temp_gdf.to_crs(epsg=3035)
    return temp_gdf_projected.geometry.area.iloc[0]
