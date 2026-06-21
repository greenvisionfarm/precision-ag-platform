"""
Health dashboard handler — визуальный дашборд для self-hosters.
"""
import time

import tornado.web

_start_time = time.time()


class HealthDashboardHandler(tornado.web.RequestHandler):
    """GET /health — HTML дашборд состояния системы."""

    def get(self) -> None:
        self.set_header("Content-Type", "text/html; charset=utf-8")
        self.write(_HEALTH_HTML)


_HEALTH_HTML = """<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Field Mapper — Health Dashboard</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
         background: #0f172a; color: #e2e8f0; padding: 2rem; }
  .container { max-width: 700px; margin: 0 auto; }
  h1 { font-size: 1.5rem; margin-bottom: 0.5rem; color: #f8fafc; }
  .subtitle { color: #94a3b8; font-size: 0.9rem; margin-bottom: 2rem; }
  .card { background: #1e293b; border-radius: 12px; padding: 1.25rem;
          margin-bottom: 1rem; border: 1px solid #334155; }
  .card-header { display: flex; justify-content: space-between;
                 align-items: center; margin-bottom: 0.75rem; }
  .card-title { font-weight: 600; font-size: 1rem; }
  .badge { padding: 0.2rem 0.6rem; border-radius: 20px; font-size: 0.75rem;
           font-weight: 600; text-transform: uppercase; }
  .badge-ok { background: #065f46; color: #6ee7b7; }
  .badge-err { background: #7f1d1d; color: #fca5a5; }
  .badge-warn { background: #78350f; color: #fcd34d; }
  .metric { display: flex; justify-content: space-between;
            padding: 0.4rem 0; border-bottom: 1px solid #334155; }
  .metric:last-child { border-bottom: none; }
  .metric-label { color: #94a3b8; }
  .metric-value { font-weight: 500; font-family: monospace; }
  .refresh-bar { text-align: center; color: #64748b; font-size: 0.8rem;
                 margin-top: 1.5rem; }
  .error-msg { color: #fca5a5; font-size: 0.85rem; margin-top: 0.5rem; }
  .spinner { display: inline-block; width: 14px; height: 14px;
             border: 2px solid #475569; border-top-color: #60a5fa;
             border-radius: 50%; animation: spin 0.8s linear infinite;
             vertical-align: middle; margin-right: 6px; }
  @keyframes spin { to { transform: rotate(360deg); } }
  #overall-status { font-size: 1.1rem; margin-bottom: 1.5rem; }
</style>
</head>
<body>
<div class="container">
  <h1>Field Mapper Health</h1>
  <p class="subtitle">Self-hosted instance monitoring</p>
  <div id="overall-status"><span class="spinner"></span> Loading...</div>
  <div id="cards"></div>
  <div id="audit-log-container"></div>
  <div class="refresh-bar" id="refresh-info">Auto-refresh in <span id="countdown">30</span>s</div>
</div>

<script>
const API = '/api/health';
const INTERVAL = 30;
let countdown = INTERVAL;

function badge(status) {
  if (status === 'ok') return '<span class="badge badge-ok">OK</span>';
  if (status === 'error') return '<span class="badge badge-err">ERROR</span>';
  return '<span class="badge badge-warn">' + status + '</span>';
}

function formatUptime(sec) {
  const h = Math.floor(sec / 3600);
  const m = Math.floor((sec % 3600) / 60);
  const s = Math.floor(sec % 60);
  if (h > 0) return h + 'h ' + m + 'm';
  if (m > 0) return m + 'm ' + s + 's';
  return s + 's';
}

function render(data) {
  const overall = document.getElementById('overall-status');
  if (data.status === 'healthy') {
    overall.innerHTML = '&#9989; System healthy';
    overall.style.color = '#6ee7b7';
  } else {
    overall.innerHTML = '&#10060; System degraded';
    overall.style.color = '#fca5a5';
  }

  let html = '';
  for (const [name, check] of Object.entries(data.checks)) {
    if (name === 'audit_log') continue;
    html += '<div class="card">';
    html += '<div class="card-header">';
    html += '<span class="card-title">' + name.toUpperCase() + '</span>';
    html += badge(check.status);
    html += '</div>';
    html += '<div class="metric"><span class="metric-label">Status</span>';
    html += '<span class="metric-value">' + check.status + '</span></div>';
    if (check.uptime_seconds !== undefined) {
      html += '<div class="metric"><span class="metric-label">Uptime</span>';
      html += '<span class="metric-value">' + formatUptime(check.uptime_seconds) + '</span></div>';
    }
    if (check.pid !== undefined) {
      html += '<div class="metric"><span class="metric-label">PID</span>';
      html += '<span class="metric-value">' + check.pid + '</span></div>';
    }
    if (check.message) {
      html += '<div class="metric"><span class="metric-label">Info</span>';
      html += '<span class="metric-value" style="color:#fcd34d">' + check.message + '</span></div>';
    }
    html += '</div>';
  }
  document.getElementById('cards').innerHTML = html;

  fetchAuditLogs();
}

async function fetchHealth() {
  try {
    const resp = await fetch(API);
    const data = await resp.json();
    render(data);
  } catch (e) {
    document.getElementById('overall-status').innerHTML =
      '<span style="color:#fca5a5">&#10060; Cannot reach server</span>';
    document.getElementById('cards').innerHTML =
      '<div class="error-msg">' + e.message + '</div>';
  }
}

setInterval(() => {
  countdown--;
  document.getElementById('countdown').textContent = countdown;
  if (countdown <= 0) {
    countdown = INTERVAL;
fetchHealth();

async function fetchAuditLogs() {
  try {
    const resp = await fetch('/api/audit-logs?limit=10');
    if (!resp.ok) return;
    const data = await resp.json();
    const logs = data.logs || [];
    if (logs.length === 0) {
      document.getElementById('audit-log-container').innerHTML =
        '<div class="card"><div class="card-title" style="margin-bottom:0.5rem;">Аудит-журнал</div><div style="color:#94a3b8;font-size:0.9rem;">Нет записей</div></div>';
      return;
    }

    let html = '<div class="card"><div class="card-header"><span class="card-title">Аудит-журнал</span>';
    html += '<span class="badge badge-ok">' + logs.length + ' записей</span></div>';
    html += '<div style="font-size:0.85rem;">';

    const actionLabels = {
      rename: 'Переименование',
      assign_owner: 'Назначение владельца',
      update_details: 'Обновление деталей',
      update_geometry: 'Обновление геометрии'
    };

    logs.forEach(log => {
      const time = log.created_at ? new Date(log.created_at).toLocaleString('ru-RU') : '';
      const action = actionLabels[log.action] || log.action;
      const details = log.details ? Object.entries(log.details).map(([k, v]) => k + '=' + v).join(', ') : '';

      html += '<div class="metric" style="flex-direction:column;align-items:flex-start;gap:2px;">';
      html += '<div style="display:flex;justify-content:space-between;width:100%;">';
      html += '<span style="color:#e2e8f0;font-weight:500;">' + action + ' ' + (log.entity_type || '') + (log.entity_name ? ' "' + log.entity_name + '"' : '') + '</span>';
      html += '<span style="color:#64748b;">' + time + '</span>';
      html += '</div>';
      if (details) html += '<div style="color:#94a3b8;font-size:0.8rem;">' + log.user_email + ': ' + details + '</div>';
      else html += '<div style="color:#94a3b8;font-size:0.8rem;">' + (log.user_email || '') + '</div>';
      html += '</div>';
    });

    html += '</div></div>';
    document.getElementById('audit-log-container').innerHTML = html;
  } catch (e) {
    // silent
  }
}
  }
}, 1000);

fetchHealth();
</script>
</body>
</html>"""
