/**
 * Управление картами Leaflet (главная, детали, fullscreen).
 */
export class MapManager {
  constructor() {
    this.instance = null;
    this.editableLayers = null;
    this.baseLayers = {};
    this.detailInstance = null;
    this.fullscreenMap = null;
    this.currentFieldGeometry = null;
    this.currentZones = [];
    this.isFullscreenMode = false;
    this._updateZonesRetries = 0;
    this._fullscreenKeyHandler = null;
  }

  initMainMap(containerId, onCreated, onEdited, onDeleted) {
    if ($(`#${containerId}`).length === 0 || this.instance) return;

    this.instance = L.map(containerId).setView([48.66, 19.69], 8);
    this.baseLayers.light = L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", { attribution: "&copy; OS" });
    this.baseLayers.dark = L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", { attribution: "&copy; CARTO" });

    const theme = localStorage.getItem("theme") || "light";
    (theme === "dark" ? this.baseLayers.dark : this.baseLayers.light).addTo(this.instance);

    this.editableLayers = new L.FeatureGroup();
    this.instance.addLayer(this.editableLayers);

    const drawControl = new L.Control.Draw({
      edit: { featureGroup: this.editableLayers },
      draw: { polygon: { allowIntersection: false, showArea: true, shapeOptions: { color: "#007BFF" } }, polyline: false, rectangle: false, circle: false, marker: false, circlemarker: false }
    });
    this.instance.addControl(drawControl);

    if (onCreated) this.instance.on(L.Draw.Event.CREATED, onCreated);
    if (onEdited) this.instance.on(L.Draw.Event.EDITED, onEdited);
    if (onDeleted) this.instance.on(L.Draw.Event.DELETED, onDeleted);

    this.instance.locate({ setView: true, maxZoom: 16 });

    const locateBtn = L.control({ position: "topleft" });
    locateBtn.onAdd = () => {
      const btn = L.DomUtil.create("button", "leaflet-bar leaflet-control leaflet-control-locate");
      btn.innerHTML = '<i class="fas fa-crosshairs"></i>';
      btn.title = "Моё местоположение";
      btn.style.cssText = "width:34px;height:34px;display:flex;align-items:center;justify-content:center;background:#fff;border:none;cursor:pointer;font-size:16px;";
      L.DomEvent.disableClickPropagation(btn);
      btn.addEventListener("click", () => {
        btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
        this.instance.locate({ setView: true, maxZoom: 16 });
      });
      return btn;
    };
    locateBtn.addTo(this.instance);

    this.instance.on("locationfound", () => {
      const btn = document.querySelector(".leaflet-control-locate");
      if (btn) btn.innerHTML = '<i class="fas fa-crosshairs"></i>';
    });
    this.instance.on("locationerror", () => {
      const btn = document.querySelector(".leaflet-control-locate");
      if (btn) btn.innerHTML = '<i class="fas fa-crosshairs"></i>';
    });
  }

  updateTheme(isDark) {
    if (!this.instance) return;
    const { light, dark } = this.baseLayers;
    if (isDark) { this.instance.removeLayer(light); dark.addTo(this.instance); }
    else { this.instance.removeLayer(dark); light.addTo(this.instance); }
  }

  renderFields(geojsonData, onDownloadKmz, onFieldClick) {
    if (!this.editableLayers) return;
    this.editableLayers.clearLayers();
    if (!geojsonData.features) return;

    const isSmallScreen = window.innerWidth <= 600;

    L.geoJSON(geojsonData, {
      style: { color: "#007BFF", weight: 2, fillOpacity: 0.3 },
      onEachFeature: (feature, layer) => {
        const props = feature.properties || {};

        if (isSmallScreen) {
          const area = props.area_sq_m ? (props.area_sq_m / 10000).toFixed(2) + " га" : "N/A";
          layer.bindPopup(`<b>${props.name || "Поле"}</b><br>Площадь: ${area}<hr><button class="btn btn-primary btn-sm btn-pop-kmz w-full" data-id="${props.db_id}"><i class="fas fa-file-download"></i> Скачать KMZ</button>`);
        } else if (onFieldClick) {
          layer.on("click", (e) => {
            L.DomEvent.stopPropagation(e);
            onFieldClick(props.db_id);
          });
        } else {
          const area = props.area_sq_m ? (props.area_sq_m / 10000).toFixed(2) + " га" : "N/A";
          layer.bindPopup(`<b>${props.name || "Поле"}</b><br>Площадь: ${area}<hr><button class="btn btn-primary btn-sm btn-pop-kmz w-full" data-id="${props.db_id}"><i class="fas fa-file-download"></i> Скачать KMZ</button>`);
        }

        if (isSmallScreen && onFieldClick) {
          layer.on("click", (e) => {
            const bar = document.getElementById("quick-export-bar");
            const nameEl = document.getElementById("qe-field-name");
            const dlBtn = document.getElementById("qe-download-kmz");
            const detailBtn = document.getElementById("qe-open-detail");
            if (bar && nameEl && dlBtn && detailBtn) {
              nameEl.textContent = props.name || "Поле";
              dlBtn.onclick = () => {
                if (window.downloadKmzWithSettings) window.downloadKmzWithSettings(props.db_id);
              };
              detailBtn.onclick = () => onFieldClick(props.db_id);
              bar.classList.add("visible");
            }
          });
        }

        this.editableLayers.addLayer(layer);
      }
    });

    $(document).off("click", ".btn-pop-kmz").on("click", ".btn-pop-kmz", (e) => {
      onDownloadKmz($(e.currentTarget).data("id"));
    });

    if (this.editableLayers.getBounds().isValid()) {
      this.instance.fitBounds(this.editableLayers.getBounds());
    }
  }

  initDetailMap(containerId, geometry, zones = [], fullscreen = false) {
    if (this.detailInstance) this.detailInstance.remove();

    this.currentFieldGeometry = geometry;
    this.isFullscreenMode = fullscreen;

    this.detailInstance = L.map(containerId, {
      zoomControl: false,
      attributionControl: !fullscreen,
      zoomSnap: fullscreen ? 0 : 1
    });

    if (!fullscreen) {
      L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png").addTo(this.detailInstance);
    } else {
      $(`#${containerId}`).css("background", "#1a1a2e");
    }

    L.geoJSON(geometry, {
      style: { color: "#007BFF", weight: 3, fillOpacity: 0 }
    }).addTo(this.detailInstance);

    if (zones && zones.length > 0) {
      zones.forEach(zone => {
        L.geoJSON(zone.geometry, {
          style: { color: zone.color, weight: 1, fillOpacity: 0.6 }
        }).addTo(this.detailInstance);
      });
    }

    this.detailInstance.fitBounds(geometry.bbox || L.geoJSON(geometry).getBounds(), { padding: [20, 20] });
    setTimeout(() => this.detailInstance.invalidateSize(), 100);
  }

  toggleBaseLayer(fullscreen) {
    if (!this.detailInstance) return;
    this.isFullscreenMode = fullscreen;

    this.detailInstance.eachLayer(layer => {
      if (layer instanceof L.TileLayer) this.detailInstance.removeLayer(layer);
    });

    if (!fullscreen) {
      L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png").addTo(this.detailInstance);
      $(this.detailInstance.getContainer()).css("background", "");
    } else {
      $(this.detailInstance.getContainer()).css("background", "#1a1a2e");
    }

    if (this.currentFieldGeometry) {
      this.detailInstance.eachLayer(layer => {
        if (layer instanceof L.TileLayer) return;
        if (layer instanceof L.Control) return;
        this.detailInstance.removeLayer(layer);
      });

      L.geoJSON(this.currentFieldGeometry, {
        style: { color: "#007BFF", weight: 3, fillOpacity: 0 }
      }).addTo(this.detailInstance);

      if (this.currentZones && this.currentZones.length > 0) {
        this.currentZones.forEach(zone => {
          L.geoJSON(zone.geometry, {
            style: { color: zone.color, weight: 1, fillOpacity: 0.6 }
          }).addTo(this.detailInstance);
        });
      }
    }
  }

  updateZones(zones = []) {
    if (!this.detailInstance) {
      if (this._updateZonesRetries < 15) {
        this._updateZonesRetries++;
        console.warn(`[MapManager] detailInstance не инициализирован, попытка ${this._updateZonesRetries}/15 через 200ms`);
        setTimeout(() => this.updateZones(zones), 200);
      } else {
        console.error("[MapManager] detailInstance так и не создан после 15 попыток");
        this._updateZonesRetries = 0;
      }
      return;
    }
    this._updateZonesRetries = 0;

    console.log("[MapManager.updateZones] Обновление зон:", zones.length);
    this.currentZones = zones;

    this.detailInstance.eachLayer(layer => {
      if (layer instanceof L.TileLayer) return;
      if (layer instanceof L.Control) return;
      this.detailInstance.removeLayer(layer);
    });

    if (this.currentFieldGeometry) {
      L.geoJSON(this.currentFieldGeometry, {
        style: { color: "#007BFF", weight: 3, fillOpacity: 0 }
      }).addTo(this.detailInstance);
    }

    if (zones && zones.length > 0) {
      zones.forEach(zone => {
        console.log("[MapManager] Рисуем зону:", zone.name, zone.color);
        L.geoJSON(zone.geometry, {
          style: { color: zone.color, weight: 1, fillOpacity: 0.6 }
        }).addTo(this.detailInstance);
      });
    }

    setTimeout(() => this.detailInstance.invalidateSize(), 100);
  }

  updateFieldGeometry(geometry, zones = []) {
    this.currentFieldGeometry = geometry;
    this.updateZones(zones);
  }

  enterFullscreen() {
    if (this.fullscreenMap) return;

    const overlay = document.createElement("div");
    overlay.id = "map-fullscreen-overlay";
    overlay.style.cssText = "position:fixed;top:0;left:0;right:0;bottom:0;z-index:9999;background:#1a1a2e;";
    document.body.appendChild(overlay);

    const toolbar = document.createElement("div");
    toolbar.id = "fs-toolbar";
    toolbar.style.cssText = "position:fixed;top:12px;right:12px;z-index:10000;display:flex;flex-direction:column;gap:4px;background:var(--card-bg);border-radius:8px;padding:4px;box-shadow:0 2px 8px rgba(0,0,0,0.3);";
    toolbar.innerHTML = `
      <button id="fs-center-btn" class="btn-icon" title="Отцентрировать" style="background:var(--card-bg);border:1px solid var(--border-color);cursor:pointer;padding:6px 10px;border-radius:6px;font-size:14px;display:flex;align-items:center;justify-content:center;width:36px;height:36px;color:var(--text-color);">
        <i class="fas fa-crosshairs"></i>
      </button>
      <button id="fs-close-btn" class="btn-icon" title="Свернуть (Esc)" style="background:var(--card-bg);border:1px solid var(--border-color);cursor:pointer;padding:6px 10px;border-radius:6px;font-size:14px;display:flex;align-items:center;justify-content:center;width:36px;height:36px;color:var(--text-color);">
        <i class="fas fa-compress"></i>
      </button>
    `;
    document.body.appendChild(toolbar);

    this.fullscreenMap = L.map(overlay, {
      zoomControl: false,
      attributionControl: true
    });

    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png").addTo(this.fullscreenMap);

    if (this.currentFieldGeometry) {
      L.geoJSON(this.currentFieldGeometry, {
        style: { color: "#007BFF", weight: 3, fillOpacity: 0 }
      }).addTo(this.fullscreenMap);

      if (this.currentZones && this.currentZones.length > 0) {
        this.currentZones.forEach(zone => {
          L.geoJSON(zone.geometry, {
            style: { color: zone.color, weight: 1, fillOpacity: 0.6 }
          }).addTo(this.fullscreenMap);
        });
      }

      const bounds = L.geoJSON(this.currentFieldGeometry).getBounds();
      this.fullscreenMap.fitBounds(bounds, { padding: [40, 40] });
    }

    setTimeout(() => this.fullscreenMap.invalidateSize(), 100);

    document.getElementById("fs-close-btn").onclick = () => this.exitFullscreen();
    document.getElementById("fs-center-btn").onclick = () => {
      if (this.currentFieldGeometry) {
        const b = L.geoJSON(this.currentFieldGeometry).getBounds();
        this.fullscreenMap.fitBounds(b, { padding: [40, 40] });
      }
    };

    this._fullscreenKeyHandler = (e) => {
      if (e.key === "Escape") this.exitFullscreen();
    };
    document.addEventListener("keydown", this._fullscreenKeyHandler);
  }

  exitFullscreen() {
    if (!this.fullscreenMap) return;
    this.fullscreenMap.remove();
    this.fullscreenMap = null;

    const overlay = document.getElementById("map-fullscreen-overlay");
    if (overlay) overlay.remove();

    const toolbar = document.getElementById("fs-toolbar");
    if (toolbar) toolbar.remove();

    if (this._fullscreenKeyHandler) {
      document.removeEventListener("keydown", this._fullscreenKeyHandler);
      this._fullscreenKeyHandler = null;
    }

    if (this.detailInstance) {
      setTimeout(() => this.detailInstance.invalidateSize(), 200);
    }
  }
}

const mapManager = new MapManager();
export default mapManager;
window.MapManager = mapManager;
