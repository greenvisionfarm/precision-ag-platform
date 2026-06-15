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


/**
 * Инициализирует и обновляет график истории NDVI.
 * @param {Array} scans - Список всех сканов поля.
 */
function initNDVIChart(scans) {
    const ctx = document.getElementById('ndvi-history-chart');
    if (!ctx) return;

    // Всегда уничтожаем старый график перед созданием нового
    if (ndviHistoryChart) {
        ndviHistoryChart.destroy();
        ndviHistoryChart = null;
    }

    // Фильтруем только обработанные сканы и сортируем по дате
    const chartData = scans
        .filter(s => s.processed && s.ndvi_avg)
        .sort((a, b) => new Date(a.uploaded_at) - new Date(b.uploaded_at));

    if (chartData.length === 0) {
        return;
    }

    const labels = chartData.map(s => new Date(s.uploaded_at).toLocaleDateString('ru-RU'));
    const values = chartData.map(s => s.ndvi_avg);

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
    loadJournal(id);
    $("#journal-add-btn").show();
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

  // Загружаем список культур лениво
  function loadCropsIfNeeded() {
    if (availableCrops.length > 0) {
      return Promise.resolve(availableCrops);
    }
    return API.getCrops().then(data => {
      availableCrops = data.crops || [];
      return availableCrops;
    });
  }

  // Заполняем выпадающий список если он пуст
  if ($select.children().length === 0) {
    loadCropsIfNeeded().then(crops => {
      $select.empty();
      crops.forEach(crop => {
        $select.append(`<option value="${crop.id}">${crop.name}</option>`);
      });
      if (currentScan) {
        $select.val(currentScan.crop_type || 'unknown');
      }
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
window.compareSelectedScans = compareSelectedScans;

/**
 * Скачивает blob-файл с именем filename.
 */
function downloadBlob(blob, filename) {
  if (!(blob instanceof Blob)) {
    blob = new Blob([blob], { type: 'application/octet-stream' });
  }
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  setTimeout(() => {
    URL.revokeObjectURL(url);
    a.remove();
  }, 100);
}

/**
 * Обработчик экспорта ISOXML.
 */
$(document).on('click', '#detail-export-isoxml', function(e) {
  e.preventDefault();
  if (!currentFieldId) return;

  Swal.fire({
    title: "Настройки экспорта ISOXML",
    html: `
      <div style="text-align: left; display: flex; flex-direction: column; gap: 16px;">
        <div>
          <label for="swal-product-name" style="display: block; font-weight: 600; margin-bottom: 4px;">Название продукта:</label>
          <input type="text" id="swal-product-name" class="swal2-input" style="margin: 0; width: 100%;" value="Аммиачная селитра" placeholder="Напр. Аммиачная селитра">
        </div>
        <div>
          <label for="swal-product-type" style="display: block; font-weight: 600; margin-bottom: 4px;">Тип продукта:</label>
          <select id="swal-product-type" class="swal2-select" style="margin: 0; width: 100%;">
            <option value="nitrogen" selected>Azote (nitrogen)</option>
            <option value="npk">NPK</option>
            <option value="phosphorus">Phosphore (phosphorus)</option>
            <option value="potassium">Potassium</option>
            <option value="organic">Organique (organic)</option>
          </select>
          <small style="color: #888; font-size: 0.8em;">Тип удобрения для ISOXML TaskData.</small>
        </div>
      </div>`,
    width: "500px",
    focusConfirm: false,
    preConfirm: () => {
      const name = document.getElementById("swal-product-name").value.trim();
      const type = document.getElementById("swal-product-type").value;
      if (!name) {
        Swal.showValidationMessage("Введите название продукта");
        return false;
      }
      return { product_name: name, product_type: type };
    }
  }).then(res => {
    if (!res.isConfirmed) return;
    const { product_name, product_type } = res.value;

    showMessage('Генерация ISOXML...', 'info');

    API.exportIsoxml(currentFieldId, { product_name, product_type }).then(blob => {
      const filename = `field_${currentFieldId}_isoxml.xml`;
      downloadBlob(blob, filename);
      showMessage(`ISOXML экспортирован: ${filename}`, 'success');
    });
  });
});

/**
 * Обработчик экспорта TaskData.zip (ISOXML v3.3).
 */
$(document).on('click', '#detail-export-taskdata', function(e) {
  e.preventDefault();
  if (!currentFieldId) return;

  const today = new Date().toISOString().split('T')[0];

  Swal.fire({
    title: "Экспорт TaskData",
    html: `
      <div style="text-align: left; display: flex; flex-direction: column; gap: 12px; font-size: 0.9em; max-height: 70vh; overflow-y: auto;">

        <fieldset style="border: 1px solid var(--border-color); border-radius: 6px; padding: 10px;">
          <legend style="font-weight: 600; padding: 0 6px;">Продукт</legend>
          <div style="display: flex; gap: 10px;">
            <div style="flex: 1;">
              <label style="display: block; margin-bottom: 3px;">Группа:</label>
              <select id="swal-td-group" class="swal2-select" style="margin: 0; width: 100%;">
                <option value="mineral" selected>Минеральные</option>
                <option value="organic">Органические</option>
                <option value="mixed">Смешанные</option>
              </select>
            </div>
            <div style="flex: 2;">
              <label style="display: block; margin-bottom: 3px;">Продукт:</label>
              <input type="text" id="swal-td-product" class="swal2-input" style="margin: 0; width: 100%; height: 34px;" value="Аммиачная селитра" placeholder="Напр. Amofos, KCl">
            </div>
          </div>
        </fieldset>

        <fieldset style="border: 1px solid var(--border-color); border-radius: 6px; padding: 10px;">
          <legend style="font-weight: 600; padding: 0 6px;">Общая информация</legend>
          <div style="display: flex; gap: 10px; flex-wrap: wrap;">
            <div style="flex: 1; min-width: 120px;">
              <label style="display: block; margin-bottom: 3px;">Целевой элемент:</label>
              <select id="swal-td-nutrient" class="swal2-select" style="margin: 0; width: 100%;">
                <option value="nitrogen" selected>Азот [кг N/га]</option>
                <option value="phosphorus">Фосфор [кг P/га]</option>
                <option value="potassium">Калий [кг K/га]</option>
              </select>
            </div>
            <div style="flex: 1; min-width: 120px;">
              <label style="display: block; margin-bottom: 3px;">Дата внесения:</label>
              <input type="date" id="swal-td-date" class="swal2-input" style="margin: 0; width: 100%; height: 34px;" value="${today}">
            </div>
          </div>
          <div style="margin-top: 8px;">
            <label style="display: block; margin-bottom: 3px;">Ферма:</label>
            <input type="text" id="swal-td-farm" class="swal2-input" style="margin: 0; width: 100%; height: 34px;" placeholder="Название хозяйства">
          </div>
        </fieldset>

        <fieldset style="border: 1px solid var(--border-color); border-radius: 6px; padding: 10px;">
          <legend style="font-weight: 600; padding: 0 6px;">Агрономия</legend>
          <div style="display: flex; gap: 10px; flex-wrap: wrap;">
            <div style="flex: 1; min-width: 120px;">
              <label style="display: block; margin-bottom: 3px;">Режим:</label>
              <select id="swal-td-rate-mode" class="swal2-select" style="margin: 0; width: 100%;">
                <option value="variable" selected>Переменный (VRA)</option>
                <option value="constant">Константа</option>
              </select>
              <small style="color: #888;">VRA — разная норма по зонам NDVI</small>
            </div>
            <div style="flex: 1; min-width: 120px;">
              <label style="display: block; margin-bottom: 3px;">Остаточный спрос [%]:</label>
              <select id="swal-td-residual" class="swal2-select" style="margin: 0; width: 100%;">
                <option value="0">0% — полное внесение</option>
                <option value="1" selected>100% — норма из расчёта</option>
                <option value="2">200% — двухкратная норма</option>
              </select>
              <small style="color: #888;">Коэффициент к расчётной норме</small>
            </div>
          </div>
          <div id="swal-td-rates" style="margin-top: 8px;">
            <label style="display: block; margin-bottom: 3px; font-weight: 500;">Норма [кг/га]:</label>
            <div style="display: flex; gap: 10px;">
              <div style="flex: 1;">
                <label style="font-size: 0.85em; color: #888;">Минимум:</label>
                <input type="number" id="swal-td-rate-min" class="swal2-input" style="margin: 0; width: 100%; height: 34px;" value="100" min="0">
              </div>
              <div style="flex: 1;">
                <label style="font-size: 0.85em; color: #888;">Максимум:</label>
                <input type="number" id="swal-td-rate-max" class="swal2-input" style="margin: 0; width: 100%; height: 34px;" value="400" min="0">
              </div>
              <div style="flex: 1;" id="swal-td-const-wrap" style="display: none;">
                <label style="font-size: 0.85em; color: #888;">Постоянная:</label>
                <input type="number" id="swal-td-rate-const" class="swal2-input" style="margin: 0; width: 100%; height: 34px;" value="250" min="0">
              </div>
            </div>
            <small style="color: #888;">Для VRA: мин/макс ограничивают диапазон норм. NDVI зоны масштабируются в эти рамки.</small>
          </div>
        </fieldset>

        <fieldset style="border: 1px solid var(--border-color); border-radius: 6px; padding: 10px;">
          <legend style="font-weight: 600; padding: 0 6px;">Грид</legend>
          <div>
            <label style="display: block; margin-bottom: 3px;">Разрешение:</label>
            <select id="swal-td-resolution" class="swal2-select" style="margin: 0; width: 100%;">
              <option value="1">1 м — высокая точность, большой файл</option>
              <option value="2" selected>2 м — стандарт (рекомендуется)</option>
              <option value="5">5 м — быстрая генерация</option>
              <option value="10">10 м — грубое, минимальный файл</option>
            </select>
            <small style="color: #888;">Размер ячейки грида. Техника меняет норму каждые N метров по GPS.</small>
          </div>
        </fieldset>

        <div style="background: #f0f0f0; padding: 8px 10px; border-radius: 6px; font-size: 0.85em;">
          <strong>Формат:</strong> TaskData.zip (ISO 11783 v3.3)<br>
          <strong>Совместимость:</strong> Agricon, John Deere TaskData, Claas
        </div>
      </div>`,
    width: "560px",
    focusConfirm: false,
    didOpen: () => {
      const modeSelect = document.getElementById('swal-td-rate-mode');
      const constWrap = document.getElementById('swal-td-const-wrap');
      const rateMin = document.getElementById('swal-td-rate-min');
      const rateMax = document.getElementById('swal-td-rate-max');
      const rateConst = document.getElementById('swal-td-rate-const');

      function updateRateMode() {
        const isConst = modeSelect.value === 'constant';
        constWrap.style.display = isConst ? 'block' : 'none';
        rateMin.disabled = isConst;
        rateMax.disabled = isConst;
        rateMin.style.opacity = isConst ? '0.5' : '1';
        rateMax.style.opacity = isConst ? '0.5' : '1';
      }
      modeSelect.addEventListener('change', updateRateMode);
      updateRateMode();
    },
    preConfirm: () => {
      const product = document.getElementById("swal-td-product").value.trim();
      const farm = document.getElementById("swal-td-farm").value.trim();
      const resolution = document.getElementById("swal-td-resolution").value;
      const rateMode = document.getElementById("swal-td-rate-mode").value;
      const nutrient = document.getElementById("swal-td-nutrient").value;
      const date = document.getElementById("swal-td-date").value;
      const residual = document.getElementById("swal-td-residual").value;
      const rateMin = parseFloat(document.getElementById("swal-td-rate-min").value) || 100;
      const rateMax = parseFloat(document.getElementById("swal-td-rate-max").value) || 400;
      const rateConst = parseFloat(document.getElementById("swal-td-rate-const").value) || 250;
      const group = document.getElementById("swal-td-group").value;

      if (!product) {
        Swal.showValidationMessage("Введите название продукта");
        return false;
      }
      return {
        product_name: product,
        product_group: group,
        nutrient: nutrient,
        application_date: date,
        farm_name: farm || null,
        resolution: parseFloat(resolution),
        rate_mode: rateMode,
        rate_min: rateMin,
        rate_max: rateMax,
        constant_rate: rateMode === 'constant' ? rateConst : null,
        residual_pct: parseFloat(residual) || 1
      };
    }
  }).then(res => {
    if (!res.isConfirmed) return;

    showMessage('Генерация TaskData.zip...', 'info');

    API.exportTaskData(currentFieldId, res.value).then(blob => {
      const filename = `field_${currentFieldId}_taskdata.zip`;
      downloadBlob(blob, filename);
      showMessage(`TaskData экспортирован: ${filename}`, 'success');
    });
  });
});

// ===== Field Journal =====

const CROP_LABELS = {
  wheat: 'Пшеница', corn: 'Кукуруза', sunflower: 'Подсолнечник',
  soybean: 'Соя', barley: 'Ячмень', rapeseed: 'Рапс',
  sugar_beet: 'Сахарная свекла', potato: 'Картофель', other: 'Другое'
};

function loadJournal(fieldId) {
  $.getJSON(`/api/field/${fieldId}/journal`).then(data => {
    const entries = data.entries || [];
    if (entries.length === 0) {
      $("#journal-entries").hide();
      $("#journal-empty").show();
      return;
    }
    $("#journal-empty").hide();
    $("#journal-entries").show();
    const $tbody = $("#journal-table-body").empty();
    entries.forEach(e => {
      const crop = CROP_LABELS[e.crop_type] || e.crop_type || '-';
      const plant = e.planting_date ? new Date(e.planting_date).toLocaleDateString('ru-RU') : '-';
      const product = e.product_name || '-';
      const rate = e.application_rate ? `${e.application_rate} кг/га` : '-';
      const yld = e.yield_amount ? `${e.yield_amount} ц/га` : '-';
      $tbody.append(`
        <tr>
          <td>${crop}${e.crop_variety ? ' (' + e.crop_variety + ')' : ''}</td>
          <td>${plant}</td>
          <td>${product}</td>
          <td>${rate}</td>
          <td>${yld}</td>
          <td><button class="btn btn-sm btn-danger" onclick="deleteJournalEntry(${fieldId}, ${e.id})" title="Удалить"><i class="fas fa-trash"></i></button></td>
        </tr>
      `);
    });
  });
}

function deleteJournalEntry(fieldId, entryId) {
  if (!confirm('Удалить запись журнала?')) return;
  $.ajax({ url: `/api/field/${fieldId}/journal/${entryId}`, type: 'DELETE' })
    .then(() => { loadJournal(fieldId); showMessage('Запись удалена', 'success'); });
}

window.deleteJournalEntry = deleteJournalEntry;

$(document).on('click', '#journal-add-btn', function() {
  if (!currentFieldId) return;

  Swal.fire({
    title: "Новая запись журнала",
    html: `
      <div class="kmz-settings-grid" style="text-align:left;">
        <div class="kmz-field">
          <label>Культура:</label>
          <select id="j-crop-type" class="swal2-select">
            <option value="wheat">Пшеница</option>
            <option value="corn">Кукуруза</option>
            <option value="sunflower">Подсолнечник</option>
            <option value="soybean">Соя</option>
            <option value="barley">Ячмень</option>
            <option value="rapeseed">Рапс</option>
            <option value="sugar_beet">Сахарная свекла</option>
            <option value="potato">Картофель</option>
            <option value="other">Другое</option>
          </select>
        </div>
        <div class="kmz-field">
          <label>Сорт:</label>
          <input type="text" id="j-crop-variety" class="swal2-input" placeholder="Не обязательно">
        </div>
        <div class="kmz-field">
          <label>Дата посадки:</label>
          <input type="date" id="j-planting-date" class="swal2-input">
        </div>
        <div class="kmz-field">
          <label>Дата уборки:</label>
          <input type="date" id="j-harvest-date" class="swal2-input">
        </div>
        <div class="kmz-field">
          <label>Продукт (удобрение):</label>
          <input type="text" id="j-product-name" class="swal2-input" placeholder="Напр. Аммиачная селитра">
        </div>
        <div class="kmz-field">
          <label>Норма (кг/га):</label>
          <input type="number" id="j-application-rate" class="swal2-input" placeholder="200">
        </div>
        <div class="kmz-field">
          <label>Урожайность (ц/га):</label>
          <input type="number" id="j-yield" class="swal2-input" placeholder="Опционально">
        </div>
        <div class="kmz-field" style="grid-column: span 2;">
          <label>Заметки:</label>
          <textarea id="j-notes" class="swal2-textarea" rows="2" placeholder="Дополнительная информация"></textarea>
        </div>
      </div>`,
    width: "700px",
    focusConfirm: false,
    preConfirm: () => {
      const crop = document.getElementById("j-crop-type").value;
      if (!crop) { Swal.showValidationMessage("Выберите культуру"); return false; }
      return {
        crop_type: crop,
        crop_variety: document.getElementById("j-crop-variety").value || null,
        planting_date: document.getElementById("j-planting-date").value || null,
        harvest_date: document.getElementById("j-harvest-date").value || null,
        product_name: document.getElementById("j-product-name").value || null,
        application_rate: parseFloat(document.getElementById("j-application-rate").value) || null,
        yield_amount: parseFloat(document.getElementById("j-yield").value) || null,
        notes: document.getElementById("j-notes").value || null,
      };
    }
  }).then(res => {
    if (!res.isConfirmed) return;
    $.ajax({
      url: `/api/field/${currentFieldId}/journal/add`,
      type: 'POST',
      contentType: 'application/json',
      data: JSON.stringify(res.value)
    }).then(() => {
      loadJournal(currentFieldId);
      showMessage('Запись добавлена', 'success');
    });
  });
});

// ===== Tabs =====
$(document).on('click', '.tab-btn', function() {
  const tabId = $(this).data('tab');
  $('.tab-btn').removeClass('active');
  $(this).addClass('active');
  $('.tab-panel').removeClass('active');
  $(`#${tabId}`).addClass('active');
  if (window.MapManager?.detailInstance) {
    setTimeout(() => window.MapManager.detailInstance.invalidateSize(), 100);
  }
});

// ===== Map Controls =====
$(document).on('click', '#map-center-btn', function() {
  if (window.MapManager?.detailInstance && window.MapManager.currentFieldGeometry) {
    const bounds = L.geoJSON(window.MapManager.currentFieldGeometry).getBounds();
    window.MapManager.detailInstance.fitBounds(bounds, { padding: [30, 30], maxZoom: 16 });
  }
});

$(document).on('click', '#map-fullscreen-btn', function() {
  const section = $('.detail-map-section');
  const icon = $(this).find('i');
  section.toggleClass('fullscreen');
  if (section.hasClass('fullscreen')) {
    icon.removeClass('fa-expand').addClass('fa-compress');
    icon.parent().attr('title', 'Свернуть');
  } else {
    icon.removeClass('fa-compress').addClass('fa-expand');
    icon.parent().attr('title', 'На весь экран');
  }
  setTimeout(() => window.MapManager?.detailInstance?.invalidateSize(), 200);
});

$(document).on('keydown', function(e) {
  if (e.key === 'Escape' && $('.detail-map-section').hasClass('fullscreen')) {
    $('.detail-map-section').removeClass('fullscreen');
    $('#map-fullscreen-btn i').removeClass('fa-compress').addClass('fa-expand');
    setTimeout(() => window.MapManager?.detailInstance?.invalidateSize(), 200);
  }
});

// ===== KMZ Export =====
$(document).on('click', '#detail-export-kmz', function(e) {
  e.preventDefault();
  if (!currentFieldId || !downloadKmzWithSettings) return;
  downloadKmzWithSettings(currentFieldId);
});

// ===== Delete Field =====
$(document).on('click', '#detail-delete-field', function() {
  if (!currentFieldId) return;
  Swal.fire({
    title: 'Удалить поле?',
    text: 'Все сканы и зоны будут удалены. Это действие необратимо.',
    icon: 'warning',
    showCancelButton: true,
    confirmButtonColor: '#dc3545',
    confirmButtonText: 'Да, удалить',
    cancelButtonText: 'Отмена'
  }).then((result) => {
    if (!result.isConfirmed) return;
    API.deleteField(currentFieldId).then(() => {
      showMessage('Поле удалено', 'success');
      window.location.hash = '#fields';
    });
  });
});

// ===== NDVI Upload on Field Page =====
$(document).on('change', '#field-ndvi-input', function() {
  const hasFiles = this.files.length > 0;
  const label = $(this).siblings('.file-input-label');
  if (hasFiles) {
    const name = this.files.length > 1 ? `${this.files.length} файлов` : this.files[0].name;
    label.html(`<i class="fas fa-file-image"></i> ${name}`);
  } else {
    label.html('<i class="fas fa-file-upload"></i> Выберите GeoTIFF или ZIP архив');
  }
  $('#field-upload-button').toggle(hasFiles);
});

$(document).on('submit', '#field-upload-form', function(e) {
  e.preventDefault();
  const file = $('#field-ndvi-input')[0].files[0];
  if (!file) return;

  const statusDiv = $('#field-upload-status');
  const btn = $('#field-upload-button');
  statusDiv.html('<i class="fas fa-spinner fa-spin"></i> Загрузка...');
  btn.prop('disabled', true);

  const formData = new FormData();
  formData.append('raster_file', file);

  $.ajax({
    url: '/api/raster/upload',
    type: 'POST',
    data: formData,
    processData: false,
    contentType: false,
    success: (res) => {
      statusDiv.html('<i class="fas fa-check" style="color: var(--success-color);"></i> Загружен! Обработка зон...');
      loadFieldScans(currentFieldId);
      $('#field-ndvi-input').val();
      $('#field-upload-button').hide();
      setTimeout(() => {
        statusDiv.empty();
        btn.prop('disabled', false);
      }, 5000);
      showMessage('NDVI файл загружен. Зоны появятся через несколько секунд.', 'success');
    },
    error: (xhr) => {
      const err = xhr.responseJSON?.error || 'Ошибка загрузки';
      statusDiv.html(`<i class="fas fa-exclamation-triangle" style="color: var(--danger-color);"></i> ${err}`);
      btn.prop('disabled', false);
      showMessage(err, 'error');
    }
  });
});
