/**
 * Статистика и графики.
 */
import API from './api.js';

let charts = {};

/**
 * Инициализирует представление статистики.
 */
export function initStatsView() {
  API.getFieldsData().then(res => {
    const data = res.data;
    let total = 0; 
    const sMap = {}; 
    const oMap = {};
    
    data.forEach(f => {
      const a = (JSON.parse(f.properties || "{}").area_sq_m || 0) / 10000;
      total += a;
      sMap[f.land_status || "N/A"] = (sMap[f.land_status || "N/A"] || 0) + a;
      oMap[f.owner || "N/A"] = (oMap[f.owner || "N/A"] || 0) + a;
    });
    
    $("#stat-total-fields").text(data.length);
    $("#stat-total-area").text(total.toFixed(2) + " га");
    
    renderPieChart("chart-land-status", sMap);
    renderPieChart("chart-owners", oMap);
  });
}

/**
 * Рисует круговую диаграмму.
 * @param {string} id - ID canvas элемента.
 * @param {Object} dataMap - Объект с данными {label: value}.
 */
function renderPieChart(id, dataMap) {
  const ctx = document.getElementById(id).getContext("2d");
  
  if (charts[id]) {
    charts[id].destroy();
  }
  
  charts[id] = new Chart(ctx, {
    type: "pie", 
    data: { 
      labels: Object.keys(dataMap), 
      datasets: [{ 
        data: Object.values(dataMap), 
        backgroundColor: ["#007bff", "#28a745", "#ffc107", "#dc3545", "#6610f2"] 
      }] 
    },
    options: { 
      responsive: true, 
      maintainAspectRatio: false, 
      plugins: { 
        legend: { 
          position: "bottom", 
          labels: { 
            color: getComputedStyle(document.documentElement).getPropertyValue("--text-color").trim() 
          } 
        } 
      } 
    }
  });
}

/**
 * Обновляет цвет текста в легендах графиков при смене темы.
 */
export function updateChartsTheme() {
  Object.keys(charts).forEach(id => {
    if (charts[id]) {
      const chart = charts[id];
      chart.options.plugins.legend.labels.color = getComputedStyle(document.documentElement)
        .getPropertyValue("--text-color").trim();
      chart.update();
    }
  });
}
