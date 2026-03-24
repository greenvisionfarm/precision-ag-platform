/**
 * Управление темой оформления (светлая/тёмная).
 */
import { updateChartsTheme } from './stats.js';

/**
 * Инициализирует переключатель темы.
 */
export function initTheme() {
  const saved = localStorage.getItem("theme") || "light";
  $("html").attr("data-theme", saved);
  
  $("#theme-toggle-btn").on("click", () => {
    const curr = $("html").attr("data-theme");
    const next = curr === "dark" ? "light" : "dark";
    $("html").attr("data-theme", next);
    localStorage.setItem("theme", next);
    
    // Обновляем тему карты
    window.MapManager?.updateTheme(next === "dark");
    
    // Обновляем графики если они есть
    if (window.location.hash === "#stats") {
      updateChartsTheme();
    }
  });
}
