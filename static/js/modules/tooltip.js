/**
 * Tooltip — контекстные подсказки.
 * Использование: добавить элементу data-help="article_id"
 * или data-help-text="текст подсказки".
 */

let tooltipEl = null;
let activeTarget = null;

function ensureTooltip() {
  if (tooltipEl) return;
  tooltipEl = document.createElement("div");
  tooltipEl.className = "help-tooltip";
  tooltipEl.innerHTML = `
    <div class="help-tooltip-content" id="help-tooltip-content"></div>
    <a class="help-tooltip-link" href="#" id="help-tooltip-link">Подробнее →</a>
  `;
  document.body.appendChild(tooltipEl);
}

export function initTooltips() {
  ensureTooltip();

  document.addEventListener("mouseenter", (e) => {
    if (!e.target.closest) return;
    const target = e.target.closest("[data-help], [data-help-text]");
    if (!target) return;
    showTooltip(target);
  }, true);

  document.addEventListener("mouseleave", (e) => {
    if (!e.target.closest) return;
    const target = e.target.closest("[data-help], [data-help-text]");
    if (!target) return;
    hideTooltip();
  }, true);

  document.addEventListener("click", (e) => {
    if (!e.target.closest) return;
    if (e.target.closest(".help-tooltip")) return;
    hideTooltip();
  });
}

function showTooltip(target) {
  if (!tooltipEl) return;
  activeTarget = target;

  const articleId = target.dataset.help;
  const text = target.dataset.helpText;

  const content = document.getElementById("help-tooltip-content");
  const link = document.getElementById("help-tooltip-link");

  if (text) {
    content.innerHTML = text;
    link.style.display = "none";
  } else if (articleId) {
    content.innerHTML = `<strong>${articleId}</strong>`;
    link.href = `#help?article=${articleId}`;
    link.style.display = "";
  } else {
    return;
  }

  tooltipEl.classList.add("visible");

  const rect = target.getBoundingClientRect();
  let top = rect.bottom + 8;
  let left = rect.left;

  if (left + 280 > window.innerWidth) {
    left = window.innerWidth - 290;
  }
  if (top + 100 > window.innerHeight) {
    top = rect.top - 10;
    tooltipEl.classList.add("above");
  } else {
    tooltipEl.classList.remove("above");
  }

  tooltipEl.style.top = top + "px";
  tooltipEl.style.left = left + "px";
}

function hideTooltip() {
  if (tooltipEl) tooltipEl.classList.remove("visible");
  activeTarget = null;
}
