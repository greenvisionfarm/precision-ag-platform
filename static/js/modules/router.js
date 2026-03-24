/**
 * Маршрутизация и навигация по приложению.
 */
import { openFieldModal } from './modals.js';
import { showFieldDetail } from './field-detail.js';

/**
 * Обработчик изменения маршрута.
 */
export function handleRoute() {
  const hash = window.location.hash || "#map";
  $(".view-section").hide();
  $(".nav-link").removeClass("active");

  if (hash === "#map") {
    $("#view-map").show();
    $(".nav-link[href=\"#map\"]").addClass("active");
    window.MapManager?.instance?.invalidateSize();
  } else if (hash === "#fields") {
    $("#view-fields").show();
    $(".nav-link[href=\"#fields\"]").addClass("active");
    // Инициализация таблицы полей будет вызвана из main.js
    window.initFieldsTable?.();
  } else if (hash.startsWith("#field/")) {
    const fieldId = hash.split("/")[1];
    $("#view-field-detail").show();
    $(".nav-link[href=\"#fields\"]").addClass("active");
    showFieldDetail(fieldId);
  } else if (hash === "#owners") {
    $("#view-owners").show();
    $(".nav-link[href=\"#owners\"]").addClass("active");
    // Инициализация таблицы владельцев будет вызвана из main.js
    window.initOwnersTable?.();
  } else if (hash === "#stats") {
    $("#view-stats").show();
    $(".nav-link[href=\"#stats\"]").addClass("active");
    // Инициализация статистики будет вызвана из main.js
    window.initStatsView?.();
  }
}
