/**
 * Отображение деталей поля.
 */
import { downloadKmzWithSettings } from './modals.js';
import { showMessage } from './utils.js';
import API from './api.js';

// Текущий выбранный скан
let currentScanId = null;
let currentFieldId = null;
let currentScan = null;
let allScans = [];
let processingPollInterval = null;
let availableCrops = [];

// Инициализация списка культур
API.getCrops().then(data => {
  availableCrops = data.crops || [];
});

const CROP_NAMES = {
    'wheat': 'Пшеница',
    'corn': 'Кукуруза',
    'sunflower': 'Подсолнечник',
    'soybean': 'Соя',
    'rapeseed': 'Рапс',
    'barley': 'Ячмень',
    'oats': 'Овес',
    'sugar_beet': 'Сахарная свекла',
    'potato': 'Картофель',
    'vegetables': 'Овощи',
    'grass': 'Трава/Сено',
    'unknown': 'Не определено'
};

/**
 * Показывает детальную информацию о поле.
 * @param {string|number} id - ID поля.
 */
export function showFieldDetail(id) {
  currentFieldId = id;

  // Очищаем polling если был запущен
  if (processingPollInterval) {
    clearInterval(processingPollInterval);
    processingPollInterval = null;
  }
  
  API.getField(id).then(field => {
    $("#field-detail-name").text(field.name);
    $("#field-detail-area").text(field.area);
    $("#field-detail-owner").text(field.owner);
    $("#field-detail-status").text(field.land_status);
    $("#field-detail-parcel").text(field.parcel_number);

    loadFieldScans(id);
  });
}

/**
 * @param {number} fieldId - ID поля.
 */
function loadFieldScans(fieldId) {
  API.getFieldScans(fieldId).then(data => {
    allScans = data.scans || [];

    if (allScans.length === 0) {
      $("#scans-selector").hide();
      $("#ndvi-processing-msg").hide();
      return;
    }

    $("#scans-selector").show();
    const $list = $("#scan-list");
    $list.empty();

    currentScanId = null;
    currentScan = null;

    const hasProcessingScans = allScans.some(scan => !scan.processed);

    allScans.forEach((scan, index) => {
      const date = new Date(scan.uploaded_at).toLocaleDateString('ru-RU', {
        day: 'numeric',
        month: 'long',
        year: 'numeric'
      });
      const status = scan.processed ? '✓' : '⏳';
      const zones = scan.has_zones ? `${scan.zones_count || 3} зоны` : 'Нет зон';
      const ndvi = scan.ndvi_avg ? `NDVI: ${scan.ndvi_avg.toFixed(2)}` : '';

      const $item = $(`
        <div class="scan-item ${index === 0 ? 'active' : ''}" data-scan-id="${scan.id}">
          <div class="scan-info" onclick="selectScan(${scan.id})">
            <span class="scan-status">${status}</span>
            <span class="scan-date">${date}</span>
            <span class="scan-zones">${zones}</span>
            <span class="scan-ndvi">${ndvi}</span>
          </div>
          <button class="btn-delete-scan" onclick="deleteScan(${fieldId}, ${scan.id})" title="Удалить снимок">
            <i class="fas fa-trash"></i>
          </button>
        </div>
      `);

      $list.append($item);

      if (!currentScanId && scan.processed && scan.has_zones) {
        currentScanId = scan.id;
        currentScan = scan;
        $item.addClass('active').siblings().removeClass('active');
      }
    });

    if (!currentScanId && allScans.length > 0) {
      currentScanId = allScans[0].id;
      currentScan = allScans[0];
    }

    if (hasProcessingScans && !currentScanId) {
      $("#ndvi-processing-msg").show();
      startProcessingPoll(fieldId);
    } else {
      $("#ndvi-processing-msg").hide();
    }

    if (currentScanId) {
      loadScanZones(currentScanId);
    }
  }).fail(err => {
    console.error("Ошибка загрузки сканов:", err);
  });
}

/**
 * Запускает polling для проверки готовности NDVI
 * @param {number} fieldId - ID поля.
 */
function startProcessingPoll(fieldId) {
  if (processingPollInterval) {
    clearInterval(processingPollInterval);
  }

  processingPollInterval = setInterval(() => {
    API.getFieldScans(fieldId).then(data => {
      const scans = data.scans || [];
      const hasProcessingScans = scans.some(scan => !scan.processed);
      const hasProcessedWithZones = scans.some(scan => scan.processed && scan.has_zones);

      if (hasProcessedWithZones) {
        clearInterval(processingPollInterval);
        processingPollInterval = null;
        loadFieldScans(fieldId);
        showMessage("NDVI обработан! Данные обновлены", "success");
      }

      if (!hasProcessingScans) {
        clearInterval(processingPollInterval);
        processingPollInterval = null;
        $("#ndvi-processing-msg").hide();
      }
    }).fail(err => {
      console.error("Ошибка polling:", err);
    });
  }, 10000);
}

function selectScan(scanId) {
  currentScanId = scanId;
  currentScan = allScans.find(s => s.id === scanId);
  $(".scan-item").removeClass("active");
  $(`.scan-item[data-scan-id="${scanId}"]`).addClass("active");
  loadScanZones(scanId);
}

function deleteScan(fieldId, scanId) {
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
        loadFieldScans(fieldId);
        if (currentScanId === scanId) {
          window.MapManager.updateZones([]);
          renderZonesStats([]);
          currentScanId = null;
          currentScan = null;
        }
      }).fail(err => {
        console.error("Ошибка удаления скана:", err);
        showMessage("Не удалось удалить скан", "error");
      });
    }
  });
}

function loadScanZones(scanId) {
  API.getScanZones(scanId).then(data => {
    const zones = data.zones || [];
    window.MapManager.updateZones(zones);
    renderZonesStats(zones);
  }).fail(err => {
    console.error("Ошибка загрузки зон:", err);
    showMessage("Не удалось загрузить зоны для этого скана", "error");
  });
}

/**
 * Отображает статистику по зонам внесения.
 * @param {Array} zones - Массив зон поля.
 */
function renderZonesStats(zones) {
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
    availableCrops.forEach(crop => {
      $select.append(`<option value="${crop.id}">${crop.name}</option>`);
    });
  }

  if (currentScan) {
    $select.val(currentScan.crop_type || 'unknown');
    
    if (currentScan.crop_type && currentScan.crop_confidence < 1.0) {
      $badge.show();
      $confidence.text(`${Math.round(currentScan.crop_confidence * 100)}%`).show();
    } else {
      $badge.hide();
      $confidence.hide();
    }
    
    $prediction.show();

    $select.off('change').on('change', function() {
      const newCrop = $(this).val();
      API.updateScanCrop(currentScanId, newCrop).then(res => {
        showMessage("Культура обновлена", 'success');
        currentScan.crop_type = newCrop;
        currentScan.crop_confidence = 1.0;
        currentScan.default_rates = res.default_rates;
        renderZonesStats(zones);
      });
    });
  } else {
    $prediction.hide();
  }

  const tbody = $("#zones-table-body");
  tbody.empty();

  zones.forEach((zone) => {
    let rate = 0;
    if (currentScan && currentScan.default_rates && currentScan.default_rates.length >= 3) {
      if (zone.avg_ndvi < 0.4) rate = currentScan.default_rates[0];
      else if (zone.avg_ndvi < 0.6) rate = currentScan.default_rates[1];
      else rate = currentScan.default_rates[2];
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
        <td>${zone.avg_ndvi?.toFixed(2) || 'N/A'}</td>
        <td><strong>${rate} кг/га</strong></td>
      </tr>
    `);
  });
}

window.selectScan = selectScan;
window.deleteScan = deleteScan;
window.loadFieldScans = loadFieldScans;
