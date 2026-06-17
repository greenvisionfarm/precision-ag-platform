/**
 * Scans — управление списком сканов поля.
 */
import API from "./api.js";
import { showMessage } from "./utils.js";
import { initNDVIChart, destroyChart, compareSelectedScans } from "./ndvi-chart.js";
import { loadScanZones } from "./zones.js";

let _boundDelegation = false;

export function loadFieldScans(fieldId, state) {
  API.getFieldScans(fieldId).then(data => {
    state.allScans = data.scans || [];

    if (state.allScans.length === 0) {
      $("#scans-selector").hide();
      $("#ndvi-processing-msg").hide();
      $("#comparison-result").hide();
      return;
    }

    $("#scans-selector").show();
    const $list = $("#scan-list").empty();

    if ($("#btn-compare-scans").length === 0) {
      $("#scans-selector label").after(`
        <button id="btn-compare-scans" class="btn btn-sm btn-outline-primary" style="float: right; margin-top: -5px;">
          <i class="fas fa-columns"></i> Сравнить
        </button>
      `);
    }

    state.currentScanId = null;
    state.currentScan = null;
    $("#comparison-result").hide();

    const hasProcessingScans = state.allScans.some(scan => !scan.processed);

    state.allScans.forEach((scan, index) => {
      const date = new Date(scan.uploaded_at).toLocaleDateString("ru-RU", { day: "numeric", month: "long", year: "numeric" });
      const status = scan.processed ? "✓" : "⏳";
      const zones = scan.has_zones ? `${scan.zones_count || 3} зоны` : "Нет зон";
      const ndvi = scan.ndvi_avg ? `NDVI: ${scan.ndvi_avg.toFixed(2)}` : "";

      const $item = $(`
        <div class="scan-item ${index === 0 ? "active" : ""}" data-scan-id="${scan.id}">
          <div class="scan-checkbox-wrapper">
            <input type="checkbox" class="scan-checkbox" value="${scan.id}">
          </div>
          <div class="scan-info">
            <span class="scan-status">${status}</span>
            <span class="scan-date">${date}</span>
            <span class="scan-zones">${zones}</span>
            <span class="scan-ndvi">${ndvi}</span>
          </div>
          <button class="btn-delete-scan" data-field-id="${fieldId}" data-scan-id="${scan.id}" title="Удалить снимок">
            <i class="fas fa-trash"></i>
          </button>
        </div>
      `);

      $list.append($item);

      if (!state.currentScanId && scan.processed && scan.has_zones) {
        state.currentScanId = scan.id;
        state.currentScan = scan;
        $item.addClass("active").siblings().removeClass("active");
      }
    });

    // Event delegation — привязываем один раз
    if (!_boundDelegation) {
      _boundDelegation = true;

      $(document).on("click", "#scan-list .scan-info", function() {
        const scanId = parseInt($(this).closest(".scan-item").data("scan-id"));
        if (scanId) selectScan(scanId, state);
      });

      $(document).on("click", "#scan-list .btn-delete-scan", function(e) {
        e.stopPropagation();
        const fieldId = parseInt($(this).data("field-id"));
        const scanId = parseInt($(this).data("scan-id"));
        if (fieldId && scanId) deleteScan(fieldId, scanId, state);
      });

      $(document).on("click", "#scan-list .scan-checkbox", function(e) {
        e.stopPropagation();
      });

      $(document).on("click", "#btn-compare-scans", function() {
        compareSelectedScans(state.currentFieldId);
      });
    }

    initNDVIChart(state.allScans);

    if (!state.currentScanId && state.allScans.length > 0) {
      state.currentScanId = state.allScans[0].id;
      state.currentScan = state.allScans[0];
    }

    if (hasProcessingScans && !state.currentScanId) {
      $("#ndvi-processing-msg").show();
      startProcessingPoll(fieldId, state);
    } else {
      $("#ndvi-processing-msg").hide();
    }

    if (state.currentScanId) {
      loadScanZones(state.currentScanId, state);
    }
  }).fail(err => {
    console.error("Ошибка загрузки сканов:", err);
  });
}

function startProcessingPoll(fieldId, state) {
  if (state.processingPollInterval) clearInterval(state.processingPollInterval);

  state.processingPollInterval = setInterval(() => {
    API.getFieldScans(fieldId).then(data => {
      const scans = data.scans || [];
      const hasProcessingScans = scans.some(scan => !scan.processed);
      const hasProcessedWithZones = scans.some(scan => scan.processed && scan.has_zones);

      if (hasProcessedWithZones) {
        clearInterval(state.processingPollInterval);
        state.processingPollInterval = null;
        loadFieldScans(fieldId, state);
        showMessage("NDVI обработан! Данные обновлены", "success");
      }

      if (!hasProcessingScans) {
        clearInterval(state.processingPollInterval);
        state.processingPollInterval = null;
        $("#ndvi-processing-msg").hide();
      }
    }).fail(err => {
      console.error("Ошибка polling:", err);
    });
  }, 10000);
}

export function selectScan(scanId, state) {
  state.currentScanId = scanId;
  state.currentScan = state.allScans.find(s => s.id === scanId);

  $(".scan-item").removeClass("active");
  $(`.scan-item[data-scan-id="${scanId}"]`).addClass("active");

  loadScanZones(scanId, state);
}

export function deleteScan(fieldId, scanId, state) {
  Swal.fire({
    title: "Удалить снимок?",
    text: "Все зоны этого снимка будут удалены",
    icon: "warning",
    showCancelButton: true,
    confirmButtonText: "Удалить",
    cancelButtonText: "Отмена"
  }).then(result => {
    if (result.isConfirmed) {
      API.deleteScan(fieldId, scanId).then(data => {
        showMessage(data.message || "Скан удалён", "success");
        loadFieldScans(fieldId, state);
        if (state.currentScanId === scanId) {
          window.MapManager.updateZones([]);
          window.currentFieldDetail?.renderZonesStats([]);
          state.currentScanId = null;
          state.currentScan = null;
        }
      }).fail(err => {
        console.error("Ошибка удаления скана:", err);
        showMessage("Не удалось удалить скан", "error");
      });
    }
  });
}

export function cleanup(state) {
  if (state.processingPollInterval) {
    clearInterval(state.processingPollInterval);
    state.processingPollInterval = null;
  }
  destroyChart();
}
