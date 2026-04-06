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
    $("#upload-button").toggle(this.files.length > 0);
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
        btn.hide();
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
    $("#raster-upload-button").toggle(this.files.length > 0);
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
        statusDiv.addClass("text-success").html("<i class=\"fas fa-check\"></i> NDVI загружен!");
        window.loadMapData?.();
        form.reset();
        $(form).find(".file-input-label").html('<i class="fas fa-file-upload"></i> Выберите TIF файл');
        btn.hide();
        setTimeout(() => {
          statusDiv.removeClass("text-success").html("");
          btn.prop("disabled", false);
        }, 3000);
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
    
    $(this).siblings(".file-input-label").html(`<i class="fas fa-file-archive"></i> ${fileName}`);
    $("#drone-upload-button").toggle(this.files.length > 0);
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

    statusDiv.removeClass("text-success text-danger").html("");
    progressDiv.show();
    btn.prop("disabled", true);

    // Создаём FormData
    const formData = new FormData();
    formData.append("drone_images", $("#drone-input")[0].files[0]);
    formData.append("data", JSON.stringify({
      field_id: fieldId || null,
      crop_type: cropType
    }));

    $.ajax({
      url: "/api/drone/upload",
      type: "POST",
      data: formData,
      processData: false,
      contentType: false,
      success: (res) => {
        statusDiv.html("<i class=\"fas fa-check\"></i> Архив принят. Обработка...");
        
        if (res.task_id) {
          pollDroneTaskStatus(res.task_id, res.field_id);
        }
        
        form.reset();
        $(form).find(".file-input-label").html('<i class="fas fa-file-upload"></i> Выберите ZIP или снимки');
        btn.hide();
      },
      error: (xhr) => {
        const err = xhr.responseJSON?.error || "Ошибка загрузки";
        statusDiv.addClass("text-danger").html(`<i class="fas fa-exclamation-triangle"></i> ${err}`);
        progressDiv.hide();
        btn.prop("disabled", false);
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
 * Опрашивает статус задачи обработки ортомозаики.
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
    $.ajax({
      url: `/api/drone/orthomosaic/status/${taskId}`,
      method: "GET",
      success: (res) => {
        if (res.status === "completed") {
          clearInterval(interval);
          progressDiv.hide();
          statusDiv.removeClass("text-danger").addClass("text-success")
            .html("<i class=\"fas fa-check\"></i> Обработка завершена!");
          
          setTimeout(() => {
            statusDiv.hide();
            if (fieldId) {
              window.location.hash = `#field/${fieldId}`;
              window.showFieldDetail?.(fieldId);
            }
            window.loadMapData?.();
          }, 2000);
          
        } else if (res.status === "error") {
          clearInterval(interval);
          progressDiv.hide();
          statusDiv.removeClass("text-success").addClass("text-danger")
            .html(`<i class="fas fa-exclamation-triangle"></i> Ошибка: ${res.error}`);
          $("#drone-upload-button").prop("disabled", false);
          showMessage(res.error, "error");
          
        } else if (res.status === "processing") {
          // Обновляем прогресс
          progress = Math.min(progress + 10, 90);
          progressFill.css("width", `${progress}%`);
          progressText.text(res.progress || "Обработка снимков...");
        }
      },
      error: () => {
        // Игнорируем ошибки сети
      }
    });
  }, 3000);
}
