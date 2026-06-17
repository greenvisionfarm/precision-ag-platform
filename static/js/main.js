/**
 * Field Mapper App — главная точка входа.
 * Использует Router с lifecycle view.
 */
import { showMessage } from "./modules/utils.js";
import { Router } from "./modules/router.js";
import { openFieldModal, downloadKmzWithSettings } from "./modules/modals.js";
import { initUploadManager } from "./modules/upload-manager.js";
import { initTheme } from "./modules/theme.js";
import { onFieldCreated, onFieldEdited, onFieldDeleted } from "./modules/map-callbacks.js";
import { getFieldsTable } from "./modules/tables.js";

// View classes
import { MapView } from "./modules/views/map-view.js";
import { FieldsView } from "./modules/views/fields-view.js";
import { FieldDetailView } from "./modules/views/field-detail-view.js";
import { OwnersView } from "./modules/views/owners-view.js";
import { StatsView, setStatsViewRef } from "./modules/stats.js";
import { UploadsView } from "./modules/views/uploads-view.js";

// Глобальная настройка jQuery для отправки cookie (авторизация)
$.ajaxSetup({
  xhrFields: { withCredentials: true }
});

/**
 * Auth gate: показывает форму входа если пользователь не авторизован.
 * @returns {Promise<boolean>} true если авторизован.
 */
async function checkAuthGate() {
  const gate = document.getElementById("auth-gate");
  if (!gate) return true;

  try {
    const resp = await fetch("/api/auth/profile", { credentials: "include" });
    if (resp.ok) {
      gate.style.display = "none";
      return true;
    }
  } catch (_) { /* network error — treat as not authenticated */ }

  gate.style.display = "flex";
  document.getElementById("sidebar-toggle").style.display = "none";
  document.getElementById("sidebar").style.display = "none";

  const form = document.getElementById("auth-gate-form");
  const alertEl = document.getElementById("auth-gate-alert");

  form.onsubmit = async (e) => {
    e.preventDefault();
    alertEl.style.display = "none";
    const email = document.getElementById("auth-gate-email").value;
    const password = document.getElementById("auth-gate-password").value;

    try {
      const resp = await fetch("/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ email, password })
      });
      const data = await resp.json();
      if (resp.ok) {
        gate.style.display = "none";
        window.location.reload();
      } else {
        alertEl.textContent = data.message || data.error || "Ошибка входа";
        alertEl.style.display = "block";
      }
    } catch (err) {
      alertEl.textContent = "Ошибка сети";
      alertEl.style.display = "block";
    }
  };

  document.getElementById("auth-gate-register-link")?.addEventListener("click", (e) => {
    e.preventDefault();
    window.AuthModule?.openLogin?.();
  });

  return false;
}

/**
 * Главный класс приложения Field Mapper.
 */
class FieldMapperApp {
  constructor() {
    this.router = new Router();
    this.mapInitialized = false;

    // Создаём view-экземпляры
    this.mapView = new MapView();
    this.fieldsView = new FieldsView();
    this.fieldDetailView = new FieldDetailView();
    this.ownersView = new OwnersView();
    this.statsView = new StatsView();
    this.uploadsView = new UploadsView();
  }

  async init() {
    const authenticated = await checkAuthGate();
    if (!authenticated) return;

    initTheme();

    // Карта
    window.MapManager.initMainMap("map", onFieldCreated, onFieldEdited, onFieldDeleted);
    this.mapInitialized = true;

    // Регистрируем view в роутере
    this.router.register("#map", this.mapView);
    this.router.register("#fields", this.fieldsView);
    this.router.register("#field/:id", this.fieldDetailView);
    this.router.register("#owners", this.ownersView);
    this.router.register("#stats", this.statsView);
    this.router.register("#uploads", this.uploadsView);

    // Sidebar
    $("#sidebar-toggle").on("click", this.toggleSidebar.bind(this));
    $(".main-content").on("click", this.closeSidebar.bind(this));
    $("#sidebar .nav-link").on("click", this.closeSidebar.bind(this));

    // Менеджер загрузок
    initUploadManager();

    // Связываем StatsView с theme.js
    setStatsViewRef(this.statsView);

    // Маршрутизация
    $(window).on("hashchange", () => this.onHashChange());
    this.onHashChange();

    // Глобальные методы (пока нужны для inline onclick в HTML)
    this._exposeGlobals();
  }

  onHashChange() {
    this.router.handleRoute();
    this.closeSidebar();
  }

  toggleSidebar(forceOpen) {
    const isOpen = $("body").hasClass("sidebar-open");
    const shouldOpen = forceOpen !== undefined ? forceOpen : !isOpen;

    $("body").toggleClass("sidebar-open", shouldOpen);
    $("#sidebar").toggleClass("open", shouldOpen);
    $("#sidebar-toggle").toggleClass("open", shouldOpen);

    setTimeout(() => {
      if (window.MapManager.instance) {
        window.MapManager.instance.invalidateSize();
      }
    }, 300);
  }

  closeSidebar() {
    this.toggleSidebar(false);
  }

  /**
     * Глобальные методы — временны, пока не уберём все inline onclick.
     * @private
     */
  _exposeGlobals() {
    window.showMessage = showMessage;
    window.openFieldModal = openFieldModal;
    window.downloadKmzWithSettings = downloadKmzWithSettings;
    window.loadMapData = () => this.mapView._loadData();
    window.getFieldsTable = getFieldsTable;
    window.showFieldDetail = (id) => this.router.handleRoute(`#field/${id}`);
    window.loadFieldScans = null;
    window.app = this;
  }
}

const app = new FieldMapperApp();

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", () => app.init());
} else {
  app.init();
}

export { FieldMapperApp, app };
