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
    $("#upload-button").toggle(this.files.length > 0); 
  });
  
  $("#upload-form").on("submit", function(e) {
    e.preventDefault();
    const form = this;
    $("#upload-status").text("Загрузка...");
    
    $.ajax({ 
      url: "/upload", 
      type: "POST", 
      data: new FormData(this), 
      processData: false, 
      contentType: false,
      success: () => {
        $("#upload-status").text("Успех!");
        window.loadMapData?.();
        window.getFieldsTable?.()?.ajax.reload();
        form.reset();
        $("#upload-button").hide();
        setTimeout(() => $("#upload-status").text(""), 3000);
      },
      error: () => {
        $("#upload-status").text("Ошибка");
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
    $("#raster-upload-button").toggle(this.files.length > 0); 
  });
  
  $("#raster-upload-form").on("submit", function(e) {
    e.preventDefault();
    const form = this;
    const statusDiv = $("#raster-upload-status");
    const btn = $("#raster-upload-button");

    statusDiv.html("<i class=\"fas fa-spinner fa-spin\"></i> Загрузка файла...").show();
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
          statusDiv.html("<span class=\"text-success\">Готово!</span>");
          btn.prop("disabled", false);
          form.reset();
          if (res.field_id) {
            window.location.hash = `#field/${res.field_id}`;
          }
        }
      },
      error: (xhr) => {
        const err = xhr.responseJSON?.error || "Ошибка загрузки";
        statusDiv.html(`<span class="text-danger">${err}</span>`);
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
        statusDiv.html("<span class=\"text-success\"><i class=\"fas fa-check\"></i> Анализ завершен!</span>");
        setTimeout(() => {
          statusDiv.hide();
          $("#raster-upload-button").prop("disabled", false).hide();
          $("#raster-upload-form")[0].reset();
          if (window.location.hash === `#field/${fieldId}`) {
            window.showFieldDetail?.(fieldId);
          } else {
            window.location.hash = `#field/${fieldId}`;
          }
          window.loadMapData?.();
        }, 2000);
      } else if (res.status === "error") {
        clearInterval(interval);
        statusDiv.html(`<span class="text-danger"><i class="fas fa-exclamation-triangle"></i> Ошибка: ${res.message}</span>`);
        $("#raster-upload-button").prop("disabled", false);
        showMessage(res.message, "error");
      }
    }).catch(() => {
      // Игнорируем ошибки сети, продолжаем опрос
    });
  }, 3000);
}
