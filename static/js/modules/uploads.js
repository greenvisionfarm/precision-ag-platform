/**
 * Загрузка файлов (GeoTIFF, Shapefile) и обработка задач.
 */
import { showMessage } from "./utils.js";
import API, { fetchApi } from "./api.js";
import { register, updateProgress, complete } from "./upload-manager.js";

/**
 * Инициализирует форму загрузки Shapefile.
 */
export function initShapefileUpload() {
  $("#shapefile-input").on("change", function() {
    const fileName = this.files[0]?.name || "Выберите ZIP файл";
    $(this).siblings(".file-input-label").html(`<i class="fas fa-file-archive"></i> ${fileName}`);
    const hasFiles = this.files.length > 0;
    $("#upload-button").toggleClass("hidden", !hasFiles).css("display", hasFiles ? "" : "");
  });

  $("#upload-form").on("submit", function(e) {
    e.preventDefault();
    const form = this;
    const statusDiv = $("#upload-status");
    const btn = $("#upload-button");
    const file = this.shapefile_zip?.files[0];
    const uploadId = file ? register({ type: "shapefile", filename: file.name }) : null;

    statusDiv.removeClass("text-success text-danger").html("<i class=\"fas fa-spinner fa-spin\"></i> Загрузка...");
    btn.prop("disabled", true);

    fetchApi("/upload", { method: "POST", body: new FormData(this) })
      .then((res) => {
        console.log("[upload] Server response:", res);
        if (res.features && res.features.length > 0) {
          showShapefilePreviewModal(res.features, uploadId);
        } else {
          console.warn("[upload] No features found in response:", res);
          statusDiv.addClass("text-success").html("<i class=\"fas fa-check\"></i> Файл загружен, но полей не найдено.");
          if (uploadId) complete(uploadId, { status: "completed", message: "Полей нет" });
        }
        btn.prop("disabled", false);
      })
      .catch((err) => {
        console.error("[upload] Upload failed:", err);
        statusDiv.addClass("text-danger").html("<i class=\"fas fa-exclamation-triangle\"></i> Ошибка загрузки");
        btn.prop("disabled", false);
        showMessage("Ошибка загрузки файла", "error");
        if (uploadId) complete(uploadId, { status: "error", message: "Ошибка загрузки" });
      });
  });
}

/**
 * Показывает модальное окно предпросмотра импортированных полей.
 */
function showShapefilePreviewModal(features, uploadId) {
  fetchApi("/api/fields").then((fc) => {
    const existingNames = new Set((fc.features || []).map(f => (f.properties.name || "").toLowerCase()));

    function renderRows() {
      const rows = document.querySelectorAll("#import-preview-body tr");
      let dupeCount = 0;
      const usedNames = new Set(
        Array.from(document.querySelectorAll("#import-preview-body .import-field-name"))
          .map(el => el.value.toLowerCase())
      );
      const existingUsedNames = new Set(
        Array.from(document.querySelectorAll("#import-preview-body"))
          .flatMap(() => [])
      );

      rows.forEach(row => {
        const nameInput = row.querySelector(".import-field-name");
        const name = (nameInput?.value || "").toLowerCase();
        const isOriginalDupe = existingNames.has(name);
        const input = row.querySelector(".import-field-name");
        if (input) {
          input.style.borderColor = isOriginalDupe ? "#ffc107" : "var(--border-color)";
        }
        const tag = row.querySelector(".import-dupe-tag");
        if (tag) tag.style.display = isOriginalDupe ? "" : "none";
        if (isOriginalDupe) dupeCount++;
      });

      const saveBtn = Swal.getConfirmButton();
      if (saveBtn) {
        saveBtn.disabled = dupeCount > 0;
        saveBtn.title = dupeCount > 0 ? `Устраните ${dupeCount} дубликат(ов) перед сохранением` : "";
      }
      const counter = document.getElementById("import-dupe-counter");
      if (counter) {
        counter.textContent = dupeCount > 0
          ? `${dupeCount} поле(ей) с дублирующимся названием — измените название или удалите`
          : "Все конфликты разрешены";
        counter.style.color = dupeCount > 0 ? "#ffc107" : "#28a745";
      }
    }

    const KEY_PROPS = ["Main_Crop", "MainCropExp", "ha", "Field_No_"];
    let rows = features.map((f, i) => {
      const isDupe = existingNames.has(f.name.toLowerCase());
      const crop = f.properties.MainCropExp || f.properties.Main_Crop || "";
      const ha = f.area_ha > 0 ? `${f.area_ha} га` : "";
      const fieldNo = f.properties.Field_No_ || "";
      const details = [crop, ha, fieldNo ? `№${fieldNo}` : ""].filter(Boolean).join(" · ");
      return `
      <tr data-index="${i}" style="border-bottom:1px solid var(--border-color);">
        <td style="padding:6px 4px;">
          <input type="text" class="import-field-name" value="${escapeHtml(f.name)}" style="width:100%;padding:6px;border:1px solid ${isDupe ? '#ffc107' : 'var(--border-color)'};border-radius:4px;background:var(--bg-secondary);color:var(--text-color);font-size:0.95em;">
          <span class="import-dupe-tag" style="display:${isDupe ? '' : 'none'};color:#ffc107;font-size:0.8em;"><i class="fas fa-exclamation-triangle"></i> дубль</span>
        </td>
        <td style="padding:6px 4px;white-space:nowrap;font-size:0.9em;">${details || "—"}</td>
        <td style="padding:6px 4px;"><button class="btn btn-sm import-delete-btn" style="color:#dc3545;background:none;border:none;padding:4px 8px;font-size:1.1em;"><i class="fas fa-trash"></i></button></td>
      </tr>`;
    }).join('');

    Swal.fire({
    title: `Импорт полей (${features.length})`,
    html: `
      <div style="text-align:left;max-height:55vh;overflow:auto;">
        <table style="width:100%;border-collapse:collapse;font-size:0.9em;">
          <thead>
            <tr style="border-bottom:2px solid var(--border-color);text-align:left;">
              <th style="padding:6px;">Название</th>
              <th style="padding:6px;">Культура · Площадь</th>
              <th style="padding:6px;"></th>
            </tr>
          </thead>
          <tbody id="import-preview-body">
            ${rows}
          </tbody>
        </table>
      </div>
      <p id="import-dupe-counter" style="margin-top:10px;font-size:0.85em;font-weight:600;"></p>
    `,
    width: "650px",
    showCancelButton: true,
    confirmButtonText: '<i class="fas fa-save"></i> Сохранить',
    cancelButtonText: '<i class="fas fa-times"></i> Отмена',
    confirmButtonColor: "#28a745",
    didOpen: () => {
      const body = Swal.getHtmlContainer().querySelector("#import-preview-body");
      body.addEventListener("click", (e) => {
        const btn = e.target.closest(".import-delete-btn");
        if (btn) {
          btn.closest("tr").remove();
          renderRows();
        }
      });
      body.addEventListener("input", (e) => {
        if (e.target.classList.contains("import-field-name")) renderRows();
      });
      renderRows();
    },
    preConfirm: () => {
      const rows = Swal.getHtmlContainer().querySelectorAll("#import-preview-body tr");
      const result = [];
      rows.forEach((row, i) => {
        const nameInput = row.querySelector(".import-field-name");
        const idx = parseInt(row.dataset.index);
        result.push({
          name: nameInput ? nameInput.value : features[idx].name,
          geometry_wkt: features[idx].geometry_wkt,
          properties: features[idx].properties,
          area_ha: features[idx].area_ha
        });
      });
      return result;
    }
    }).then((result) => {
    if (!result.isConfirmed) return;
    if (result.value.length === 0) {
      showMessage("Все поля удалены, нечего сохранять", "warning");
      return;
    }
    console.log("[import] Confirming import:", result.value.length, "features");
    fetchApi("/api/fields/confirm_import", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ features: result.value })
    }).then((res) => {
      console.log("[import] Server response:", res);
      showMessage(res.message || "Поля сохранены", "success");
      window.loadMapData?.();
      window.getFieldsTable?.()?.ajax.reload();
      const statusDiv = $("#upload-status");
      statusDiv.addClass("text-success").html("<i class=\"fas fa-check\"></i> Поля сохранены!");
      if (uploadId) complete(uploadId, { status: "completed", message: res.message });
      setTimeout(() => statusDiv.removeClass("text-success").html(""), 3000);
    }).catch((err) => {
      console.error("[import] Confirm import failed:", err);
      showMessage("Ошибка сохранения полей", "error");
      if (uploadId) complete(uploadId, { status: "error", message: "Ошибка сохранения" });
    });
  });
  }).catch(() => {
    showMessage("Не удалось загрузить данные для проверки дублей", "warning");
  });
}

function escapeHtml(str) {
  return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

/**
 * Инициализирует форму загрузки NDVI (GeoTIFF).
 */
export function initRasterUpload() {
  $("#raster-input").on("change", function() {
    const fileName = this.files[0]?.name || "Выберите TIF файл";
    $(this).siblings(".file-input-label").html(`<i class="fas fa-file-image"></i> ${fileName}`);
    const hasFiles = this.files.length > 0;
    $("#raster-upload-button").toggleClass("hidden", !hasFiles).css("display", hasFiles ? "" : "");
  });

  $("#raster-upload-form").on("submit", function(e) {
    e.preventDefault();
    const form = this;
    const statusDiv = $("#raster-upload-status");
    const btn = $("#raster-upload-button");
    const file = $("#raster-input")[0].files[0];
    const uploadId = file ? register({ type: "raster", filename: file.name }) : null;

    statusDiv.removeClass("text-success text-danger").html("<i class=\"fas fa-spinner fa-spin\"></i> Загрузка...");
    btn.prop("disabled", true);

    const formData = new FormData();
    formData.append("raster_file", file);

    fetchApi("/api/raster/upload", { method: "POST", body: formData })
      .then((res) => {
        statusDiv.addClass("text-success").html("<i class=\"fas fa-check\"></i> NDVI загружен! Обработка зон...");
        window.loadMapData?.();

        if (window.loadFieldScans && res.field_id) {
          setTimeout(() => {
            window.loadFieldScans(res.field_id);
          }, 2000);
        }

        form.reset();
        $(form).find(".file-input-label").html("<i class=\"fas fa-file-upload\"></i> Выберите TIF файл");
        btn.addClass("hidden");
        if (uploadId) complete(uploadId, { status: "completed", message: "Загружен" });
        setTimeout(() => {
          statusDiv.removeClass("text-success").html("");
          btn.prop("disabled", false);
        }, 5000);

        showMessage("NDVI файл загружен. Зоны появятся через несколько секунд.", "success");
      })
      .catch((err) => {
        const errMsg = err.message || "Ошибка загрузки";
        statusDiv.addClass("text-danger").html(`<i class=\"fas fa-exclamation-triangle\"></i> ${errMsg}`);
        btn.prop("disabled", false);
        showMessage(errMsg, "error");
        if (uploadId) complete(uploadId, { status: "error", message: errMsg });
      });
  });
}

/**
 * Инициализирует форму загрузки снимков с дрона.
 */
export function initDroneUpload() {
  // Загрузка файлов
  $("#drone-input").on("change", function() {
    const files = this.files;
    let fileName;
    
    if (files.length > 1) {
      fileName = `Файлов: ${files.length}`;
    } else if (files.length === 1) {
      fileName = files[0].name;
    } else {
      fileName = "Выберите ZIP или снимки";
    }
    
    const hasFiles = this.files.length > 0;
    $(this).siblings(".file-input-label").html(`<i class="fas fa-file-archive"></i> ${fileName}`);
    $("#drone-upload-button").toggleClass("hidden", !hasFiles).css("display", hasFiles ? "" : "");
  });

  // Заполняем список полей
  loadFieldsForDropdown();

  // Обработка формы
  $("#drone-upload-form").on("submit", function(e) {
    e.preventDefault();
    const form = this;
    const statusDiv = $("#drone-upload-status");
    const progressDiv = $("#drone-progress");
    const progressFill = progressDiv.find(".progress-fill");
    const progressText = progressDiv.find(".progress-text");
    const stepsDiv = $("#drone-steps");
    const btn = $("#drone-upload-button");
    const fieldId = $("#drone-field-select").val();
    const cropType = $("#drone-crop-type").val();
    const file = $("#drone-input")[0].files[0];

    if (!file) {
      showMessage("Выберите файл для загрузки", "warning");
      return;
    }

    // Проверка размера файла (макс 8GB — совпадает с nginx и tornado)
    const MAX_SIZE = 8 * 1024 * 1024 * 1024;
    if (file.size > MAX_SIZE) {
      showMessage(`Файл слишком большой (${(file.size / 1024 / 1024 / 1024).toFixed(1)} GB). Максимум 8 GB.`, "error");
      return;
    }

    const fileSizeMB = (file.size / 1024 / 1024).toFixed(0);
    statusDiv.removeClass("text-success text-danger").html("");
    progressDiv.removeClass("hidden").show();
    stepsDiv.removeClass("hidden").show();
    btn.prop("disabled", true).addClass("hidden");

    // Обновляем шаги
    function setStep(step, text) {
      stepsDiv.find(".step").removeClass("active done");
      stepsDiv.find(".step").each(function(i) {
        if (i < step) $(this).addClass("done");
        if (i === step) $(this).addClass("active");
      });
      stepsDiv.find(".step-text").text(text);
    }

    setStep(0, `Загрузка на сервер (${fileSizeMB} MB)...`);
    progressFill.css("width", "0%");
    progressText.text("0%");

    // Создаём FormData
    const isOrthomosaic = !$("#drone-fast-mode").is(":checked");
    const formData = new FormData();
    formData.append("data", JSON.stringify({
      field_id: fieldId || null,
      crop_type: cropType,
      processing_mode: isOrthomosaic ? "orthomosaic" : "fast"
    }));
    formData.append("drone_images", file);

    const xhr = new XMLHttpRequest();
    xhr.open("POST", "/api/drone/upload", true);
    xhr.timeout = 3600000;

    // Регистрируем в менеджере загрузок
    const uploadId = register({ type: "drone", filename: file.name, xhr });

    // Прогресс загрузки файла
    xhr.upload.onprogress = function(e) {
      if (e.lengthComputable) {
        const pct = Math.round((e.loaded / e.total) * 100);
        const loadedMB = (e.loaded / 1024 / 1024).toFixed(0);
        const totalMB = (e.total / 1024 / 1024).toFixed(0);
        progressFill.css("width", `${pct}%`);
        progressText.text(`${pct}% — ${loadedMB} / ${totalMB} MB`);
        updateProgress(uploadId, { progress: pct, message: `${loadedMB} / ${totalMB} MB` });
      }
    };

    xhr.onload = function() {
      if (xhr.status >= 200 && xhr.status < 300) {
        const res = JSON.parse(xhr.responseText);
        const modeLabel = res.processing_mode === "orthomosaic" ? "ортомозаика" : "быстрая";

        setStep(2, `Обработка (${modeLabel}) запущена`);
        progressFill.css("width", "100%");
        progressText.text("Готово");

        updateProgress(uploadId, { status: "processing", progress: 100, message: `Обработка (${modeLabel})` });

        statusDiv.removeClass("text-danger").addClass("text-success")
          .html(`<i class="fas fa-check"></i> Архив принят! Обработка (${modeLabel}) запущена...`);
        statusDiv.show();

        if (res.task_id) {
          pollDroneTaskStatus(res.task_id, res.field_id, uploadId);
        }

        if (res.flight_date && res.scan_id) {
          const detected = new Date(res.flight_date);
          const dateStr = detected.toISOString().slice(0, 10);
          const timeStr = detected.toTimeString().slice(0, 5);
          Swal.fire({
            title: "Дата съёмки",
            html: `Обнаружена дата из имени файла:<br><strong>${dateStr} ${timeStr}</strong><br><br>Измените при необходимости:`,
            input: "date",
            inputValue: dateStr,
            showCancelButton: true,
            confirmButtonText: "Сохранить",
            cancelButtonText: "Оставить как есть",
            reverseButtons: true
          }).then(result => {
            if (result.isConfirmed && result.value) {
              const newDate = result.value + "T" + timeStr + ":00";
              fetchApi(`/api/scan/${res.scan_id}/update_date`, {
                method: "POST",
                body: { flight_date: newDate }
              }).catch(() => {});
            }
          });
        }

        form.reset();
        $(form).find(".file-input-label").html("<i class=\"fas fa-file-upload\"></i> Выберите ZIP или снимки");
      } else {
        let err;
        if (xhr.status === 413) {
          err = "Файл слишком большой для сервера.";
        } else if (xhr.status === 502) {
          err = "Сервер перегружен. Попробуйте позже.";
        } else {
          try {
            err = JSON.parse(xhr.responseText).error;
          } catch(e) {
            err = `Ошибка загрузки (HTTP ${xhr.status})`;
          }
        }
        statusDiv.removeClass("text-success").addClass("text-danger")
          .html(`<i class="fas fa-exclamation-triangle"></i> ${err}`);
        statusDiv.show();
        progressDiv.addClass("hidden");
        stepsDiv.addClass("hidden");
        btn.prop("disabled", false).removeClass("hidden");
        showMessage(err, "error");
        complete(uploadId, { status: "error", message: err });
      }
    };

    xhr.onerror = function() {
      statusDiv.removeClass("text-success").addClass("text-danger")
        .html("<i class=\"fas fa-exclamation-triangle\"></i> Нет соединения с сервером. Проверьте интернет.");
      statusDiv.show();
      progressDiv.addClass("hidden");
      stepsDiv.addClass("hidden");
      btn.prop("disabled", false).removeClass("hidden");
      showMessage("Нет соединения с сервером", "error");
      complete(uploadId, { status: "error", message: "Нет соединения с сервером" });
    };

    xhr.ontimeout = function() {
      statusDiv.removeClass("text-success").addClass("text-danger")
        .html("<i class=\"fas fa-exclamation-triangle\"></i> Превышено время ожидания.");
      statusDiv.show();
      progressDiv.addClass("hidden");
      stepsDiv.addClass("hidden");
      btn.prop("disabled", false).removeClass("hidden");
      showMessage("Превышено время ожидания", "error");
      complete(uploadId, { status: "error", message: "Превышено время ожидания" });
    };

    // Симулируем серверные этапы после завершения загрузки
    xhr.upload.onload = function() {
      setStep(1, "Сохранение на диск...");
      progressFill.css("width", "100%");
      progressText.text("Загрузка завершена, обработка...");
      updateProgress(uploadId, { message: "Сохранение на диск..." });
    };

    xhr.send(formData);
  });
}

/**
 * Загружает список полей для dropdown.
 */
function loadFieldsForDropdown() {
  API.getFields().then(fields => {
    const select = $("#drone-field-select");
    fields.features.forEach(field => {
      const name = field.properties.name || `Поле #${field.properties.db_id}`;
      select.append(`<option value="${field.properties.db_id}">${name}</option>`);
    });
  }).catch(() => {
    // Игнорируем ошибку
  });
}

/**
 * Опрашивает статус задачи обработки снимков с дрона.
 * @param {string} taskId - ID задачи.
 * @param {string|number} fieldId - ID поля.
 */
function pollDroneTaskStatus(taskId, fieldId, uploadId) {
  const statusDiv = $("#drone-upload-status");
  const progressDiv = $("#drone-progress");
  const progressFill = progressDiv.find(".progress-fill");
  const progressText = progressDiv.find(".progress-text");
  const stepsDiv = $("#drone-steps");
  
  let progress = 50;
  
  // Обновляем шаг на "Обработка"
  stepsDiv.find(".step").removeClass("active done");
  stepsDiv.find(".step").eq(0).addClass("done");
  stepsDiv.find(".step").eq(1).addClass("done");
  stepsDiv.find(".step").eq(2).addClass("active");
  stepsDiv.find(".step-text").text("Обработка снимков...");
  
  progressFill.css("width", `${progress}%`);
  progressText.text(`${progress}% — обработка...`);
  
  const interval = setInterval(() => {
    API.getTaskStatus(taskId).then(res => {
      if (res.status === "completed") {
        clearInterval(interval);
        progressDiv.addClass("hidden");
        stepsDiv.find(".step").removeClass("active");
        stepsDiv.find(".step").addClass("done");
        stepsDiv.find(".step-text").text("Готово!");
        statusDiv.removeClass("text-danger").addClass("text-success")
          .html("<i class=\"fas fa-check-circle\"></i> Обработка завершена! Зоны созданы.");
        showMessage("Обработка завершена! Зоны NDVI созданы.", "success");
        complete(uploadId, { status: "completed", message: "Обработка завершена" });
        
        setTimeout(() => {
          stepsDiv.addClass("hidden");
          if (fieldId) {
            window.location.hash = `#field/${fieldId}`;
          }
          window.loadMapData?.();
          statusDiv.removeClass("text-success").html("");
        }, 3000);
        
      } else if (res.status === "error") {
        clearInterval(interval);
        progressDiv.addClass("hidden");
        stepsDiv.addClass("hidden");
        statusDiv.removeClass("text-success").addClass("text-danger")
          .html(`<i class="fas fa-exclamation-triangle"></i> Ошибка: ${res.message || "Ошибка обработки"}`);
        showMessage(res.message || "Ошибка обработки дрон-данных", "error");
        complete(uploadId, { status: "error", message: res.message || "Ошибка обработки" });
        
      } else {
        progress = Math.min(progress + 5, 95);
        progressFill.css("width", `${progress}%`);
        progressText.text(`${progress}% — ${res.message || "Обработка снимков..."}`);
        stepsDiv.find(".step-text").text(res.message || "Обработка снимков...");
        updateProgress(uploadId, { progress, message: res.message || "Обработка снимков..." });
      }
    }).catch(() => {
      // Игнорируем ошибки сети, продолжаем опрос
    });
  }, 3000);
}
