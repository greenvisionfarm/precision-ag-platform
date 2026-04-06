/**
 * Field Mapper App - главная точка входа.
 * Инкапсулирует состояние приложения в классе.
 */

// Импорт модулей
import { showMessage } from './modules/utils.js';
import { handleRoute } from './modules/router.js';
import { initFieldsTable, initOwnersTable, getFieldsTable } from './modules/tables.js';
import { openFieldModal, downloadKmzWithSettings } from './modules/modals.js';
import { showFieldDetail } from './modules/field-detail.js';
import { initShapefileUpload, initRasterUpload, initDroneUpload } from './modules/uploads.js';
import { initStatsView } from './modules/stats.js';
import { initTheme } from './modules/theme.js';
import { loadMapData, onFieldCreated, onFieldEdited, onFieldDeleted } from './modules/map-callbacks.js';

/**
 * Главный класс приложения Field Mapper.
 * Инкапсулирует состояние и предоставляет методы для работы с приложением.
 */
class FieldMapperApp {
  constructor() {
    // Состояние приложения
    this.mapInitialized = false;
    this.currentView = 'map';
  }

  /**
   * Инициализирует приложение.
   */
  init() {
    // Инициализация темы
    initTheme();

    // Инициализация карты
    window.MapManager.initMainMap("map", onFieldCreated, onFieldEdited, onFieldDeleted);
    this.mapInitialized = true;

    // Загрузка данных карты
    loadMapData();

    // Обработка навигации
    $(window).on("hashchange", this.onHashChange.bind(this));
    this.onHashChange();

    // Sidebar toggle
    $("#sidebar-toggle").on("click", this.toggleSidebar.bind(this));
    
    // Закрытие sidebar кликом на контент
    $(".main-content").on("click", this.closeSidebar.bind(this));
    
    // Закрытие sidebar при выборе ссылки в меню
    $("#sidebar .nav-link").on("click", this.closeSidebar.bind(this));

    // Инициализация загрузки файлов
    initShapefileUpload();
    initRasterUpload();
    initDroneUpload();

    // Экспортируем методы для глобального доступа
    this.exportGlobalMethods();
  }

  /**
   * Обработчик изменения hash в URL.
   */
  onHashChange() {
    handleRoute();
    // Закрываем sidebar при смене маршрута
    this.closeSidebar();
  }

  /**
   * Переключает sidebar.
   * @param {boolean} forceOpen - Принудительно открыть (true) или закрыть (false).
   */
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

  /**
   * Закрывает sidebar.
   */
  closeSidebar() {
    this.toggleSidebar(false);
  }

  /**
   * Экспортирует методы для глобального доступа (для HTML onclick и т.д.).
   */
  exportGlobalMethods() {
    window.showMessage = showMessage;
    window.handleRoute = handleRoute;
    window.initFieldsTable = initFieldsTable;
    window.initOwnersTable = initOwnersTable;
    window.getFieldsTable = getFieldsTable;
    window.openFieldModal = openFieldModal;
    window.downloadKmzWithSettings = downloadKmzWithSettings;
    window.showFieldDetail = showFieldDetail;
    window.initStatsView = initStatsView;
    window.loadMapData = loadMapData;
    window.app = this; // Экспортируем экземпляр приложения
  }

  /**
   * Получает текущее представление.
   * @returns {string} Текущее представление.
   */
  getCurrentView() {
    return this.currentView;
  }

  /**
   * Проверяет, инициализирована ли карта.
   * @returns {boolean} true если карта инициализирована.
   */
  isMapInitialized() {
    return this.mapInitialized;
  }
}

// Создаем и экспортируем экземпляр приложения
const app = new FieldMapperApp();

$(document).ready(() => {
  app.init();
});

// Экспортируем для тестов
export { FieldMapperApp, app };
