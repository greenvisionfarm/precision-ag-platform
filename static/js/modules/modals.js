/**
 * Модальные окна и диалоги.
 */
import { showMessage } from './utils.js';
import API from './api.js';

/**
 * Открывает модальное окно с деталями поля.
 * @param {string|number} id - ID поля.
 */
export function openFieldModal(id) {
  // Показываем прелоадер
  Swal.fire({
    title: "Загрузка...",
    allowOutsideClick: false,
    didOpen: () => Swal.showLoading()
  });

  API.getField(id).then(field => {
    const area = field.area;
    const owner = field.owner || "Не назначен";
    const status = field.land_status || "Не указан";
    const parcel = field.parcel_number || "N/A";

    Swal.fire({
      title: field.name,
      html: `
        <div class="modal-detail-grid">
          <div id="modal-field-map" class="modal-field-map"></div>
          <table class="info-table">
            <tr><th>Площадь:</th><td>${area}</td></tr>
            <tr><th>Владелец:</th><td>${owner}</td></tr>
            <tr><th>Статус:</th><td>${status}</td></tr>
            <tr><th>Кадастровый №:</th><td>${parcel}</td></tr>
          </table>
          <div class="modal-actions">
            <button id="modal-export-kmz" class="btn btn-primary btn-sm"><i class="fas fa-file-download"></i> Экспорт KMZ</button>
            <button id="modal-go-to-detail" class="btn btn-outline-primary btn-sm"><i class="fas fa-external-link-alt"></i> На страницу поля</button>
          </div>
        </div>
      `,
      width: "600px",
      showConfirmButton: false,
      showCloseButton: true,
      didOpen: () => {
        // Инициализируем карту в модальном окне с зонами
        window.MapManager.initDetailMap("modal-field-map", field.geometry, field.zones);

        $("#modal-export-kmz").on("click", () => {
          Swal.close();
          downloadKmzWithSettings(id);
        });

        $("#modal-go-to-detail").on("click", () => {
          Swal.close();
          window.location.hash = `#field/${id}`;
        });
      }
    });
  }).fail(() => {
    showMessage("Не удалось загрузить данные поля", "error");
  });
}

/**
 * Диалог настройки экспорта KMZ.
 * @param {string|number} fieldId - ID поля.
 */
export function downloadKmzWithSettings(fieldId) {
  Swal.fire({
    title: "Настройки DJI KMZ",
    html: `
      <div class="kmz-settings-grid">
        <div class="kmz-field">
          <label for="swal-h">Высота полета (м):</label>
          <input type="number" id="swal-h" class="swal2-input" value="100" min="20" max="150">
          <small>Высота над точкой взлета. Для NDVI оптимально 100-120м.</small>
        </div>
        <div class="kmz-field">
          <label for="swal-oh">Фронтальное перекрытие (%):</label>
          <input type="number" id="swal-oh" class="swal2-input" value="80" min="40" max="90">
          <small>Наложение снимков по ходу движения. Нужно 75-80%.</small>
        </div>
        <div class="kmz-field">
          <label for="swal-ow">Боковое перекрытие (%):</label>
          <input type="number" id="swal-ow" class="swal2-input" value="70" min="40" max="90">
          <small>Наложение между проходами (галсами). Обычно 70-75%.</small>
        </div>
        <div class="kmz-field">
          <label for="swal-dir">Угол курса (град):</label>
          <input type="number" id="swal-dir" class="swal2-input" value="0" min="0" max="360">
          <small>Направление полета. 0 - север, 90 - восток.</small>
        </div>
      </div>`,
    width: "700px",
    focusConfirm: false,
    preConfirm: () => {
      return {
        height: document.getElementById("swal-h").value,
        oh: document.getElementById("swal-oh").value,
        ow: document.getElementById("swal-ow").value,
        dir: document.getElementById("swal-dir").value
      };
    }
  }).then(res => {
    if (res.isConfirmed) {
      const p = res.value;
      const url = "/api/field/export/kmz/" + fieldId +
        "?height=" + p.height +
        "&overlap_h=" + p.oh +
        "&overlap_w=" + p.ow +
        "&direction=" + p.dir;
      window.location.href = url;
    }
  });
}
