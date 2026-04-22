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
let ndviHistoryChart = null;

// Инициализация списка культур
API.getCrops().then(data => {
  availableCrops = data.crops || [];
});

/**
 * Инициализирует и обновляет график истории NDVI.
 * @param {Array} scans - Список всех сканов поля.
 */
function initNDVIChart(scans) {
    const ctx = document.getElementById('ndvi-history-chart');
    if (!ctx) return;

    // Фильтруем только обработанные сканы и сортируем по дате
    const chartData = scans
        .filter(s => s.processed && s.ndvi_avg)
        .sort((a, b) => new Date(a.uploaded_at) - new Date(b.uploaded_at));

    if (chartData.length === 0) {
        if (ndviHistoryChart) ndviHistoryChart.destroy();
        return;
    }

    const labels = chartData.map(s => new Date(s.uploaded_at).toLocaleDateString('ru-RU'));
    const values = chartData.map(s => s.ndvi_avg);

    if (ndviHistoryChart) {
        ndviHistoryChart.data.labels = labels;
        ndviHistoryChart.data.datasets[0].data = values;
        ndviHistoryChart.update();
    } else {
        ndviHistoryChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Средний NDVI',
                    data: values,
                    borderColor: '#4CAF50',
                    backgroundColor: 'rgba(76, 175, 80, 0.1)',
                    borderWidth: 2,
                    fill: true,
                    tension: 0.3
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        min: 0,
                        max: 1,
                        title: { display: true, text: 'NDVI' }
                    }
                },
                plugins: {
                    legend: { display: false }
                }
            }
        });
    }
}

/**
 * Выполняет сравнение двух выбранных сканов.
 */
function compareSelectedScans() {
    const selected = $(".scan-checkbox:checked");
    if (selected.length !== 2) {
        showMessage("Выберите ровно 2 снимка для сравнения", "warning");
        return;
    }

    const scanIds = selected.map((_, el) => $(el).val()).get();
    // Сортируем по ID (или дате), чтобы старый был первым
    const sortedScans = allScans
        .filter(s => scanIds.includes(s.id.toString()))
        .sort((a, b) => new Date(a.uploaded_at) - new Date(b.uploaded_at));

    const scan1Id = sortedScans[0].id;
    const scan2Id = sortedScans[1].id;

    API.compareScans(currentFieldId, scan1Id, scan2Id).then(result => {
        $("#comparison-result").show();
        const delta = result.delta_avg;
        const deltaText = (delta > 0 ? "+" : "") + (delta * 100).toFixed(1) + "%";
        
        const $val = $("#compare-delta-value");
        $val.text(deltaText);
        $val.css("color", delta > 0 ? "#4CAF50" : "#f44336");

        const trendIcon = delta > 0.05 ? "📈 Улучшение" : (delta < -0.05 ? "📉 Ухудшение" : "➡️ Стабильно");
        $("#compare-trend-icon").text(trendIcon);

        showMessage(`Сравнение завершено. Изменение NDVI: ${deltaText}`, "info");
    }).fail(err => {
        console.error("Ошибка сравнения:", err);
        showMessage("Не удалось выполнить сравнение", "error");
    });
}

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

    // Инициализируем карту деталей поля
    if (window.MapManager) {
      window.MapManager.initDetailMap("field-detail-map", field.geometry);
    }

    loadFieldScans(id);
  });
}

/**
 * Загружает список сканов поля.
 * @param {number} fieldId - ID поля.
 */
function loadFieldScans(fieldId) {
  API.getFieldScans(fieldId).then(data => {
    allScans = data.scans || [];

    if (allScans.length === 0) {
      $("#scans-selector").hide();
      $("#ndvi-processing-msg").hide();
      $("#comparison-result").hide();
      return;
    }

    $("#scans-selector").show();
    const $list = $("#scan-list");
    $list.empty();
    
    // Добавляем кнопку сравнения если её нет
    if ($("#btn-compare-scans").length === 0) {
        $("#scans-selector label").after(`
            <button id="btn-compare-scans" class="btn btn-sm btn-outline-primary" style="float: right; margin-top: -5px;" onclick="compareSelectedScans()">
                <i class="fas fa-columns"></i> Сравнить
            </button>
        `);
    }

    // Сбрасываем currentScanId
    currentScanId = null;
    currentScan = null;
    $("#comparison-result").hide();

    // Проверяем есть ли необработанные сканы
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
          <div class="scan-checkbox-wrapper">
             <input type="checkbox" class="scan-checkbox" value="${scan.id}" onclick="event.stopPropagation()">
          </div>
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

      // Выбираем первый обработанный скан с зонами
      if (!currentScanId && scan.processed && scan.has_zones) {
        currentScanId = scan.id;
        currentScan = scan;
        // Отмечаем его как активный
        $item.addClass('active').siblings().removeClass('active');
      }
    });

    // Инициализируем график
    initNDVIChart(allScans);

    // Если не нашли обработанный скан с зонами, берем первый доступный
    if (!currentScanId && allScans.length > 0) {
      currentScanId = allScans[0].id;
      currentScan = allScans[0];
    }

    // Показываем сообщение о обработке если есть необработанные сканы
    if (hasProcessingScans && !currentScanId) {
      $("#ndvi-processing-msg").show();
      // Запускаем polling для проверки готовности
      startProcessingPoll(fieldId);
    } else {
      $("#ndvi-processing-msg").hide();
    }

    // Загружаем зоны выбранного скана
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
  // Очищаем предыдущий polling если есть
  if (processingPollInterval) {
    clearInterval(processingPollInterval);
  }

  // Проверяем каждые 10 секунд
  processingPollInterval = setInterval(() => {
    API.getFieldScans(fieldId).then(data => {
      const scans = data.scans || [];
      const hasProcessingScans = scans.some(scan => !scan.processed);
      const hasProcessedWithZones = scans.some(scan => scan.processed && scan.has_zones);

      // Если появился обработанный скан с зонами, перезагружаем
      if (hasProcessedWithZones) {
        clearInterval(processingPollInterval);
        processingPollInterval = null;
        loadFieldScans(fieldId);
        showMessage("NDVI обработан! Данные обновлены", "success");
      }

      // Если все сканы обработаны но нет зон, останавливаем
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

/**
 * Выбирает скан для отображения.
 * @param {number} scanId - ID скана.
 */
function selectScan(scanId) {
  currentScanId = scanId;
  currentScan = allScans.find(s => s.id === scanId);

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
          currentScan = null;
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
    // Перерисовываем зоны на карте
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

  // Показываем предсказание культуры
  const $prediction = $("#crop-prediction");
  const $select = $("#crop-type-select");
  const $badge = $("#prediction-badge");
  const $confidence = $("#prediction-confidence");

  // Заполняем выпадающий список если он пуст
  if ($select.children().length === 0) {
    availableCrops.forEach(crop => {
      $select.append(`<option value="${crop.id}">${crop.name}</option>`);
    });
  }

  if (currentScan) {
    $select.val(currentScan.crop_type || 'unknown');
    
    // Если уверенность < 1.0, значит это предсказание системы
    if (currentScan.crop_type && currentScan.crop_confidence < 1.0) {
      $badge.show();
      $confidence.text(`${Math.round(currentScan.crop_confidence * 100)}%`).show();
    } else {
      $badge.hide();
      $confidence.hide();
    }
    
    $prediction.show();

    // Обработчик изменения культуры
    $select.off('change').on('change', function() {
      const newCrop = $(this).val();
      API.updateScanCrop(currentScanId, newCrop).then(res => {
        showMessage("Культура обновлена", 'success');
        // Обновляем текущий скан локально
        currentScan.crop_type = newCrop;
        currentScan.crop_confidence = 1.0;
        currentScan.default_rates = res.default_rates;
        
        // Перерисовываем статистику с новыми нормами
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
