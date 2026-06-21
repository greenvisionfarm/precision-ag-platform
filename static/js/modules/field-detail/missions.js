/**
 * Missions — управление миссиями дронов (план полёта).
 */
import API from "../api.js";
import { showMessage } from "../utils.js";

let _boundDelegation = false;
let _currentPathLayer = null;

export function loadMissions(fieldId, state) {
  API.getMissions(fieldId).then(data => {
    const missions = data.missions || [];
    renderMissionsList(missions, fieldId, state);
  }).catch(err => {
    console.error("Ошибка загрузки миссий:", err);
  });
}

function renderMissionsList(missions, fieldId, state) {
  const $list = $("#missions-list").empty();

  if (missions.length === 0) {
    $list.append("<div style=\"color:var(--text-muted);font-size:.9rem;padding:10px;\">Миссий пока нет. Создайте первую миссию для планирования полёта дрона.</div>");
    return;
  }

  missions.forEach(mission => {
    const direction = mission.direction !== null ? `${mission.direction}°` : "Авто";

    const $item = $(`
      <div class="scan-item" data-mission-id="${mission.id}">
        <div class="scan-info">
          <span class="scan-date">${mission.name || "Миссия #" + mission.id}</span>
          <span class="scan-zones">${mission.height}м · ${mission.overlap_w}%</span>
          <span class="scan-ndvi">${direction}</span>
        </div>
        <button class="btn-delete-mission" data-field-id="${fieldId}" data-mission-id="${mission.id}" title="Удалить миссию">
          <i class="fas fa-trash"></i>
        </button>
      </div>
    `);

    $list.append($item);
  });

  if (!_boundDelegation) {
    _boundDelegation = true;

    $(document).on("click", "#missions-list .scan-info", function() {
      const missionId = parseInt($(this).closest(".scan-item").data("mission-id"));
      if (missionId) loadMissionPath(fieldId, missionId);
    });

    $(document).on("click", "#missions-list .btn-delete-mission", function(e) {
      e.stopPropagation();
      const fId = parseInt($(this).data("field-id"));
      const mId = parseInt($(this).data("mission-id"));
      if (fId && mId) deleteMission(fId, mId, state);
    });
  }
}

function loadMissionPath(fieldId, missionId) {
  API.getMission(fieldId, missionId).then(data => {
    showMissionOnMap(data);
    renderMissionInfo(data);
  }).catch(err => {
    console.error("Ошибка загрузки миссии:", err);
    showMessage("Не удалось загрузить миссию", "error");
  });
}

function showMissionOnMap(mission) {
  if (!window.MapManager?.detailInstance) return;

  if (_currentPathLayer) {
    window.MapManager.detailInstance.removeLayer(_currentPathLayer);
    _currentPathLayer = null;
  }

  if (!mission.path || mission.path.length === 0) return;

  _currentPathLayer = L.layerGroup();

  const polyline = L.polyline(mission.path, {
    color: "#FF6B35",
    weight: 2,
    opacity: 0.8,
    dashArray: "5, 5"
  });
  _currentPathLayer.addLayer(polyline);

  if (mission.path.length > 0) {
    const startIcon = L.divIcon({
      className: "mission-marker",
      html: "<div style=\"width:10px;height:10px;background:#4CAF50;border-radius:50%;border:2px solid #fff;\"></div>",
      iconSize: [14, 14],
      iconAnchor: [7, 7]
    });
    const endIcon = L.divIcon({
      className: "mission-marker",
      html: "<div style=\"width:10px;height:10px;background:#F44336;border-radius:50%;border:2px solid #fff;\"></div>",
      iconSize: [14, 14],
      iconAnchor: [7, 7]
    });

    L.marker(mission.path[0], { icon: startIcon }).addTo(_currentPathLayer);
    L.marker(mission.path[mission.path.length - 1], { icon: endIcon }).addTo(_currentPathLayer);
  }

  _currentPathLayer.addTo(window.MapManager.detailInstance);

  const bounds = L.latLngBounds(mission.path);
  window.MapManager.detailInstance.fitBounds(bounds, { padding: [30, 30] });
}

function renderMissionInfo(mission) {
  const $info = $("#mission-info").empty();
  $info.show();

  const direction = mission.direction !== null ? `${mission.direction}°` : `${mission.optimal_direction}° (авто)`;

  $info.html(`
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;">
      <div>
        <div style="color:var(--text-muted);font-size:.85rem;">Высота</div>
        <div style="font-size:1.1em;font-weight:600;">${mission.height} м</div>
      </div>
      <div>
        <div style="color:var(--text-muted);font-size:.85rem;">Курс</div>
        <div style="font-size:1.1em;font-weight:600;">${direction}</div>
      </div>
      <div>
        <div style="color:var(--text-muted);font-size:.85rem;">Боковое перекрытие</div>
        <div style="font-size:1.1em;font-weight:600;">${mission.overlap_w}%</div>
      </div>
      <div>
        <div style="color:var(--text-muted);font-size:.85rem;">Точек</div>
        <div style="font-size:1.1em;font-weight:600;">${mission.waypoint_count}</div>
      </div>
    </div>
  `);
}

function deleteMission(fieldId, missionId, state) {
  Swal.fire({
    title: "Удалить миссию?",
    text: "Маршрут будет удалён навсегда",
    icon: "warning",
    showCancelButton: true,
    confirmButtonText: "Удалить",
    cancelButtonText: "Отмена"
  }).then(result => {
    if (result.isConfirmed) {
      API.deleteMission(fieldId, missionId).then(() => {
        showMessage("Миссия удалена", "success");
        if (_currentPathLayer && window.MapManager?.detailInstance) {
          window.MapManager.detailInstance.removeLayer(_currentPathLayer);
          _currentPathLayer = null;
        }
        $("#mission-info").hide();
        loadMissions(fieldId, state);
      }).catch(err => {
        console.error("Ошибка удаления миссии:", err);
        showMessage("Не удалось удалить миссию", "error");
      });
    }
  });
}

export function initMissionCreateHandler(getFieldId) {
  $(document).off("click", "#mission-create-btn").on("click", "#mission-create-btn", function() {
    const fieldId = getFieldId();
    if (!fieldId) return;

    Swal.fire({
      title: "Новая миссия",
      html: `
        <div style="text-align:left;">
          <label style="display:block;margin-bottom:4px;font-size:.9em;">Название</label>
          <input id="swal-mission-name" class="swal2-input" placeholder="Миссия 1" style="margin-bottom:12px;">
          <label style="display:block;margin-bottom:4px;font-size:.9em;">Высота (м)</label>
          <input id="swal-mission-height" class="swal2-input" type="number" value="100" min="10" max="500" style="margin-bottom:12px;">
          <label style="display:block;margin-bottom:4px;font-size:.9em;">Боковое перекрытие (%)</label>
          <input id="swal-mission-overlap" class="swal2-input" type="number" value="70" min="10" max="95" style="margin-bottom:12px;">
          <label style="display:block;margin-bottom:4px;font-size:.9em;">Курс (градусы, 0 = авто)</label>
          <input id="swal-mission-direction" class="swal2-input" type="number" value="0" min="0" max="359">
        </div>
      `,
      showCancelButton: true,
      confirmButtonText: "Создать",
      cancelButtonText: "Отмена",
      preConfirm: () => {
        const height = parseInt(document.getElementById("swal-mission-height").value);
        const overlap = parseInt(document.getElementById("swal-mission-overlap").value);
        const direction = parseInt(document.getElementById("swal-mission-direction").value);

        if (!height || height < 10 || height > 500) {
          Swal.showValidationMessage("Высота: 10-500 м");
          return false;
        }
        if (!overlap || overlap < 10 || overlap > 95) {
          Swal.showValidationMessage("Перекрытие: 10-95%");
          return false;
        }

        return {
          name: document.getElementById("swal-mission-name").value || null,
          height: height,
          overlap_h: overlap,
          overlap_w: overlap,
          direction: direction === 0 ? null : direction,
        };
      }
    }).then(result => {
      if (result.isConfirmed) {
        API.createMission(fieldId, result.value).then(data => {
          showMessage("Миссия создана", "success");
          loadMissions(fieldId, { currentFieldId: fieldId });
          if (data.id) {
            loadMissionPath(fieldId, data.id, { currentFieldId: fieldId });
          }
        }).catch(err => {
          console.error("Ошибка создания миссии:", err);
        });
      }
    });
  });
}

export function cleanup() {
  if (_currentPathLayer && window.MapManager?.detailInstance) {
    window.MapManager.detailInstance.removeLayer(_currentPathLayer);
    _currentPathLayer = null;
  }
}
