/**
 * Централизованный менеджер загрузок.
 * Отслеживает все активные загрузки, показывает индикатор в хедере.
 */

let nextId = 1;
const uploads = new Map();

/**
 * Регистрирует новую загрузку.
 * @param {object} opts - { type, filename, xhr?, taskId? }
 * @returns {number} id загрузки
 */
export function register({ type, filename, xhr = null, taskId = null }) {
  const id = nextId++;
  uploads.set(id, {
    id, type, filename, xhr, taskId,
    status: "uploading", // uploading | processing | completed | error | aborted
    progress: 0,
    message: "",
  });
  renderBadge();
  renderDropdown();
  return id;
}

/**
 * Обновляет прогресс загрузки.
 */
export function updateProgress(id, { progress, message, status } = {}) {
  const u = uploads.get(id);
  if (!u) return;
  if (progress !== undefined) u.progress = progress;
  if (message !== undefined) u.message = message;
  if (status !== undefined) u.status = status;
  renderBadge();
  renderDropdown();
}

/**
 * Помечает загрузку как завершённую (успешно или с ошибкой).
 */
export function complete(id, { status = "completed", message = "" } = {}) {
  const u = uploads.get(id);
  if (!u) return;
  u.status = status;
  u.message = message;
  u.progress = 100;
  renderBadge();
  renderDropdown();
  // Автоскрытие через 5 сек
  setTimeout(() => {
    uploads.delete(id);
    renderBadge();
    renderDropdown();
  }, 5000);
}

/**
 * Отменяет загрузку по id.
 */
export function abort(id) {
  const u = uploads.get(id);
  if (!u) return;
  u.status = "aborted";
  u.message = "Отменено";
  if (u.xhr && u.xhr.readyState !== 4) {
    u.xhr.abort();
  }
  renderBadge();
  renderDropdown();
  setTimeout(() => {
    uploads.delete(id);
    renderBadge();
    renderDropdown();
  }, 2000);
}

function getActive() {
  return [...uploads.values()].filter(u =>
    u.status === "uploading" || u.status === "processing"
  );
}

function getRecent() {
  return [...uploads.values()].filter(u =>
    u.status === "completed" || u.status === "error" || u.status === "aborted"
  );
}

const typeLabels = {
  drone: "Дрон",
  shapefile: "Shapefile",
  raster: "NDVI",
};

const statusIcons = {
  uploading: "<i class=\"fas fa-cloud-upload-alt fa-spin\"></i>",
  processing: "<i class=\"fas fa-cog fa-spin\"></i>",
  completed: "<i class=\"fas fa-check-circle\" style=\"color:var(--success-color)\"></i>",
  error: "<i class=\"fas fa-exclamation-circle\" style=\"color:var(--danger-color)\"></i>",
  aborted: "<i class=\"fas fa-ban\" style=\"color:var(--text-muted)\"></i>",
};

function renderBadge() {
  const badge = document.getElementById("upload-badge");
  const trigger = document.getElementById("upload-badge-trigger");
  if (!badge) return;
  const active = getActive();
  if (active.length === 0) {
    badge.classList.add("hidden");
    trigger?.classList.add("hidden");
    return;
  }
  trigger?.classList.remove("hidden");
  badge.classList.remove("hidden");
  badge.textContent = active.length;
}

function renderDropdown() {
  const panel = document.getElementById("upload-panel-list");
  if (!panel) return;
  const all = [...getActive(), ...getRecent()];
  if (all.length === 0) {
    panel.innerHTML = "<div class=\"upload-panel-empty\">Нет загрузок</div>";
    return;
  }
  panel.innerHTML = all.map(u => {
    const label = typeLabels[u.type] || u.type;
    const icon = statusIcons[u.status] || "";
    const showCancel = u.status === "uploading" || u.status === "processing";
    const showProgress = u.status === "uploading";
    return `
      <div class="upload-panel-item" data-id="${u.id}">
        <div class="upload-panel-item-header">
          <span class="upload-panel-item-icon">${icon}</span>
          <span class="upload-panel-item-label">${label}: ${u.filename}</span>
          ${showCancel ? `<button class="upload-panel-cancel" onclick="window.uploadManager.abort(${u.id})" title="Отменить"><i class="fas fa-times"></i></button>` : ""}
        </div>
        ${showProgress ? `
          <div class="upload-panel-progress">
            <div class="upload-panel-progress-bar">
              <div class="upload-panel-progress-fill" style="width:${u.progress}%"></div>
            </div>
            <span class="upload-panel-progress-text">${u.progress}%</span>
          </div>
        ` : ""}
        ${u.message ? `<div class="upload-panel-message">${u.message}</div>` : ""}
      </div>
    `;
  }).join("");
}

function togglePanel() {
  const panel = document.getElementById("upload-panel");
  if (!panel) return;
  panel.classList.toggle("hidden");
}

function initUploadManager() {
  const badge = document.getElementById("upload-badge");
  const trigger = document.getElementById("upload-badge-trigger");
  const panel = document.getElementById("upload-panel");
  if (!badge || !trigger || !panel) return;

  trigger.addEventListener("click", (e) => {
    e.stopPropagation();
    togglePanel();
  });

  document.addEventListener("click", (e) => {
    if (!panel.contains(e.target) && !trigger.contains(e.target)) {
      panel.classList.add("hidden");
    }
  });

  window.uploadManager = { register, updateProgress, complete, abort };
}

export { initUploadManager };
