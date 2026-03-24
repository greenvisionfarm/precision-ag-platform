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
 * Инициализирует форму загрузки растра (NDVI).
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

    statusDiv.removeClass("text-success text-danger").html("<i class=\"fas fa-spinner fa-spin\"></i> Загрузка файла...");
    btn.prop("disabled", true);

    $.ajax({
      url: "/upload",
      type: "POST",
      data: new FormData(form),
      processData: false,
      contentType: false,
      success: (res) => {
        if (res.task_id) {
          statusDiv.html("<i class=\"fas fa-cog fa-spin\"></i> Файл на сервере. Анализ NDVI...");
          pollTaskStatus(res.task_id, res.field_id);
        } else {
          statusDiv.addClass("text-success").html("<i class=\"fas fa-check\"></i> Готово!");
          btn.prop("disabled", false);
          form.reset();
          $(form).find(".file-input-label").html('<i class="fas fa-file-upload"></i> Выберите TIF файл');
          if (res.field_id) {
            window.location.hash = `#field/${res.field_id}`;
          }
        }
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
 * Опрашивает статус фоновой задачи.
 * @param {string} taskId - ID задачи.
 * @param {string|number} fieldId - ID поля.
 */
function pollTaskStatus(taskId, fieldId) {
  const statusDiv = $("#raster-upload-status");
  const interval = setInterval(() => {
    API.getTaskStatus(taskId).then(res => {
      if (res.status === "completed") {
        clearInterval(interval);
        statusDiv.removeClass("text-danger").addClass("text-success")
          .html("<i class=\"fas fa-check\"></i> Анализ завершен!");
        setTimeout(() => {
          statusDiv.removeClass("text-success").hide();
          $("#raster-upload-button").prop("disabled", false).hide();
          $("#raster-upload-form")[0].reset();
          $("#raster-upload-form").find(".file-input-label").html('<i class="fas fa-file-upload"></i> Выберите TIF файл');
          if (window.location.hash === `#field/${fieldId}`) {
            window.showFieldDetail?.(fieldId);
          } else {
            window.location.hash = `#field/${fieldId}`;
          }
          window.loadMapData?.();
        }, 2000);
      } else if (res.status === "error") {
        clearInterval(interval);
        statusDiv.removeClass("text-success").addClass("text-danger")
          .html(`<i class="fas fa-exclamation-triangle"></i> Ошибка: ${res.message}`);
        $("#raster-upload-button").prop("disabled", false);
        showMessage(res.message, "error");
      }
    }).catch(() => {
      // Игнорируем ошибки сети, продолжаем опрос
    });
  }, 3000);
}
