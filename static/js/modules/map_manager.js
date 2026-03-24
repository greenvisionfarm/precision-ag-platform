const MapManager = {
  instance: null,
  editableLayers: null,
  baseLayers: {},
  detailInstance: null,

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
          layer.bindPopup(`<b>${props.name || "Поле"}</b><br>Площадь: ${area}<hr><button class="btn btn-primary btn-sm btn-pop-kmz" data-id="${props.db_id}" style="width:100%"><i class="fas fa-file-download"></i> Скачать KMZ</button>`);
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

  initDetailMap: (containerId, geometry, zones = []) => {
    if (MapManager.detailInstance) { MapManager.detailInstance.remove(); }

    MapManager.detailInstance = L.map(containerId, { zoomControl: false, attributionControl: false });
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png").addTo(MapManager.detailInstance);

    // Сначала рисуем зоны (если есть), чтобы они были под границей
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

    // Затем рисуем контур поля
    const mainLayer = L.geoJSON(geometry, {
      style: { color: "#007BFF", weight: 3, fillOpacity: zones.length > 0 ? 0 : 0.2 }
    }).addTo(MapManager.detailInstance);

    MapManager.detailInstance.fitBounds(mainLayer.getBounds(), { padding: [20, 20] });

    setTimeout(() => MapManager.detailInstance.invalidateSize(), 100);
  }
};

export default MapManager;
window.MapManager = MapManager;
