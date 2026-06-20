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
import { HelpView } from "./modules/views/help-view.js";
import { initTooltips } from "./modules/tooltip.js";

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
  document.getElementById("app-header").style.display = "none";

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
    this.helpView = new HelpView();
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
    this.router.register("#help", this.helpView);

    // Header navigation
    this.initHeader();

    // Менеджер загрузок
    initUploadManager();

    // Связываем StatsView с theme.js
    setStatsViewRef(this.statsView);

    // Тултипы
    initTooltips();

    // Маршрутизация
    $(window).on("hashchange", () => this.onHashChange());
    this.onHashChange();

    // Глобальные методы (пока нужны для inline onclick в HTML)
    this._exposeGlobals();
  }

  onHashChange() {
    this.router.handleRoute();
  }

  initHeader() {
    // Header nav active state
    $(window).on("hashchange", () => this.updateHeaderNav());
    this.updateHeaderNav();

    // Header theme toggle
    $("#header-theme-toggle").on("click", () => {
      const current = document.documentElement.getAttribute("data-theme");
      const next = current === "dark" ? "light" : "dark";
      document.documentElement.setAttribute("data-theme", next);
      localStorage.setItem("theme", next);
      this.updateThemeIcon(next);
      if (window.MapManager.instance) window.MapManager.instance.updateTheme();
    });

    // User menu dropdown
    $(".header-user-btn").on("click", (e) => {
      e.stopPropagation();
      $(".header-user-dropdown").toggleClass("hidden");
    });
    $(document).on("click", () => $(".header-user-dropdown").addClass("hidden"));

    // Header user info
    this.updateHeaderUser();

    // Logout
    $("#header-logout").on("click", (e) => {
      e.preventDefault();
      if (window.AuthModule) AuthModule.logout();
    });
  }

  updateHeaderNav() {
    const hash = window.location.hash || "#map";
    $(".header-nav-link").each(function () {
      const navHash = $(this).attr("href");
      $(this).toggleClass("active", hash.startsWith(navHash));
    });
  }

  updateThemeIcon(theme) {
    const icon = $("#header-theme-toggle i");
    icon.removeClass("fa-moon fa-sun").addClass(theme === "dark" ? "fa-sun" : "fa-moon");
  }

  updateHeaderUser() {
    const user = window.AuthModule?.getCurrentUser?.();
    if (!user) return;
    const name = user.first_name || user.email?.split("@")[0] || "U";
    $(".header-avatar").text(name.charAt(0).toUpperCase());
    $(".header-username").text(name);
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
