/**
 * Отображение деталей поля.
 */
import { downloadKmzWithSettings } from './modals.js';
import { showMessage } from './utils.js';
import API from './api.js';

// Текущий выбранный скан
let currentScanId = null;
let currentFieldId = null;

/**
 * Показывает детальную информацию о поле.
 * @param {string|number} id - ID поля.
 */
export function showFieldDetail(id) {
  currentFieldId = id;
  
  API.getField(id).then(field => {
    $("#field-detail-name").text(field.name);
    $("#field-detail-area").text(field.area);
    $("#field-detail-owner").text(field.owner);
    $("#field-detail-status").text(field.land_status);
    $("#field-detail-parcel").text(field.parcel_number);

    // Экспорт ISOXML
    $("#detail-export-isoxml").off("click").on("click", (e) => {
      e.preventDefault();
      if (!field.zones || field.zones.length === 0) {
        showMessage("Нет зон для экспорта. Сначала загрузите TIFF файл.", "warning");
        return;
      }
      window.open(`/api/field/export/isoxml/${id}`, '_blank');
      showMessage("ISOXML файл загружен", "success");
    });

    // Экспорт KMZ
    $("#detail-export-kmz").off("click").on("click", () => downloadKmzWithSettings(id));

    // Удаление поля
    $("#detail-delete-field").off("click").on("click", () => {
      Swal.fire({
        title: "Удалить поле?",
        icon: "warning",
        showCancelButton: true
      }).then(r => {
        if (r.isConfirmed) {
          API.deleteField(id).then(() => {
            window.location.hash = "#fields";
          });
        }
      });
    });

    // Инициализация карты
    window.MapManager.initDetailMap("field-detail-map", field.geometry, field.zones);

    // Отображение статистики зон
    renderZonesStats(field.zones);

    // Загрузка списка сканов
    loadFieldScans(id);

    // Обработчик полноэкранного режима
    initFullscreenMode();

  }).fail(() => {
    showMessage("Данные не найдены", "error");
    window.location.hash = "#fields";
  });
}

/**
 * Инициализирует полноэкранный режим карты.
 */
function initFullscreenMode() {
  const $btn = $("#map-fullscreen-btn");
  const $mapCard = $(".map-card");
  const $icon = $btn.find("i");
  
  $btn.off("click").on("click", () => {
    const isFullscreen = $mapCard.hasClass("fullscreen");
    
    if (isFullscreen) {
      // Выход из полноэкранного режима
      $mapCard.removeClass("fullscreen");
      $icon.removeClass("fa-compress").addClass("fa-expand");
      $btn.attr("title", "На весь экран");
      
      // Включаем подложку
      window.MapManager.toggleBaseLayer(false);
    } else {
      // Вход в полноэкранный режим
      $mapCard.addClass("fullscreen");
      $icon.removeClass("fa-expand").addClass("fa-compress");
      $btn.attr("title", "Выйти из полноэкранного");
      
      // Выключаем подложку - показываем только поле
      window.MapManager.toggleBaseLayer(true);
    }
    
    // Перерисовываем карту для корректного отображения
    setTimeout(() => {
      if (window.MapManager.detailInstance) {
        window.MapManager.detailInstance.invalidateSize();
      }
    }, 100);
  });
  
  // Выход по ESC
  $(document).off("keydown.fullscreen").on("keydown.fullscreen", (e) => {
    if (e.key === "Escape" && $mapCard.hasClass("fullscreen")) {
      $mapCard.removeClass("fullscreen");
      $icon.removeClass("fa-compress").addClass("fa-expand");
      $btn.attr("title", "На весь экран");
      window.MapManager.toggleBaseLayer(false);
      setTimeout(() => {
        if (window.MapManager.detailInstance) {
          window.MapManager.detailInstance.invalidateSize();
        }
      }, 100);
    }
  });
}

/**
 * Загружает список сканов поля.
 * @param {number} fieldId - ID поля.
 */
function loadFieldScans(fieldId) {
  API.getFieldScans(fieldId).then(data => {
    const scans = data.scans || [];

    if (scans.length === 0) {
      $("#scans-selector").hide();
      return;
    }

    $("#scans-selector").show();
    const $list = $("#scan-list");
    $list.empty();

    scans.forEach((scan, index) => {
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

      // Выбираем первый (последний по дате) скан
      if (index === 0) {
        currentScanId = scan.id;
      }
    });

    // Загружаем зоны последнего скана
    if (currentScanId) {
      loadScanZones(currentScanId);
    }

  }).fail(err => {
    console.error("Ошибка загрузки сканов:", err);
  });
}

/**
 * Выбирает скан для отображения.
 * @param {number} scanId - ID скана.
 */
function selectScan(scanId) {
  currentScanId = scanId;
  
  // Обновляем активный элемент в списке
  $(".scan-item").removeClass("active");
  $(`.scan-item[data-scan-id="${scanId}"]`).addClass("active");
  
  loadScanZones(scanId);
}

/**
 * Удаляет скан.
 * @param {number} fieldId - ID поля.
 * @param {number} scanId - ID скана.
 */
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
        // Перезагружаем список сканов
        loadFieldScans(fieldId);
        // Если удалили текущий скан, очищаем карту
        if (currentScanId === scanId) {
          window.MapManager.updateZones([]);
          renderZonesStats([]);
          currentScanId = null;
        }
      }).fail(err => {
        console.error("Ошибка удаления скана:", err);
        showMessage("Не удалось удалить скан", "error");
      });
    }
  });
}

/**
 * Загружает зоны выбранного скана.
 * @param {number} scanId - ID скана.
 */
function loadScanZones(scanId) {
  API.getScanZones(scanId).then(data => {
    const zones = data.zones || [];

    console.log(`[DEBUG] Загружено зон для скана ${scanId}:`, zones.length);
    if (zones.length > 0) {
      console.log(`[DEBUG] Первая зона:`, zones[0]);
    }

    // Перерисовываем зоны на карте
    window.MapManager.updateZones(zones);

    // Обновляем статистику
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

  // Таблица зон
  const tbody = $("#zones-table-body");
  tbody.empty();

  zones.forEach(zone => {
    // Определяем норму внесения на основе NDVI
    let rate;
    if (zone.avg_ndvi < 0.4) {
      rate = 150; // Низкая зона
    } else if (zone.avg_ndvi < 0.6) {
      rate = 250; // Средняя зона
    } else {
      rate = 350; // Высокая зона
    }

    const row = `
      <tr>
        <td>
          <span class="zone-color-dot" style="background-color: ${zone.color}"></span>
          ${zone.name}
        </td>
        <td>${zone.avg_ndvi?.toFixed(2) || 'N/A'}</td>
        <td><strong>${rate} кг/га</strong></td>
      </tr>
    `;
    tbody.append(row);
  });

  // Легенда для карты
  const legend = $("#zones-legend");
  legend.empty();
  legend.append('<div class="legend-title">Зоны</div>');
  zones.forEach(zone => {
    legend.append(`
      <div class="legend-item">
        <span class="legend-color" style="background-color: ${zone.color}"></span>
        <span class="legend-label">${zone.name} (${zone.avg_ndvi?.toFixed(2) || 'N/A'})</span>
      </div>
    `);
  });
}

// Делаем функции глобальными для onclick handlers
window.selectScan = selectScan;
window.deleteScan = deleteScan;
window.loadFieldScans = loadFieldScans;
