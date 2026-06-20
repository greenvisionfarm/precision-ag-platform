/**
 * Export — экспорт поля в various форматы.
 */
import API, { fetchApi } from "../api.js";
import { showMessage } from "../utils.js";
import { downloadKmzWithSettings } from "../modals.js";

function downloadBlob(blob, filename) {
  if (!(blob instanceof Blob)) {
    blob = new Blob([blob], { type: "application/octet-stream" });
  }
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  setTimeout(() => { URL.revokeObjectURL(url); a.remove(); }, 100);
}

export function initExportHandlers(getFieldId) {
  // ISOXML export
  $(document).on("click", "#detail-export-isoxml", function(e) {
    e.preventDefault();
    const fieldId = getFieldId();
    if (!fieldId) return;

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
        if (!name) { Swal.showValidationMessage("Введите название продукта"); return false; }
        return { product_name: name, product_type: type };
      }
    }).then(res => {
      if (!res.isConfirmed) return;
      showMessage("Генерация ISOXML...", "info");
      API.exportIsoxml(fieldId, res.value).then(blob => {
        console.log("[isoxml] Downloaded blob:", blob?.constructor?.name, blob?.size);
        downloadBlob(blob, `field_${fieldId}_isoxml.xml`);
        showMessage("ISOXML экспортирован", "success");
      }).catch(err => {
        console.error("[isoxml] Export failed:", err);
        showMessage("Ошибка экспорта ISOXML", "error");
      });
    });
  });

  // TaskData export
  $(document).on("click", "#detail-export-taskdata", function(e) {
    e.preventDefault();
    const fieldId = getFieldId();
    if (!fieldId) return;

    const today = new Date().toISOString().split("T")[0];

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
              </div>
              <div style="flex: 1; min-width: 120px;">
                <label style="display: block; margin-bottom: 3px;">Остаточный спрос [%]:</label>
                <select id="swal-td-residual" class="swal2-select" style="margin: 0; width: 100%;">
                  <option value="0">0%</option>
                  <option value="1" selected>100%</option>
                  <option value="2">200%</option>
                </select>
              </div>
            </div>
            <div id="swal-td-rates" style="margin-top: 8px;">
              <label style="display: block; margin-bottom: 3px;">Норма [кг/га]:</label>
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
            </div>
          </fieldset>
          <fieldset style="border: 1px solid var(--border-color); border-radius: 6px; padding: 10px;">
            <legend style="font-weight: 600; padding: 0 6px;">Грид</legend>
            <label style="display: block; margin-bottom: 3px;">Разрешение:</label>
            <select id="swal-td-resolution" class="swal2-select" style="margin: 0; width: 100%;">
              <option value="1">1 м</option>
              <option value="2" selected>2 м</option>
              <option value="5">5 м</option>
              <option value="10">10 м</option>
            </select>
          </fieldset>
          <div style="background: #f0f0f0; padding: 8px 10px; border-radius: 6px; font-size: 0.85em;">
            <strong>Формат:</strong> TaskData.zip (ISO 11783 v3.3)
          </div>
        </div>`,
      width: "560px",
      focusConfirm: false,
      didOpen: () => {
        const modeSelect = document.getElementById("swal-td-rate-mode");
        const constWrap = document.getElementById("swal-td-const-wrap");
        const rateMin = document.getElementById("swal-td-rate-min");
        const rateMax = document.getElementById("swal-td-rate-max");

        function updateRateMode() {
          const isConst = modeSelect.value === "constant";
          constWrap.style.display = isConst ? "block" : "none";
          rateMin.disabled = isConst;
          rateMax.disabled = isConst;
          rateMin.style.opacity = isConst ? "0.5" : "1";
          rateMax.style.opacity = isConst ? "0.5" : "1";
        }
        modeSelect.addEventListener("change", updateRateMode);
        updateRateMode();
      },
      preConfirm: () => {
        const product = document.getElementById("swal-td-product").value.trim();
        if (!product) { Swal.showValidationMessage("Введите название продукта"); return false; }
        return {
          product_name: product,
          product_group: document.getElementById("swal-td-group").value,
          nutrient: document.getElementById("swal-td-nutrient").value,
          application_date: document.getElementById("swal-td-date").value,
          farm_name: document.getElementById("swal-td-farm").value.trim() || null,
          resolution: parseFloat(document.getElementById("swal-td-resolution").value),
          rate_mode: document.getElementById("swal-td-rate-mode").value,
          rate_min: parseFloat(document.getElementById("swal-td-rate-min").value) || 100,
          rate_max: parseFloat(document.getElementById("swal-td-rate-max").value) || 400,
          constant_rate: document.getElementById("swal-td-rate-mode").value === "constant" ? parseFloat(document.getElementById("swal-td-rate-const").value) || 250 : null,
          residual_pct: parseFloat(document.getElementById("swal-td-residual").value) || 1
        };
      }
    }).then(res => {
      if (!res.isConfirmed) return;
      showMessage("Генерация TaskData.zip...", "info");
      API.exportTaskData(fieldId, res.value).then(blob => {
        console.log("[taskdata] Downloaded blob:", blob?.constructor?.name, blob?.size);
        downloadBlob(blob, `field_${fieldId}_taskdata.zip`);
        showMessage("TaskData экспортирован", "success");
      }).catch(err => {
        console.error("[taskdata] Export failed:", err);
        showMessage("Ошибка экспорта TaskData", "error");
      });
    });
  });

  // KMZ export
  $(document).on("click", "#detail-export-kmz", function(e) {
    e.preventDefault();
    const fieldId = getFieldId();
    if (!fieldId) return;
    downloadKmzWithSettings(fieldId);
  });

  // Delete field
  $(document).on("click", "#detail-delete-field", function() {
    const fieldId = getFieldId();
    if (!fieldId) return;
    Swal.fire({
      title: "Удалить поле?",
      text: "Все сканы и зоны будут удалены. Это действие необратимо.",
      icon: "warning",
      showCancelButton: true,
      confirmButtonColor: "#dc3545",
      confirmButtonText: "Да, удалить",
      cancelButtonText: "Отмена"
    }).then(result => {
      if (!result.isConfirmed) return;
      API.deleteField(fieldId).then(() => {
        showMessage("Поле удалено", "success");
        window.location.hash = "#fields";
      });
    });
  });

  // NDVI upload from header
  $(document).on("change", "#field-ndvi-input", function() {
    const file = this.files[0];
    const fieldId = getFieldId();
    if (!file || !fieldId) return;

    showMessage("Загрузка NDVI...", "info");
    const formData = new FormData();
    formData.append("raster_file", file);

    fetchApi("/api/raster/upload", { method: "POST", body: formData })
      .then(() => {
        showMessage("NDVI загружен! Зоны появятся через несколько секунд.", "success");
        $("#field-ndvi-input").val();
      })
      .catch((err) => {
        showMessage(err.message || "Ошибка загрузки", "error");
        $("#field-ndvi-input").val();
      });
  });
}
