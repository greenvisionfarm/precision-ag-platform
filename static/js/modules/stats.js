/**
 * View: Статистика — графики и KPI.
 */
import { View } from "./view.js";
import API from "./api.js";

export class StatsView extends View {
  constructor() {
    super("view-stats", { navHref: "#stats" });
    this.charts = {};
  }

  mount() {
    this._load();
  }

  update() {
    this._load();
  }

  unmount() {
    // Уничтожаем графики
    Object.values(this.charts).forEach(c => c?.destroy());
    this.charts = {};
    super.unmount();
  }

  async _load() {
    try {
      const res = await API.getFieldsData();
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

      document.getElementById("stat-total-fields").textContent = data.length;
      document.getElementById("stat-total-area").textContent = total.toFixed(2) + " га";

      this._renderPieChart("chart-land-status", sMap);
      this._renderPieChart("chart-owners", oMap);
    } catch (e) {
      console.error("[StatsView] load error:", e);
    }
  }

  _renderPieChart(id, dataMap) {
    const ctx = document.getElementById(id);
    if (!ctx) return;

    if (this.charts[id]) {
      this.charts[id].destroy();
    }

    this.charts[id] = new Chart(ctx.getContext("2d"), {
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
              color: getComputedStyle(document.documentElement)
                .getPropertyValue("--text-color").trim()
            }
          }
        }
      }
    });
  }

  updateChartsTheme() {
    Object.values(this.charts).forEach(chart => {
      if (!chart) return;
      chart.options.plugins.legend.labels.color = getComputedStyle(document.documentElement)
        .getPropertyValue("--text-color").trim();
      chart.update();
    });
  }
}

/**
 * Обновляет тему графиков (обратная совместимость).
 * Вызывается из theme.js.
 */
let _statsViewRef = null;

export function setStatsViewRef(view) {
  _statsViewRef = view;
}

export function updateChartsTheme() {
  _statsViewRef?.updateChartsTheme();
}
