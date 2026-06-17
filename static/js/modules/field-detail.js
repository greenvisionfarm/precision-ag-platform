/**
 * Field Detail — оркестратор для деталей поля.
 * Делегирует подмодулям: scans, zones, ndvi-chart, journal, export.
 */
import API from "./api.js";
import { loadFieldScans, cleanup as _cleanupScans } from "./scans.js";
import { renderZonesStats } from "./zones.js";
import { loadJournal, deleteJournalEntry as _deleteJournalEntry, initJournalAddHandler } from "./journal.js";
import { initExportHandlers } from "./export.js";

// Разделяемое состояние view
const state = {
  currentFieldId: null,
  currentScanId: null,
  currentScan: null,
  allScans: [],
  processingPollInterval: null,
};

export function showFieldDetail(id) {
  state.currentFieldId = id;

  _cleanupScans(state);

  API.getField(id).then(field => {
    $("#field-detail-name").text(field.name);
    $("#field-detail-area").text(field.area);
    $("#field-detail-owner").text(field.owner);
    $("#field-detail-status").text(field.land_status);
    $("#field-detail-parcel").text(field.parcel_number);

    if (window.MapManager) {
      window.MapManager.initDetailMap("field-detail-map", field.geometry);
    }

    loadFieldScans(id, state);
    loadJournal(id);
    $("#journal-add-btn").show();
  });
}

// Обёртки для window.* (только то что реально нужно для inline onclick в HTML)
// Убираем selectScan, deleteScan, loadFieldScans, compareSelectedScans — они теперь через event delegation
window.deleteJournalEntry = _deleteJournalEntry;
window.currentFieldDetail = { renderZonesStats: (zones) => renderZonesStats(zones, state) };

// Инициализация обработчиков (вызывается один раз)
initJournalAddHandler(() => state.currentFieldId);
initExportHandlers(() => state.currentFieldId);

// Tabs
$(document).on("click", ".tab-btn", function() {
  const tabId = $(this).data("tab");
  $(".tab-btn").removeClass("active");
  $(this).addClass("active");
  $(".tab-panel").removeClass("active");
  $(`#${tabId}`).addClass("active");
  if (window.MapManager?.detailInstance) {
    setTimeout(() => window.MapManager.detailInstance.invalidateSize(), 100);
  }
});

// Map controls
$(document).on("click", "#map-center-btn", function() {
  if (window.MapManager?.detailInstance && window.MapManager.currentFieldGeometry) {
    const bounds = L.geoJSON(window.MapManager.currentFieldGeometry).getBounds();
    window.MapManager.detailInstance.fitBounds(bounds, { padding: [30, 30], maxZoom: 16 });
  }
});

$(document).on("click", "#map-fullscreen-btn", function() {
  window.MapManager?.enterFullscreen();
});

export { state };
