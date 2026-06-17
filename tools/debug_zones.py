"""Diagnose zone geometry via API."""
import os, sys, json
from playwright.sync_api import sync_playwright
from shapely.geometry import shape
import numpy as np

BASE_URL = "http://192.168.31.196:8080"

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1400, "height": 900})

        page.goto(f"{BASE_URL}/")
        page.wait_for_load_state("networkidle")
        page.fill("#auth-gate-email", "admin@fieldmapper.test")
        page.fill("#auth-gate-password", "admin")
        page.click("#auth-gate-form button[type=submit]")
        page.wait_for_timeout(3000)

        # Get field detail (has zones)
        field = page.evaluate("""async () => {
            const r = await fetch('/api/field/5');
            return await r.json();
        }""")

        field_geom = shape(field['geometry'])
        print(f"Field area: {field_geom.area:.6f} (sq deg)")
        print(f"Field bounds: {field_geom.bounds}")

        zones = field.get('zones', [])
        print(f"\nZones from field detail: {len(zones)}")
        for z in zones:
            geom = shape(z['geometry'])
            print(f"  '{z.get('name')}' type={geom.geom_type} area={geom.area:.6f} ndvi={z.get('avg_ndvi')}")

        # Get scan zones
        scans_resp = page.evaluate("""async () => {
            const r = await fetch('/api/field/5/scans');
            return await r.json();
        }""")
        scans = scans_resp.get('scans', [])

        for s in scans:
            sid = s.get('id')
            resp = page.evaluate(f"""async () => {{
                const r = await fetch('/api/scan/{sid}/zones');
                return await r.json();
            }}""")
            zones = resp.get('zones', [])
            print(f"\nScan {sid} zones: {len(zones)}")
            for z in zones:
                geom = shape(z['geometry'])
                bounds = geom.bounds
                # Check if zone is inside field
                intersection = geom.intersection(field_geom)
                overlap_pct = (intersection.area / geom.area * 100) if geom.area > 0 else 0
                print(f"  '{z.get('name')}' area={geom.area:.6f} bounds={[round(x,4) for x in bounds]} overlap_field={overlap_pct:.1f}%")
                # Count coordinates
                coords = list(geom.coords) if geom.geom_type == 'Polygon' else []
                print(f"    coords={len(coords)}")

        browser.close()

if __name__ == "__main__":
    main()
