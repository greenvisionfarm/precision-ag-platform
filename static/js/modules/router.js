/**
 * Централизованный роутер с управлением жизненным циклом view.
 * Каждый view — экземпляр класса View с mount/update/unmount.
 */
export class Router {
  constructor() {
    this.views = new Map();
    this.currentView = null;
    this.currentParams = {};
  }

  /**
     * Регистрирует view для маршрута.
     * @param {string} pattern - Строка '#map', '#fields' или '#field/:id'.
     * @param {import('./view.js').View} view
     */
  register(pattern, view) {
    this.views.set(pattern, view);
  }

  /**
     * Обрабатывает изменение hash.
     * @param {string} [forcedHash]
     */
  handleRoute(forcedHash) {
    const hash = forcedHash || window.location.hash || "#map";
    document.body.setAttribute("data-route", hash);

    const { pattern, params } = this._match(hash);
    if (!pattern) return;

    // Если переключаемся на другой view — unmount текущего
    if (this.currentView && this.currentView !== this.views.get(pattern)) {
      this.currentView.hide();
    }

    const view = this.views.get(pattern);
    this.currentView = view;
    this.currentParams = params;
    view.show(params);
  }

  /**
     * Возвращает текущий view.
     */
  getCurrentView() {
    return this.currentView;
  }

  /**
     * Принудительно unmount текущего view.
     */
  unmountCurrent() {
    if (this.currentView) {
      this.currentView.hide();
      this.currentView = null;
    }
  }

  // --- Internal ---

  /**
     * Матчит hash на зарегистрированный pattern.
     * Поддерживает: '#map' (точное), '#field/:id' (параметры).
     */
  _match(hash) {
    // Точное совпадение
    if (this.views.has(hash)) {
      return { pattern: hash, params: {} };
    }

    // Параметризованные маршруты (например #field/:id)
    for (const [pattern] of this.views) {
      if (pattern.includes("/:")) {
        const prefix = pattern.split("/:")[0] + "/";
        if (hash.startsWith(prefix)) {
          const paramValue = hash.slice(prefix.length);
          const paramName = pattern.split("/:")[1];
          return { pattern, params: { [paramName]: paramValue } };
        }
      }
    }

    return { pattern: null, params: {} };
  }
}
