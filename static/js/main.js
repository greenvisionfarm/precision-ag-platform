/**
 * Field Mapper App — главная точка входа.
 * Инкапсулирует состояние приложения в классе.
 */
import { showMessage } from './modules/utils.js';
import { handleRoute } from './modules/router.js';
import { initFieldsTable, initOwnersTable, getFieldsTable } from './modules/tables.js';
import { openFieldModal, downloadKmzWithSettings } from './modules/modals.js';
import { showFieldDetail } from './modules/field-detail.js';
import { initShapefileUpload, initRasterUpload, initDroneUpload } from './modules/uploads.js';
import { initUploadManager } from './modules/upload-manager.js';
import { initStatsView } from './modules/stats.js';
import { initTheme } from './modules/theme.js';
import { loadMapData, onFieldCreated, onFieldEdited, onFieldDeleted } from './modules/map-callbacks.js';

// Глобальная настройка jQuery для отправки cookie (авторизация)
$.ajaxSetup({
    xhrFields: { withCredentials: true }
});

/**
 * Auth gate: показывает форму входа если пользователь не авторизован.
 * @returns {Promise<boolean>} true если авторизован.
 */
async function checkAuthGate() {
    const gate = document.getElementById('auth-gate');
    if (!gate) return true;

    try {
        const resp = await fetch('/api/auth/profile', { credentials: 'include' });
        if (resp.ok) {
            gate.style.display = 'none';
            return true;
        }
    } catch (_) {}

    // Показываем gate, скрываем интерфейс
    gate.style.display = 'flex';
    document.getElementById('sidebar-toggle').style.display = 'none';
    document.getElementById('sidebar').style.display = 'none';

    const form = document.getElementById('auth-gate-form');
    const alertEl = document.getElementById('auth-gate-alert');

    form.onsubmit = async (e) => {
        e.preventDefault();
        alertEl.style.display = 'none';
        const email = document.getElementById('auth-gate-email').value;
        const password = document.getElementById('auth-gate-password').value;

        try {
            const resp = await fetch('/api/auth/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify({ email, password })
            });
            const data = await resp.json();
            if (resp.ok) {
                gate.style.display = 'none';
                window.location.reload();
            } else {
                alertEl.textContent = data.message || data.error || 'Ошибка входа';
                alertEl.style.display = 'block';
            }
        } catch (err) {
            alertEl.textContent = 'Ошибка сети';
            alertEl.style.display = 'block';
        }
    };

    document.getElementById('auth-gate-register-link')?.addEventListener('click', (e) => {
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
        this.mapInitialized = false;
        this.currentView = 'map';
    }

    /**
     * Инициализирует приложение.
     * Порядок вызовов критичен: exportGlobalMethods() ДО onHashChange().
     */
    async init() {
        // 0. Auth gate — блокируем пока не войдёт
        const authenticated = await checkAuthGate();
        if (!authenticated) {
            return;
        }

        // 1. Тема
        initTheme();

        // 2. Карта
        window.MapManager.initMainMap('map', onFieldCreated, onFieldEdited, onFieldDeleted);
        this.mapInitialized = true;

        // 3. Загрузка данных карты (только если авторизован)
        if (window.AuthModule?.isLoggedIn()) {
            loadMapData();
        }

        // 4. Экспортируем методы ДО обработки маршрутов
        //    Это нужно потому что router.js и tables.js используют window.* для обратных вызовов
        this.exportGlobalMethods();

        // 5. Обработка начального маршрута
        $(window).on('hashchange', this.onHashChange.bind(this));
        this.onHashChange();

        // 6. Sidebar toggle
        $('#sidebar-toggle').on('click', this.toggleSidebar.bind(this));
        $('.main-content').on('click', this.closeSidebar.bind(this));
        $('#sidebar .nav-link').on('click', this.closeSidebar.bind(this));

        // 7. Менеджер загрузок
        initUploadManager();

        // 8. Инициализация загрузок
        initShapefileUpload();
        initRasterUpload();
        initDroneUpload();
    }

    /**
     * Обработчик изменения hash в URL.
     */
    onHashChange() {
        handleRoute();
        this.closeSidebar();
    }

    /**
     * Переключает sidebar.
     * @param {boolean} [forceOpen] - Принудительно открыть (true) или закрыть (false).
     */
    toggleSidebar(forceOpen) {
        const isOpen = $('body').hasClass('sidebar-open');
        const shouldOpen = forceOpen !== undefined ? forceOpen : !isOpen;

        $('body').toggleClass('sidebar-open', shouldOpen);
        $('#sidebar').toggleClass('open', shouldOpen);
        $('#sidebar-toggle').toggleClass('open', shouldOpen);

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
     * Экспортирует методы для глобального доступа (HTML onclick, modals и т.д.).
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
        window.app = this;
    }

    /**
     * Возвращает текущее представление.
     * @returns {string}
     */
    getCurrentView() {
        return this.currentView;
    }

    /**
     * Проверяет инициализирована ли карта.
     * @returns {boolean}
     */
    isMapInitialized() {
        return this.mapInitialized;
    }
}

// Создаём экземпляр приложения
const app = new FieldMapperApp();

// Инициализация при готовности DOM
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => app.init());
} else {
    app.init();
}

// Экспорт для тестов
export { FieldMapperApp, app };
