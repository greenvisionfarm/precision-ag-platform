/**
 * Базовый класс для всех view приложения.
 * Предоставляет жизненный цикл: mount → update → unmount.
 */
export class View {
  /**
     * @param {string} id - Идентификатор view (совпадает с data-view в HTML).
     * @param {object} [opts]
     * @param {string} [opts.navHref] - href навигационной ссылки для подсветки.
     * @param {string} [opts.display] - CSS display при показе (по умолчанию 'flex').
     */
  constructor(id, { navHref, display = "flex" } = {}) {
    this.id = id;
    this.navHref = navHref;
    this.display = display;
    this.el = document.getElementById(id);
    this._mounted = false;
    this._cleanups = [];
  }

  /**
     * Показывает view, скрывает все остальные.
     * Вызывает mount() если ещё не был смонтирован,
     * иначе update() для обновления данных.
     * @param {object} params - Параметры маршрута.
     */
  show(params = {}) {
    this._hideAll();
    this._setActiveNav();

    if (this.el) {
      this.el.classList.remove("hidden");
      this.el.style.display = this.display;
    }

    if (!this._mounted) {
      this.mount(params);
      this._mounted = true;
    } else {
      this.update(params);
    }
  }

  /**
     * Скрывает view и вызывает unmount().
     */
  hide() {
    if (this.el) {
      this.el.classList.add("hidden");
    }
    if (this._mounted) {
      this.unmount();
      this._mounted = false;
    }
  }

  /**
     * Инициализация view при первом показе.
     * Переопределяется в наследниках.
     * @param {object} params - Параметры маршрута.
     */
  mount(params) {}

  /**
     * Обновление view при повторном показе.
     * Переопределяется в наследниках.
     * @param {object} params - Параметры маршрута.
     */
  update(params) {}

  /**
     * Очистка при скрытии view: интервалы, слушатели, чарты.
     * Переопределяется в наследниках.
     */
  unmount() {
    this._runCleanups();
  }

  /**
     * Регистрация callback-а очистки, который вызовется при unmount.
     * @param {Function} fn
     */
  onCleanup(fn) {
    this._cleanups.push(fn);
  }

  /**
     * Регистрация setInterval с автоматической очисткой.
     * @param {Function} fn
     * @param {number} ms
     * @returns {number} interval id
     */
  setInterval(fn, ms) {
    const id = window.setInterval(fn, ms);
    this.onCleanup(() => window.clearInterval(id));
    return id;
  }

  /**
     * Регистрация setTimeout с автоматической очисткой.
     * @param {Function} fn
     * @param {number} ms
     * @returns {number} timeout id
     */
  setTimeout(fn, ms) {
    const id = window.setTimeout(fn, ms);
    this.onCleanup(() => window.clearTimeout(id));
    return id;
  }

  /**
     * Привязка DOM-события с автоматической очисткой при unmount.
     * @param {Element|jQuery} el
     * @param {string} event
     * @param {Function} handler
     * @param {object} [opts] - options для addEventListener или delegation selector
     */
  listen(el, event, handler, opts) {
    const $el = el instanceof jQuery ? el[0] : el;
    if (!$el) return;

    if (opts && opts.delegate) {
      // jQuery delegation
      const $wrapper = $(el);
      $wrapper.on(event, opts.delegate, handler);
      this.onCleanup(() => $wrapper.off(event, opts.delegate, handler));
    } else {
      $el.addEventListener(event, handler);
      this.onCleanup(() => $el.removeEventListener(event, handler));
    }
  }

  /**
     * Универсальный $.on с автоочисткой.
     * @param {jQuery} $el
     * @param {string} event
     * @param {string|Function} selectorOrHandler
     * @param {Function} [handler]
     */
  bindEvent($el, event, selectorOrHandler, handler) {
    if (typeof selectorOrHandler === "function") {
      $el.on(event, selectorOrHandler);
      this.onCleanup(() => $el.off(event, selectorOrHandler));
    } else {
      $el.on(event, selectorOrHandler, handler);
      this.onCleanup(() => $el.off(event, selectorOrHandler, handler));
    }
  }

  // --- Internal ---

  _hideAll() {
    document.querySelectorAll(".view-section").forEach(el => {
      el.classList.add("hidden");
    });
  }

  _setActiveNav() {
    document.querySelectorAll(".nav-link").forEach(el => {
      el.classList.remove("active");
    });
    if (this.navHref) {
      const link = document.querySelector(`.nav-link[href="${this.navHref}"]`);
      if (link) link.classList.add("active");
    }
  }

  _runCleanups() {
    while (this._cleanups.length) {
      const fn = this._cleanups.pop();
      try { fn(); } catch (e) { console.error("Cleanup error:", e); }
    }
  }
}
