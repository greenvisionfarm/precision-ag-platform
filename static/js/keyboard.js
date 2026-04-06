/**
 * Модуль горячих клавиш для карты Field Mapper.
 * Реализует:
 * - Список настроенных клавиш
 * - UI подсказки (панель помощи и всплывающие уведомления)
 * - Пользовательскую настройку через localStorage
 */

class MapKeyboardShortcuts {
  constructor(mapElement) {
    this.map = mapElement;
    this.shortcuts = this.loadShortcuts();
    this.enabled = true;
    this.helpVisible = false;
    this.helpPanel = null;
    this.init();
  }

  loadShortcuts() {
    try {
      const saved = localStorage.getItem('fm_keyboard_shortcuts');
      return saved ? JSON.parse(saved) : this.getDefaultShortcuts();
    } catch {
      return this.getDefaultShortcuts();
    }
  }

  getDefaultShortcuts() {
    return {
      zoom_in: { key: '+', description: 'Приблизить' },
      zoom_out: { key: '-', description: 'Отдалить' },
      fit_bounds: { key: 'f', description: 'Вместить все объекты' },
      toggle_layers: { key: 'l', description: 'Слои' },
      toggle_help: { key: '?', description: 'Справка' },
      reset_settings: { key: 'r', description: 'Сбросить настройки' }
    };
  }

  saveShortcuts(newShortcuts) {
    localStorage.setItem('fm_keyboard_shortcuts', JSON.stringify(newShortcuts));
    this.shortcuts = newShortcuts;
  }

  init() {
    document.addEventListener('keydown', (e) => this.handleKey(e));
    this.createHelpPanel();
    console.log('⌨️ Горячие клавиши карты инициализированы');
  }

  handleKey(e) {
    if (!this.enabled) return;
    
    const tag = e.target.tagName.toLowerCase();
    if (tag === 'input' || tag === 'textarea' || tag === 'select' || e.target.isContentEditable) {
      return;
    }

    const key = e.key.toLowerCase();
    const match = Object.entries(this.shortcuts).find(([_, cfg]) => cfg.key.toLowerCase() === key);

    if (match) {
      e.preventDefault();
      const [action, cfg] = match;
      this.execute(action);
      // Не показываем тост для помощи, чтобы не мигать над панелью
      if (action !== 'toggle_help') {
        this.showToast(`Выполнено: ${cfg.description}`);
      }
    }
  }

  execute(action) {
    if (!this.map) return;
    
    switch(action) {
      case 'zoom_in':
        if (typeof this.map.zoomIn === 'function') this.map.zoomIn();
        else if (this.map.getView && this.map.getView().setZoom) {
          const view = this.map.getView();
          view.setZoom(view.getZoom() + 1);
        }
        break;
      case 'zoom_out':
        if (typeof this.map.zoomOut === 'function') this.map.zoomOut();
        else if (this.map.getView && this.map.getView().setZoom) {
          const view = this.map.getView();
          view.setZoom(view.getZoom() - 1);
        }
        break;
      case 'fit_bounds':
        if (typeof this.map.invalidateSize === 'function') this.map.invalidateSize();
        if (typeof this.map.setView === 'function') this.map.setView([0, 0], 2);
        break;
      case 'toggle_layers':
        this.togglePanel('.leaflet-control-layers, #layers-panel, .ol-layerswitcher');
        break;
      case 'toggle_help':
        this.toggleHelp();
        break;
      case 'reset_settings':
        this.saveShortcuts(this.getDefaultShortcuts());
        this.showToast('Настройки клавиш сброшены');
        break;
    }
  }

  togglePanel(selector) {
    const panels = document.querySelectorAll(selector);
    panels.forEach(p => {
      p.style.display = p.style.display === 'none' ? '' : 'none';
    });
  }

  createHelpPanel() {
    if (this.helpPanel) return;
    this.helpPanel = document.createElement('div');
    this.helpPanel.id = 'fm-hotkeys-help';
    this.helpPanel.style.cssText = `
      position: fixed; bottom: 80px; right: 20px; background: #fff; color: #333;
      padding: 12px; border-radius: 8px; box-shadow: 0 4px 15px rgba(0,0,0,0.2);
      z-index: 10000; font-family: system-ui, -apple-system, sans-serif;
      max-width: 280px; transition: all 0.2s ease;
    `;
    this.updateHelpContent();
    document.body.appendChild(this.helpPanel);
    this.helpVisible = false;
    this.helpPanel.style.display = 'none';
  }

  updateHelpContent() {
    let html = '<h4 style="margin:0 0 8px; font-size:14px;">⌨️ Горячие клавиши</h4><ul style="list-style:none; padding:0; margin:0; font-size:12px;">';
    Object.entries(this.shortcuts).forEach(([action, cfg]) => {
      const isEditable = ['zoom_in', 'zoom_out', 'fit_bounds', 'toggle_layers', 'toggle_help', 'reset_settings'].includes(action);
      html += `<li style="display:flex; justify-content:space-between; padding:4px 0; border-bottom:1px solid #eee;">
        <span>${cfg.description}</span>
        <kbd style="background:#f0f0f0; border:1px solid #ccc; border-radius:4px; padding:1px 5px; font-family:monospace;">${cfg.key}</kbd>
      </li>`;
    });
    html += '</ul><div style="margin-top:8px; font-size:11px; color:#666; text-align:right;">Нажмите <kbd>R</kbd> для сброса</div>';
    this.helpPanel.innerHTML = html;
  }

  toggleHelp() {
    if (!this.helpPanel) this.createHelpPanel();
    this.helpVisible = !this.helpVisible;
    this.helpPanel.style.display = this.helpVisible ? 'block' : 'none';
    this.helpPanel.style.opacity = this.helpVisible ? '1' : '0';
  }

  showToast(message) {
    const existing = document.querySelector('.fm-toast');
    if (existing) existing.remove();

    const toast = document.createElement('div');
    toast.className = 'fm-toast';
    toast.textContent = message;
    toast.style.cssText = `
      position: fixed; top: 20px; left: 50%; transform: translateX(-50%);
      background: rgba(0,0,0,0.85); color: #fff; padding: 10px 20px; border-radius: 20px;
      font-size: 13px; z-index: 11000; transition: opacity 0.3s; pointer-events: none;
    `;
    document.body.appendChild(toast);
    requestAnimationFrame(() => toast.style.opacity = '1');
    setTimeout(() => {
      toast.style.opacity = '0';
      setTimeout(() => toast.remove(), 300);
    }, 1500);
  }

  openSettings() {
    const input = prompt('Настройка горячих клавиш (JSON формат):', JSON.stringify(this.shortcuts, null, 2));
    if (input) {
      try {
        const parsed = JSON.parse(input);
        this.saveShortcuts(parsed);
        this.updateHelpContent();
        this.showToast('Настройки сохранены');
      } catch (e) {
        alert('Ошибка парсинга JSON. Используйте формат: { "action": { "key": "a", "description": "..." } }');
      }
    }
  }
}

// Авто-инициализация при появлении карты
if (typeof window !== 'undefined') {
  const initKeyboard = () => {
    const map = window.fmMap || window.map || window.leafletMap;
    if (map && !window._fmKeyboardManager) {
      window._fmKeyboardManager = new MapKeyboardShortcuts(map);
      window.fmKeyboardSettings = () => window._fmKeyboardManager.openSettings();
    } else if (!window._fmKeyboardManager) {
      setTimeout(initKeyboard, 500);
    }
  };
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initKeyboard);
  } else {
    initKeyboard();
  }
}