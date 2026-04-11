/**
 * Маршрутизация и навигация по приложению.
 * Использует прямые импорты вместо window.* для надёжности.
 */
import { initFieldsTable } from './tables.js';
import { initOwnersTable } from './tables.js';
import { openFieldModal } from './modals.js';
import { showFieldDetail } from './field-detail.js';
import { initStatsView } from './stats.js';
import { loadMapData } from './map-callbacks.js';

/**
 * Обработчик изменения маршрута.
 * @param {string} [forcedHash] - Принудительный hash для навигации.
 */
export function handleRoute(forcedHash) {
    const hash = forcedHash || window.location.hash || '#map';
    document.body.setAttribute('data-route', hash);

    // Скрываем все секции и деактивируем навигацию
    $('.view-section').addClass('hidden');
    $('.nav-link').removeClass('active');

    if (hash === '#map') {
        $('#view-map').removeClass('hidden');
        $('.nav-link[href="#map"]').addClass('active');
        window.MapManager?.instance?.invalidateSize();
        // Загружаем данные полей на карту
        loadMapData();
    } else if (hash === '#fields') {
        $('#view-fields').removeClass('hidden');
        $('.nav-link[href="#fields"]').addClass('active');
        // Прямой вызов — не через window.*
        initFieldsTable();
    } else if (hash.startsWith('#field/')) {
        const fieldId = hash.split('/')[1];
        $('#view-field-detail').removeClass('hidden');
        $('.nav-link[href="#fields"]').addClass('active');
        showFieldDetail(fieldId);
    } else if (hash === '#owners') {
        $('#view-owners').removeClass('hidden');
        $('.nav-link[href="#owners"]').addClass('active');
        // Прямой вызов — не через window.*
        initOwnersTable();
    } else if (hash === '#stats') {
        $('#view-stats').removeClass('hidden');
        $('.nav-link[href="#stats"]').addClass('active');
        // Прямой вызов — не через window.*
        initStatsView();
    } else if (hash === '#uploads') {
        $('#view-uploads').removeClass('hidden');
        $('.nav-link[href="#uploads"]').addClass('active');
    }
}
