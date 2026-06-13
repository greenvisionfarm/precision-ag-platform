/**
 * Загрузка файлов (GeoTIFF, Shapefile) и обработка задач.
 */
import { showMessage } from './utils.js';
import API from './api.js';

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

    statusDiv.removeClass("text-success text-danger").html("<i class=\"fas fa-spinner fa-spin\"></i> Загрузка...");
    btn.prop("disabled", true);

    $.ajax({
      url: "/upload",
      type: "POST",
      data: new FormData(this),
      processData: false,
      contentType: false,
      success: (res) => {
        statusDiv.addClass("text-success").html("<i class=\"fas fa-check\"></i> Успешно загружено!");
        window.loadMapData?.();
        window.getFieldsTable?.()?.ajax.reload();
        form.reset();
        $(form).find(".file-input-label").html('<i class="fas fa-file-upload"></i> Выберите ZIP файл');
        btn.addClass("hidden");
        setTimeout(() => {
          statusDiv.removeClass("text-success").html("");
          btn.prop("disabled", false);
        }, 3000);
      },
      error: () => {
        statusDiv.addClass("text-danger").html("<i class=\"fas fa-exclamation-triangle\"></i> Ошибка загрузки");
        btn.prop("disabled", false);
        showMessage("Ошибка загрузки файла", "error");
      }
    });
  });
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

    statusDiv.removeClass("text-success text-danger").html("<i class=\"fas fa-spinner fa-spin\"></i> Загрузка...");
    btn.prop("disabled", true);

    const formData = new FormData();
    formData.append("raster_file", $("#raster-input")[0].files[0]);

    $.ajax({
      url: "/api/raster/upload",
      type: "POST",
      data: formData,
      processData: false,
      contentType: false,
      success: (res) => {
        statusDiv.addClass("text-success").html("<i class=\"fas fa-check\"></i> NDVI загружен! Обработка зон...");
        window.loadMapData?.();

        // Если открыта детальная страница поля, обновляем сканы
        if (window.loadFieldScans && res.field_id) {
          setTimeout(() => {
            window.loadFieldScans(res.field_id);
          }, 2000); // Ждем 2 секунды чтобы worker успел обработать
        }

        form.reset();
        $(form).find(".file-input-label").html('<i class="fas fa-file-upload"></i> Выберите TIF файл');
        btn.addClass("hidden");
        setTimeout(() => {
          statusDiv.removeClass("text-success").html("");
          btn.prop("disabled", false);
        }, 5000);

        showMessage(`NDVI файл загружен. Зоны появятся через несколько секунд.`, "success");
      },
      error: (xhr) => {
        const err = xhr.responseJSON?.error || "Ошибка загрузки";
        statusDiv.addClass("text-danger").html(`<i class="fas fa-exclamation-triangle"></i> ${err}`);
        btn.prop("disabled", false);
        showMessage(err, "error");
      }
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
    const btn = $("#drone-upload-button");
    const fieldId = $("#drone-field-select").val();
    const cropType = $("#drone-crop-type").val();
    const fertilizer = $("#drone-fertilizer").val();
    const file = $("#drone-input")[0].files[0];

    if (!file) {
      showMessage("Выберите файл для загрузки", "warning");
      return;
    }

    // Проверка размера файла (макс 6GB)
    const MAX_SIZE = 6 * 1024 * 1024 * 1024;
    if (file.size > MAX_SIZE) {
      showMessage(`Файл слишком большой (${(file.size / 1024 / 1024 / 1024).toFixed(1)} GB). Максимум 6 GB.`, "error");
      return;
    }

    statusDiv.removeClass("text-success text-danger")
      .html('<i class="fas fa-spinner fa-spin"></i> Загрузка архива...');
    progressDiv.removeClass("hidden").show();
    btn.prop("disabled", true).addClass("hidden");

    // Создаём FormData
    const formData = new FormData();
    formData.append("drone_images", file);
    formData.append("data", JSON.stringify({
      field_id: fieldId || null,
      crop_type: cropType,
      processing_mode: "fast",
      total_fertilizer_kg: fertilizer ? parseFloat(fertilizer) : null
    }));

    $.ajax({
      url: "/api/drone/upload",
      type: "POST",
      data: formData,
      processData: false,
      contentType: false,
      timeout: 600000,
      success: (res) => {
        statusDiv.removeClass("text-danger").addClass("text-success")
          .html('<i class="fas fa-check"></i> Архив принят! Обработка запущена...');
        statusDiv.show();
        
        if (res.task_id) {
          pollDroneTaskStatus(res.task_id, res.field_id);
        }
        
        form.reset();
        $(form).find(".file-input-label").html('<i class="fas fa-file-upload"></i> Выберите ZIP или снимки');
      },
      error: (xhr) => {
        let err;
        if (xhr.status === 0) {
          err = "Нет соединения с сервером. Проверьте интернет.";
        } else if (xhr.status === 413) {
          err = "Файл слишком большой для сервера.";
        } else if (xhr.status === 502) {
          err = "Сервер перегружен. Попробуйте позже.";
        } else {
          err = xhr.responseJSON?.error || `Ошибка загрузки (HTTP ${xhr.status})`;
        }
        statusDiv.removeClass("text-success").addClass("text-danger")
          .html(`<i class="fas fa-exclamation-triangle"></i> ${err}`);
        statusDiv.show();
        progressDiv.addClass("hidden");
        btn.prop("disabled", false).removeClass("hidden");
        showMessage(err, "error");
      }
    });
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
function pollDroneTaskStatus(taskId, fieldId) {
  const statusDiv = $("#drone-upload-status");
  const progressDiv = $("#drone-progress");
  const progressFill = progressDiv.find(".progress-fill");
  const progressText = progressDiv.find(".progress-text");
  
  let progress = 0;
  
  const interval = setInterval(() => {
    API.getTaskStatus(taskId).then(res => {
      if (res.status === "completed") {
        clearInterval(interval);
        progressDiv.addClass("hidden");
        statusDiv.removeClass("text-danger").addClass("text-success")
          .html('<i class="fas fa-check-circle"></i> Обработка завершена! Зоны созданы.');
        showMessage("Обработка завершена! Зоны NDVI созданы.", "success");
        
        setTimeout(() => {
          if (fieldId) {
            window.location.hash = `#field/${fieldId}`;
            window.showFieldDetail?.(fieldId);
          }
          window.loadMapData?.();
          statusDiv.removeClass("text-success").html("");
        }, 3000);
        
      } else if (res.status === "error") {
        clearInterval(interval);
        progressDiv.addClass("hidden");
        statusDiv.removeClass("text-success").addClass("text-danger")
          .html(`<i class="fas fa-exclamation-triangle"></i> Ошибка: ${res.message || "Ошибка обработки"}`);
        showMessage(res.message || "Ошибка обработки дрон-данных", "error");
        
      } else {
        progress = Math.min(progress + 5, 95);
        progressFill.css("width", `${progress}%`);
        progressText.text(res.message || "Обработка снимков...");
      }
    }).catch(() => {
      // Игнорируем ошибки сети, продолжаем опрос
    });
  }, 3000);
}
