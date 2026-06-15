const MapManager = {
  instance: null,
  editableLayers: null,
  baseLayers: {},
  detailInstance: null,
  fullscreenMap: null,

  initMainMap: (containerId, onCreated, onEdited, onDeleted) => {
    if ($(`#${containerId}`).length === 0 || MapManager.instance) return;

    MapManager.instance = L.map(containerId).setView([48.66, 19.69], 8);
    MapManager.baseLayers.light = L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", { attribution: "&copy; OS" });
    MapManager.baseLayers.dark = L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", { attribution: "&copy; CARTO" });

    const theme = localStorage.getItem("theme") || "light";
    (theme === "dark" ? MapManager.baseLayers.dark : MapManager.baseLayers.light).addTo(MapManager.instance);

    MapManager.editableLayers = new L.FeatureGroup();
    MapManager.instance.addLayer(MapManager.editableLayers);

    const drawControl = new L.Control.Draw({
      edit: { featureGroup: MapManager.editableLayers },
      draw: { polygon: { allowIntersection: false, showArea: true, shapeOptions: { color: "#007BFF" } }, polyline: false, rectangle: false, circle: false, marker: false, circlemarker: false }
    });
    MapManager.instance.addControl(drawControl);

    if (onCreated) MapManager.instance.on(L.Draw.Event.CREATED, onCreated);
    if (onEdited) MapManager.instance.on(L.Draw.Event.EDITED, onEdited);
    if (onDeleted) MapManager.instance.on(L.Draw.Event.DELETED, onDeleted);

    MapManager.instance.locate({setView: true, maxZoom: 16});
  },

  updateTheme: (isDark) => {
    if (!MapManager.instance) return;
    const { light, dark } = MapManager.baseLayers;
    if (isDark) { MapManager.instance.removeLayer(light); dark.addTo(MapManager.instance); }
    else { MapManager.instance.removeLayer(dark); light.addTo(MapManager.instance); }
  },

  renderFields: (geojsonData, onDownloadKmz, onFieldClick) => {
    if (!MapManager.editableLayers) return;
    MapManager.editableLayers.clearLayers();
    if (!geojsonData.features) return;

    L.geoJSON(geojsonData, {
      style: { color: "#007BFF", weight: 2, fillOpacity: 0.3 },
      onEachFeature: (feature, layer) => {
        const props = feature.properties || {};

        // Вместо попапа вешаем клик, если передан обработчик
        if (onFieldClick) {
          layer.on("click", (e) => {
            L.DomEvent.stopPropagation(e);
            onFieldClick(props.db_id);
          });
        } else {
          const area = props.area_sq_m ? (props.area_sq_m / 10000).toFixed(2) + " га" : "N/A";
          layer.bindPopup(`<b>${props.name || "Поле"}</b><br>Площадь: ${area}<hr><button class="btn btn-primary btn-sm btn-pop-kmz w-full" data-id="${props.db_id}"><i class="fas fa-file-download"></i> Скачать KMZ</button>`);
        }

        MapManager.editableLayers.addLayer(layer);
      }
    });

    $(document).off("click", ".btn-pop-kmz").on("click", ".btn-pop-kmz", function() {
      onDownloadKmz($(this).data("id"));
    });

    if (MapManager.editableLayers.getBounds().isValid()) {
      MapManager.instance.fitBounds(MapManager.editableLayers.getBounds());
    }
  },

  /**
   * Инициализирует карту деталей поля.
   * @param {string} containerId - ID контейнера карты.
   * @param {Object} geometry - GeoJSON геометрия поля.
   * @param {Array} zones - Массив зон для отображения.
   * @param {boolean} fullscreen - Режим без подложки (только поле).
   */
  initDetailMap: (containerId, geometry, zones = [], fullscreen = false) => {
    if (MapManager.detailInstance) { MapManager.detailInstance.remove(); }

    // Сохраняем геометрию поля для последующего обновления
    MapManager.currentFieldGeometry = geometry;
    MapManager.isFullscreenMode = fullscreen;

    MapManager.detailInstance = L.map(containerId, {
      zoomControl: false,
      attributionControl: !fullscreen, // Скрываем attribution в fullscreen
      zoomSnap: fullscreen ? 0 : 1
    });

    // Добавляем подложку только если не fullscreen режим
    if (!fullscreen) {
      L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png").addTo(MapManager.detailInstance);
    } else {
      // В fullscreen режиме устанавливаем тёмный фон через CSS
      $(`#${containerId}`).css('background', '#1a1a2e');
    }

    // Сначала рисуем контур поля (он будет ПОД зонами)
    L.geoJSON(geometry, {
      style: { color: "#007BFF", weight: 3, fillOpacity: 0 }
    }).addTo(MapManager.detailInstance);

    // Затем рисуем зоны ПОВЕРХ контура
    if (zones && zones.length > 0) {
      zones.forEach(zone => {
        L.geoJSON(zone.geometry, {
          style: {
            color: zone.color,
            weight: 1,
            fillOpacity: 0.6
          }
        }).addTo(MapManager.detailInstance);
      });
    }

    MapManager.detailInstance.fitBounds(geometry.bbox || L.geoJSON(geometry).getBounds(), { padding: [20, 20] });

    setTimeout(() => MapManager.detailInstance.invalidateSize(), 100);
  },

  /**
   * Переключает режим отображения подложки.
   * @param {boolean} fullscreen - true для режима без подложки.
   */
  toggleBaseLayer: (fullscreen) => {
    if (!MapManager.detailInstance) return;

    MapManager.isFullscreenMode = fullscreen;

    // Удаляем все тайловые слои
    MapManager.detailInstance.eachLayer(layer => {
      if (layer instanceof L.TileLayer) {
        MapManager.detailInstance.removeLayer(layer);
      }
    });

    // Добавляем подложку только если не fullscreen
    if (!fullscreen) {
      L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png").addTo(MapManager.detailInstance);
      // Убираем тёмный фон
      $(MapManager.detailInstance.getContainer()).css('background', '');
    } else {
      // В fullscreen режиме устанавливаем тёмный фон
      $(MapManager.detailInstance.getContainer()).css('background', '#1a1a2e');
    }

    // Перерисовываем контур поля и зоны в правильном порядке
    if (MapManager.currentFieldGeometry) {
      // Сначала удаляем старые слои (кроме подложки и контролов)
      MapManager.detailInstance.eachLayer(layer => {
        if (layer instanceof L.TileLayer) return;
        if (layer instanceof L.Control) return;
        MapManager.detailInstance.removeLayer(layer);
      });

      // Рисуем контур
      L.geoJSON(MapManager.currentFieldGeometry, {
        style: { color: "#007BFF", weight: 3, fillOpacity: 0 }
      }).addTo(MapManager.detailInstance);

      // Рисуем зоны поверх
      if (MapManager.currentZones && MapManager.currentZones.length > 0) {
        MapManager.currentZones.forEach(zone => {
          L.geoJSON(zone.geometry, {
            style: {
              color: zone.color,
              weight: 1,
              fillOpacity: 0.6
            }
          }).addTo(MapManager.detailInstance);
        });
      }
    }
  },

  /**
   * Обновляет зоны на карте деталей.
   * @param {Array} zones - Массив зон для отображения.
   */
  _updateZonesRetries: 0,

  updateZones: (zones = []) => {
    if (!MapManager.detailInstance) {
      if (MapManager._updateZonesRetries < 15) {
        MapManager._updateZonesRetries++;
        console.warn(`[MapManager] detailInstance не инициализирован, попытка ${MapManager._updateZonesRetries}/15 через 200ms`);
        setTimeout(() => MapManager.updateZones(zones), 200);
      } else {
        console.error('[MapManager] detailInstance так и не создан после 15 попыток');
        MapManager._updateZonesRetries = 0;
      }
      return;
    }
    MapManager._updateZonesRetries = 0;

    console.log('[MapManager.updateZones] Обновление зон:', zones.length);

    // Сохраняем текущие зоны
    MapManager.currentZones = zones;

    // Очищаем все слои кроме подложки и attribution
    MapManager.detailInstance.eachLayer(layer => {
      if (layer instanceof L.TileLayer) return; // Сохраняем подложку
      if (layer instanceof L.Control) return; // Сохраняем контролы
      // Удаляем полигоны и GeoJSON слои
      MapManager.detailInstance.removeLayer(layer);
    });

    // Сначала рисуем контур поля (он будет ПОД зонами)
    if (MapManager.currentFieldGeometry) {
      L.geoJSON(MapManager.currentFieldGeometry, {
        style: { color: "#007BFF", weight: 3, fillOpacity: 0 }
      }).addTo(MapManager.detailInstance);
    }

    // Рисуем новые зоны ПОВЕРХ контура
    if (zones && zones.length > 0) {
      zones.forEach(zone => {
        console.log('[MapManager] Рисуем зону:', zone.name, zone.color);
        L.geoJSON(zone.geometry, {
          style: {
            color: zone.color,
            weight: 1,
            fillOpacity: 0.6
          }
        }).addTo(MapManager.detailInstance);
      });
    }

    setTimeout(() => MapManager.detailInstance.invalidateSize(), 100);
  },

  /**
   * Обновляет геометрию поля и зоны.
   * @param {Object} geometry - GeoJSON геометрия поля.
   * @param {Array} zones - Массив зон.
   */
  updateFieldGeometry: (geometry, zones = []) => {
    MapManager.currentFieldGeometry = geometry;
    MapManager.updateZones(zones);
  },

  enterFullscreen: () => {
    if (MapManager.fullscreenMap) return;

    const overlay = document.createElement('div');
    overlay.id = 'map-fullscreen-overlay';
    overlay.style.cssText = 'position:fixed;top:0;left:0;right:0;bottom:0;z-index:9999;background:#1a1a2e;';
    document.body.appendChild(overlay);

    const toolbar = document.createElement('div');
    toolbar.id = 'fs-toolbar';
    toolbar.style.cssText = 'position:fixed;top:12px;right:12px;z-index:10000;display:flex;flex-direction:column;gap:4px;background:var(--card-bg);border-radius:8px;padding:4px;box-shadow:0 2px 8px rgba(0,0,0,0.3);';
    toolbar.innerHTML = `
      <button id="fs-center-btn" class="btn-icon" title="Отцентрировать" style="background:var(--card-bg);border:1px solid var(--border-color);cursor:pointer;padding:6px 10px;border-radius:6px;font-size:14px;display:flex;align-items:center;justify-content:center;width:36px;height:36px;color:var(--text-color);">
        <i class="fas fa-crosshairs"></i>
      </button>
      <button id="fs-close-btn" class="btn-icon" title="Свернуть (Esc)" style="background:var(--card-bg);border:1px solid var(--border-color);cursor:pointer;padding:6px 10px;border-radius:6px;font-size:14px;display:flex;align-items:center;justify-content:center;width:36px;height:36px;color:var(--text-color);">
        <i class="fas fa-compress"></i>
      </button>
    `;
    document.body.appendChild(toolbar);

    MapManager.fullscreenMap = L.map(overlay, {
      zoomControl: false,
      attributionControl: true
    });

    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png").addTo(MapManager.fullscreenMap);

    if (MapManager.currentFieldGeometry) {
      L.geoJSON(MapManager.currentFieldGeometry, {
        style: { color: "#007BFF", weight: 3, fillOpacity: 0 }
      }).addTo(MapManager.fullscreenMap);

      if (MapManager.currentZones && MapManager.currentZones.length > 0) {
        MapManager.currentZones.forEach(zone => {
          L.geoJSON(zone.geometry, {
            style: { color: zone.color, weight: 1, fillOpacity: 0.6 }
          }).addTo(MapManager.fullscreenMap);
        });
      }

      const bounds = L.geoJSON(MapManager.currentFieldGeometry).getBounds();
      MapManager.fullscreenMap.fitBounds(bounds, { padding: [40, 40] });
    }

    setTimeout(() => MapManager.fullscreenMap.invalidateSize(), 100);

    document.getElementById('fs-close-btn').onclick = () => MapManager.exitFullscreen();
    document.getElementById('fs-center-btn').onclick = () => {
      if (MapManager.currentFieldGeometry) {
        const b = L.geoJSON(MapManager.currentFieldGeometry).getBounds();
        MapManager.fullscreenMap.fitBounds(b, { padding: [40, 40] });
      }
    };

    MapManager._fullscreenKeyHandler = (e) => {
      if (e.key === 'Escape') MapManager.exitFullscreen();
    };
    document.addEventListener('keydown', MapManager._fullscreenKeyHandler);
  },

  exitFullscreen: () => {
    if (!MapManager.fullscreenMap) return;
    MapManager.fullscreenMap.remove();
    MapManager.fullscreenMap = null;

    const overlay = document.getElementById('map-fullscreen-overlay');
    if (overlay) overlay.remove();

    const toolbar = document.getElementById('fs-toolbar');
    if (toolbar) toolbar.remove();

    if (MapManager._fullscreenKeyHandler) {
      document.removeEventListener('keydown', MapManager._fullscreenKeyHandler);
      MapManager._fullscreenKeyHandler = null;
    }

    if (MapManager.detailInstance) {
      setTimeout(() => MapManager.detailInstance.invalidateSize(), 200);
    }
  }
};

export default MapManager;
window.MapManager = MapManager;
