/**
 * View: Помощь — внутренняя вики.
 */
import { View } from "../view.js";
import { HELP_ARTICLES, HELP_CATEGORIES } from "../help-content.js";

export class HelpView extends View {
  constructor() {
    super("view-help", { navHref: "#help" });
    this.activeArticle = null;
  }

  mount() {
    this._render();
  }

  update() {
    this._render();
  }

  unmount() {
    super.unmount();
  }

  _render() {
    const container = this.el;
    if (!container) return;

    const params = new URLSearchParams(window.location.hash.split("?")[1]);
    const articleId = params.get("article") || "getting-started";

    container.innerHTML = `
      <div class="help-layout">
        <aside class="help-sidebar">
          <h2><i class="fas fa-book-open"></i> Справка</h2>
          <input type="text" class="help-search" placeholder="Поиск..." id="help-search">
          <nav class="help-nav" id="help-nav">
            ${this._renderNav(articleId)}
          </nav>
        </aside>
        <main class="help-content" id="help-content">
          ${this._renderArticle(articleId)}
        </main>
      </div>
    `;

    this._bindEvents();
  }

  _renderNav(activeId) {
    let html = "";
    HELP_CATEGORIES.forEach(cat => {
      const articles = HELP_ARTICLES.filter(a => a.category === cat.name);
      if (articles.length === 0) return;
      html += `<div class="help-nav-category">${cat.icon} ${cat.name}</div>`;
      articles.forEach(a => {
        const active = a.id === activeId ? " active" : "";
        html += `<a class="help-nav-item${active}" data-article="${a.id}" href="#help?article=${a.id}">${a.icon} ${a.title}</a>`;
      });
    });
    return html;
  }

  _renderArticle(id) {
    const article = HELP_ARTICLES.find(a => a.id === id);
    if (!article) return "<p>Статья не найдена.</p>";

    let html = "<div class=\"help-article\">";
    html += `<h1>${article.icon} ${article.title}</h1>`;
    article.sections.forEach(s => {
      html += "<div class=\"help-section\">";
      html += `<h2>${s.heading}</h2>`;
      html += `<div class="help-body">${s.body}</div>`;
      html += "</div>";
    });
    html += "</div>";
    return html;
  }

  _bindEvents() {
    const search = document.getElementById("help-search");
    const nav = document.getElementById("help-nav");

    if (search) {
      search.addEventListener("input", () => {
        const q = search.value.toLowerCase();
        nav.querySelectorAll(".help-nav-item").forEach(item => {
          const text = item.textContent.toLowerCase();
          item.style.display = text.includes(q) ? "" : "none";
        });
        nav.querySelectorAll(".help-nav-category").forEach(cat => {
          const next = [];
          let el = cat.nextElementSibling;
          while (el && !el.classList.contains("help-nav-category")) {
            if (el.classList.contains("help-nav-item")) next.push(el);
            el = el.nextElementSibling;
          }
          const hasVisible = next.some(n => n.style.display !== "none");
          cat.style.display = hasVisible ? "" : "none";
        });
      });
    }

    if (nav) {
      nav.addEventListener("click", (e) => {
        const item = e.target.closest(".help-nav-item");
        if (!item) return;
        e.preventDefault();
        const id = item.dataset.article;
        window.location.hash = `#help?article=${id}`;
      });
    }
  }
}
