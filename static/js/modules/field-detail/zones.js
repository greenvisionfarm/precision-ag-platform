/**
 * Zones — отображение зон NDVI и статистика.
 */
import API from "../api.js";
import { showMessage } from "../utils.js";

let availableCrops = [];

export function loadScanZones(scanId, state) {
  API.getScanZones(scanId).then(data => {
    const zones = data.zones || [];
    window.MapManager.updateZones(zones);
    renderZonesStats(zones, state);
  }).catch(err => {
    console.error("Ошибка загрузки зон:", err);
    showMessage("Не удалось загрузить зоны для этого скана", "error");
  });
}

export function renderZonesStats(zones, state) {
  if (!zones || zones.length === 0) {
    $("#zones-stats").hide();
    $("#zones-legend").hide();
    return;
  }

  $("#zones-stats").show();
  $("#zones-legend").show();

  const $prediction = $("#crop-prediction");
  const $select = $("#crop-type-select");
  const $badge = $("#prediction-badge");
  const $confidence = $("#prediction-confidence");

  if ($select.children().length === 0) {
    loadCropsIfNeeded().then(crops => {
      $select.empty();
      crops.forEach(crop => {
        $select.append(`<option value="${crop.id}">${crop.name}</option>`);
      });
      if (state.currentScan) {
        $select.val(state.currentScan.crop_type || "unknown");
      }
    });
  }

  if (state.currentScan) {
    $select.val(state.currentScan.crop_type || "unknown");

    if (state.currentScan.crop_type && state.currentScan.crop_confidence < 1.0) {
      $badge.show();
      $confidence.text(`${Math.round(state.currentScan.crop_confidence * 100)}%`).show();
    } else {
      $badge.hide();
      $confidence.hide();
    }

    $prediction.show();

    $select.off("change").on("change", function() {
      const newCrop = $(this).val();
      API.updateScanCrop(state.currentScanId, newCrop).then(res => {
        showMessage("Культура обновлена", "success");
        state.currentScan.crop_type = newCrop;
        state.currentScan.crop_confidence = 1.0;
        state.currentScan.default_rates = res.default_rates;
        renderZonesStats(zones, state);
      });
    });
  } else {
    $prediction.hide();
  }

  const tbody = $("#zones-table-body").empty();
  zones.forEach(zone => {
    let rate;
    if (state.currentScan && state.currentScan.default_rates && state.currentScan.default_rates.length >= 3) {
      if (zone.avg_ndvi < 0.4) rate = state.currentScan.default_rates[0];
      else if (zone.avg_ndvi < 0.6) rate = state.currentScan.default_rates[1];
      else rate = state.currentScan.default_rates[2];
    } else {
      if (zone.avg_ndvi < 0.4) rate = 150;
      else if (zone.avg_ndvi < 0.6) rate = 250;
      else rate = 350;
    }

    tbody.append(`
      <tr>
        <td>
          <span class="zone-color-dot" style="background-color: ${zone.color}"></span>
          ${zone.name}
        </td>
        <td>${zone.avg_ndvi?.toFixed(2) || "N/A"}</td>
        <td><strong>${rate} кг/га</strong></td>
      </tr>
    `);
  });
}

function loadCropsIfNeeded() {
  if (availableCrops.length > 0) return Promise.resolve(availableCrops);
  return API.getCrops().then(data => {
    availableCrops = data.crops || [];
    return availableCrops;
  });
}
