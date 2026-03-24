/**
 * Отображение деталей поля.
 */
import { downloadKmzWithSettings } from './modals.js';
import { showMessage } from './utils.js';
import API from './api.js';

/**
 * Показывает детальную информацию о поле.
 * @param {string|number} id - ID поля.
 */
export function showFieldDetail(id) {
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
    
  }).fail(() => {
    showMessage("Данные не найдены", "error");
    window.location.hash = "#fields";
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
