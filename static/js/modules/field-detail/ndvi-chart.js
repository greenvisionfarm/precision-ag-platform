/**
 * NDVI Chart — график истории NDVI и сравнение сканов.
 */
import API from "./api.js";
import { showMessage } from "./utils.js";

let chartInstance = null;

export function initNDVIChart(scans) {
  const ctx = document.getElementById("ndvi-history-chart");
  if (!ctx) return;

  const existing = Chart.getChart(ctx);
  if (existing) existing.destroy();
  chartInstance = null;

  const chartData = scans
    .filter(s => s.processed && s.ndvi_avg)
    .sort((a, b) => new Date(a.uploaded_at) - new Date(b.uploaded_at));

  if (chartData.length === 0) return;

  const labels = chartData.map(s => new Date(s.uploaded_at).toLocaleDateString("ru-RU"));
  const values = chartData.map(s => s.ndvi_avg);

  chartInstance = new Chart(ctx, {
    type: "line",
    data: {
      labels,
      datasets: [{
        label: "Средний NDVI",
        data: values,
        borderColor: "#4CAF50",
        backgroundColor: "rgba(76, 175, 80, 0.1)",
        borderWidth: 2,
        fill: true,
        tension: 0.3
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: { y: { min: 0, max: 1, title: { display: true, text: "NDVI" } } },
      plugins: { legend: { display: false } }
    }
  });
}

export function destroyChart() {
  if (chartInstance) {
    chartInstance.destroy();
    chartInstance = null;
  }
}

export function compareSelectedScans(fieldId) {
  const checked = $(".scan-checkbox:checked");
  if (checked.length !== 2) {
    showMessage("Выберите ровно 2 скана для сравнения", "warning");
    return;
  }

  const scan1Id = parseInt(checked[0].value);
  const scan2Id = parseInt(checked[1].value);

  API.compareScans(fieldId, scan1Id, scan2Id).then(data => {
    const delta = data.delta_ndvi || 0;
    const deltaText = delta > 0 ? `+${delta.toFixed(3)}` : delta.toFixed(3);

    $("#compare-delta-value").text(deltaText);
    $("#compare-delta-value").css("color", delta > 0 ? "#4CAF50" : "#f44336");

    const trendIcon = delta > 0.05 ? "📈 Улучшение" : (delta < -0.05 ? "📉 Ухудшение" : "➡️ Стабильно");
    $("#compare-trend-icon").text(trendIcon);
    showMessage(`Сравнение завершено. Изменение NDVI: ${deltaText}`, "info");
  }).fail(err => {
    console.error("Ошибка сравнения:", err);
    showMessage("Не удалось выполнить сравнение", "error");
  });
}
