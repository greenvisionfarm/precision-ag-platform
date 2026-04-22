
import rasterio
import numpy as np
import pandas as pd
import logging
import os

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

class VRAMapper:
    def __init__(self, ndvi_path, ndre_path):
        self.ndvi_path = ndvi_path
        self.ndre_path = ndre_path

    def generate_vra(self, target_avg_rate_kg_ha=200, output_path="vra_map.tif"):
        logger.info(f"Loading indices...")
        with rasterio.open(self.ndvi_path) as s_ndvi:
            ndvi = s_ndvi.read(1)
            profile = s_ndvi.profile
            res_x, res_y = s_ndvi.res

        with rasterio.open(self.ndre_path) as s_ndre:
            ndre = s_ndre.read(1)

        # 1. Composite Health Index (70/30)
        # Filter out invalid values and non-field areas (NDVI < 0.2)
        mask = (ndvi > 0.2) & (ndvi <= 1.0)
        chi = 0.7 * ndvi + 0.3 * ndre
        
        valid_chi = chi[mask]
        if len(valid_chi) == 0:
            logger.error("No valid vegetation detected!")
            return

        # 2. Define Zones based on percentiles
        p20 = np.percentile(valid_chi, 20)
        p50 = np.percentile(valid_chi, 50)
        p80 = np.percentile(valid_chi, 80)
        
        logger.info(f"Zones thresholds (CHI): P20={p20:.2f}, P50={p50:.2f}, P80={p80:.2f}")

        # Zone logic: 1-Low, 2-MidLow, 3-MidHigh, 4-High
        zones = np.zeros_like(chi, dtype=np.uint8)
        zones[mask & (chi <= p20)] = 1
        zones[mask & (chi > p20) & (chi <= p50)] = 2
        zones[mask & (chi > p50) & (chi <= p80)] = 3
        zones[mask & (chi > p80)] = 4

        # 3. Initial Multipliers (Compensatory Strategy)
        multipliers = {
            1: 1.2, # Poor areas get more
            2: 1.0, # Base
            3: 0.9, # Maintenance
            4: 0.8, # Saving
            0: 0.0  # Non-field
        }

        # 4. Mass Balance Calculation
        pixel_area_m2 = abs(res_x * res_y)
        pixel_area_ha = pixel_area_m2 / 10000.0
        field_area_ha = np.sum(mask) * pixel_area_ha
        
        target_total_mass_kg = target_avg_rate_kg_ha * field_area_ha
        
        # Calculate uncorrected total mass with base multipliers
        raw_total_mass = 0
        zone_areas_ha = {}
        for z in range(1, 5):
            count = np.sum(zones == z)
            area_ha = count * pixel_area_ha
            zone_areas_ha[z] = area_ha
            raw_total_mass += area_ha * multipliers[z] * target_avg_rate_kg_ha

        # Correction factor to match exact target mass
        correction_factor = target_total_mass_kg / raw_total_mass
        final_rates = {z: multipliers[z] * target_avg_rate_kg_ha * correction_factor for z in range(1, 5)}
        final_rates[0] = 0.0

        logger.info(f"Field Area: {field_area_ha:.2f} ha")
        logger.info(f"Target Total Mass: {target_total_mass_kg:.1f} kg")
        
        print("\n=== VRA ZONE SUMMARY ===")
        print(f"{'Zone':<10} | {'Area (ha)':<10} | {'Rate (kg/ha)':<15} | {'Multiplier'}")
        print("-" * 55)
        for z in range(1, 5):
            print(f"Zone {z:<5} | {zone_areas_ha[z]:<10.2f} | {final_rates[z]:<15.1f} | {multipliers[z]:.2f}x")

        # 5. Create VRA Map
        vra_map = np.zeros_like(zones, dtype=np.float32)
        for z, rate in final_rates.items():
            vra_map[zones == z] = rate

        # 6. Safety Check: Total Mass Verification
        actual_total_mass = np.sum(vra_map) * pixel_area_ha
        error_pct = abs(actual_total_mass - target_total_mass_kg) / target_total_mass_kg * 100
        
        print(f"\nMass Balance Check: {actual_total_mass:.1f} kg (Error: {error_pct:.4f}%)")

        # Save to GeoTIFF
        profile.update(dtype=rasterio.float32, count=1, nodata=0)
        with rasterio.open(output_path, 'w', **profile) as dst:
            dst.write(vra_map, 1)
        
        logger.info(f"VRA Map saved to {output_path}")

if __name__ == "__main__":
    mapper = VRAMapper("ndvi_final_corrected.tif", "ndre_final_corrected.tif")
    mapper.generate_vra(target_avg_rate_kg_ha=200, output_path="vra_prescription_200kg.tif")
