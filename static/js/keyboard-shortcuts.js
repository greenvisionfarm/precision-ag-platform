/**
 * Модуль горячих клавиш для карты
 * Реализует быстрые действия на карте через клавиатуру, 
 * UI-подсказки и пользовательскую настройку.
 */

const MapKeyboardShortcuts = (() => {
    // Хранилище по умолчанию
    const DEFAULT_SHORTCUTS = {
        'ZoomIn': { key: '+', label: 'Приблизить' },
        'ZoomOut': { key: '-', label: 'Отдалить' },
        'FitBounds': { key: 'f', label: 'Показать все поля' },
        'ToggleLayers': { key: 'l', label: 'Переключить слои' },
        'ToggleLabels': { key: 'k', label: 'Переключить подписи' },
        'Fullscreen': { key: 'F11', label: 'Полный экран' },
        'ShowShortcuts': { key: '?', label: 'Показать горячие клавиши' },
        'PanUp': { key: 'ArrowUp', label: 'Вверх' },
        'PanDown': { key: 'ArrowDown', label: 'Вниз' },
        'PanLeft': { key: 'ArrowLeft', label: 'Влево' },
        'PanRight': { key: 'ArrowRight', label: 'Вправо' },
    };

    let shortcuts = {};
    let map = null;
    let hintPanel = null;
    let isHintVisible = false;

    /**
     * Инициализация модуля
     * @param {L.Map} leafletMap - Экземпляр Leaflet карты
     */
    function init(leafletMap) {
        map = leafletMap;
        loadUserShortcuts();
        setupHintPanel();
        bindGlobalEvents();
        console.log('[KeyboardShortcuts] Инициализирован');
    }

    /**
     * Загрузка пользовательских настроек из localStorage
     */
    function loadUserShortcuts() {
        try {
            const stored = localStorage.getItem('fm_map_shortcuts');
            if (stored) {
                const parsed = JSON.parse(stored);
                // Мержим с дефолтными, чтобы новые экшены не терялись
                shortcuts = { ...DEFAULT_SHORTCUTS, ...parsed };
            } else {
                shortcuts = { ...DEFAULT_SHORTCUTS };
            }
        } catch (e) {
            console.error('[KeyboardShortcuts] Ошибка загрузки настроек:', e);
            shortcuts = { ...DEFAULT_SHORTCUTS };
        }
    }

    /**
     * Сохранение настроек пользователя
     */
    function saveUserShortcuts() {
        try {
            localStorage.setItem('fm_map_shortcuts', JSON.stringify(shortcuts));
        } catch (e) {
            console.error('[KeyboardShortcuts] Ошибка сохранения:', e);
        }
    }

    /**
     * Создание UI панели с подсказками
     */
    function setupHintPanel() {
        if (!map) return;
        
        // Контейнер кнопки подсказок
        const btnContainer = L.DomUtil.create('div', 'leaflet-bar leaflet-control');
        const toggleBtn = L.DomUtil.create('a', 'leaflet-control-shortcuts-toggle', btnContainer);
        toggleBtn.href = '#';
        toggleBtn.title = 'Горячие клавиши (?)';
        toggleBtn.innerHTML = '⌨️';
        toggleBtn.setAttribute('role', 'button');
        toggleBtn.setAttribute('aria-label', 'Показать горячие клавиши');

        L.DomEvent.on(toggleBtn, 'click', L.DomEvent.stop);
        L.DomEvent.on(toggleBtn, 'click', toggleHintPanel);

        // Панель подсказок
        hintPanel = L.DomUtil.create('div', 'map-keyboard-hint', document.body);
        hintPanel.style.display = 'none';
        
        // Добавляем контрол на карту
        const ControlClass = L.Control.extend({
            onAdd: () => btnContainer
        });
        map.addControl(new ControlClass({ position: 'topright' }));
    }

    /**
     * Переключение видимости панели подсказок
     */
    function toggleHintPanel() {
        if (!hintPanel) return;
        
        if (isHintVisible) {
            hintPanel.style.display = 'none';
            isHintVisible = false;
        } else {
            renderHintContent();
            hintPanel.style.display = 'block';
            isHintVisible = true;
        }
    }

    /**
     * Рендер содержимого панели подсказок
     */
    function renderHintContent() {
        let html = `
            <div class="hint-header">
                <h3>⌨️ Горячие клавиши</h3>
                <button class="close-hint" aria-label="Закрыть">&times;</button>
            </div>
            <div class="hint-list">
                ${Object.entries(shortcuts).map(([action, data]) => `
                    <div class="hint-row" data-action="${action}">
                        <span class="key-badge">${escapeHtml(data.key)}</span>
                        <span class="label">${escapeHtml(data.label)}</span>
                        <button class="edit-key" title="Изменить" aria-label="Изменить сочетание">✏️</button>
                    </div>
                `).join('')}
            </div>
            <div class="hint-footer">
                <p>Нажмите на ✏️, чтобы переназначить клавишу</p>
                <button class="reset-defaults">Сбросить по умолчанию</button>
            </div>
        `;
        hintPanel.innerHTML = html;
        bindHintEvents();
    }

    /**
     * Привязка событий к элементам подсказок
     */
    function bindHintEvents() {
        if (!hintPanel) return;

        // Закрытие
        const closeBtn = hintPanel.querySelector('.close-hint');
        if (closeBtn) {
            L.DomEvent.on(closeBtn, 'click', (e) => {
                L.DomEvent.stop(e);
                toggleHintPanel();
            });
        }

        // Редактирование
        const editBtns = hintPanel.querySelectorAll('.edit-key');
        editBtns.forEach(btn => {
            L.DomEvent.on(btn, 'click', (e) => {
                L.DomEvent.stop(e);
                const row = btn.closest('.hint-row');
                const action = row.dataset.action;
                startRebinding(action, row);
            });
        });

        // Сброс
        const resetBtn = hintPanel.querySelector('.reset-defaults');
        if (resetBtn) {
            L.DomEvent.on(resetBtn, 'click', (e) => {
                L.DomEvent.stop(e);
                shortcuts = { ...DEFAULT_SHORTCUTS };
                localStorage.removeItem('fm_map_shortcuts');
                renderHintContent();
            });
        }
    }

    /**
     * Процесс переназначения клавиши
     * @param {string} action - Название действия
     * @param {HTMLElement} row - DOM-элемент строки
     */
    function startRebinding(action, row) {
        const keyBadge = row.querySelector('.key-badge');
        const originalText = keyBadge.textContent;
        
        keyBadge.textContent = '...';
        keyBadge.classList.add('recording');

        const handler = (e) => {
            e.preventDefault();
            e.stopPropagation();
            
            const newKey = e.key === ' ' ? 'Space' : e.key;
            
            // Проверяем конфликты
            const conflict = Object.entries(shortcuts).find(
                ([act, data]) => act !== action && data.key.toLowerCase() === newKey.toLowerCase()
            );
            
            if (conflict) {
                alert(`Клавиша "${newKey}" уже используется для: "${conflict[1].label}"`);
                keyBadge.textContent = originalText;
            } else {
                shortcuts[action].key = newKey;
                saveUserShortcuts();
                keyBadge.textContent = newKey;
            }
            
            keyBadge.classList.remove('recording');
            document.removeEventListener('keydown', handler);
        };

        document.addEventListener('keydown', handler, { once: true });
    }

    /**
     * Привязка глобальных событий клавиатуры
     */
    function bindGlobalEvents() {
        document.addEventListener('keydown', handleKeydown);
    }

    /**
     * Обработчик нажатий клавиш
     * @param {KeyboardEvent} e 
     */
    function handleKeydown(e) {
        // Игнорируем события в полях ввода
        if (e.target.tagName === 'INPUT' || 
            e.target.tagName === 'TEXTAREA' || 
            e.target.isContentEditable) {
            return;
        }

        const pressedKey = e.key;
        
        // Поиск действия по нажатой клавише
        const action = Object.entries(shortcuts).find(
            ([_, data]) => data.key.toLowerCase() === pressedKey.toLowerCase()
        );

        if (!action) return;

        const [actionName] = action;
        e.preventDefault();

        switch (actionName) {
            case 'ZoomIn':
                map.zoomIn();
                break;
            case 'ZoomOut':
                map.zoomOut();
                break;
            case 'FitBounds':
                window.dispatchEvent(new CustomEvent('map:fit-bounds'));
                break;
            case 'ToggleLayers':
                window.dispatchEvent(new CustomEvent('map:toggle-layers'));
                break;
            case 'ToggleLabels':
                window.dispatchEvent(new CustomEvent('map:toggle-labels'));
                break;
            case 'Fullscreen':
                toggleFullscreen();
                break;
            case 'ShowShortcuts':
                toggleHintPanel();
                break;
            case 'PanUp':
            case 'PanDown':
            case 'PanLeft':
            case 'PanRight':
                panMap(actionName);
                break;
            default:
                // Пробрасываем кастомное событие для других действий
                window.dispatchEvent(new CustomEvent(`shortcut:${actionName.toLowerCase()}`));
        }
    }

    /**
     * Панорамирование карты
     * @param {string} direction - Направление
     */
    function panMap(direction) {
        const panAmount = 100; // пикселей
        let delta = [0, 0];
        
        switch (direction) {
            case 'PanUp': delta = [0, -panAmount]; break;
            case 'PanDown': delta = [0, panAmount]; break;
            case 'PanLeft': delta = [-panAmount, 0]; break;
            case 'PanRight': delta = [panAmount, 0]; break;
        }
        
        if (map && delta.some(d => d !== 0)) {
            map.panBy(delta, { animate: true, duration: 0.3 });
        }
    }

    /**
     * Переключение полноэкранного режима
     */
    function toggleFullscreen() {
        if (!document.fullscreenElement) {
            document.documentElement.requestFullscreen().catch(err => {
                console.warn(`Fullscreen error: ${err.message}`);
            });
        } else {
            document.exitFullscreen();
        }
    }

    /**
     * Утилиты
     */
    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    /**
     * Публичное API
     */
    return {
        init,
        getShortcuts: () => ({ ...shortcuts }),
        setShortcuts: (newShortcuts) => {
            shortcuts = { ...DEFAULT_SHORTCUTS, ...newShortcuts };
            saveUserShortcuts();
        },
        resetToDefaults: () => {
            shortcuts = { ...DEFAULT_SHORTCUTS };
            localStorage.removeItem('fm_map_shortcuts');
        }
    };
})();

// Экспорт для использования в других модулях
if (typeof module !== 'undefined' && module.exports) {
    module.exports = MapKeyboardShortcuts;
}