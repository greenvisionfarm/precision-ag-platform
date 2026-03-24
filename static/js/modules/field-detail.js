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

    $("#detail-export-kmz").off("click").on("click", () => downloadKmzWithSettings(id));
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

    window.MapManager.initDetailMap("field-detail-map", field.geometry, field.zones);
  }).fail(() => {
    showMessage("Данные не найдены", "error");
    window.location.hash = "#fields";
  });
}
