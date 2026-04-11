/**
 * Callback'и для взаимодействия с картой.
 */
import { showMessage } from './utils.js';
import API from './api.js';

/**
 * Загружает данные полей на карту.
 */
export function loadMapData() {
  API.getFields().then(data => {
    // При клике на поле сразу переходим на страницу поля
    const onFieldClick = (fieldId) => {
      window.location.hash = `#field/${fieldId}`;
    };
    window.MapManager.renderFields(data, window.downloadKmzWithSettings, onFieldClick);
  }).catch(err => {
    console.error('[map-callbacks] loadMapData ошибка:', err);
  });
}

/**
 * Обработчик создания нового поля.
 * @param {Object} e - Событие Leaflet.
 */
export function onFieldCreated(e) {
  Swal.fire({ 
    title: "Название поля", 
    input: "text", 
    inputValue: "Новое поле", 
    showCancelButton: true 
  }).then(res => {
    if (res.isConfirmed && res.value) {
      API.addField(e.layer.toGeoJSON().geometry, res.value).then(() => {
        loadMapData();
        window.getFieldsTable?.()?.ajax.reload();
        showMessage("Поле создано", "success");
      });
    }
  });
}

/**
 * Обработчик редактирования поля.
 * @param {Object} e - Событие Leaflet.
 */
export function onFieldEdited(e) {
  e.layers.eachLayer(layer => {
    const id = layer.feature?.properties?.db_id;
    if (id) {
      API.updateField(id, "update_geometry", { 
        geometry: layer.toGeoJSON().geometry 
      }).then(() => {
        loadMapData();
        window.getFieldsTable?.()?.ajax.reload();
        showMessage("Геометрия обновлена", "success");
      });
    }
  });
}

/**
 * Обработчик удаления поля.
 * @param {Object} e - Событие Leaflet.
 */
export function onFieldDeleted(e) {
  e.layers.eachLayer(layer => {
    const id = layer.feature?.properties?.db_id;
    if (id) {
      API.deleteField(id).then(() => { 
        loadMapData(); 
        window.getFieldsTable?.()?.ajax.reload();
        showMessage("Поле удалено", "success");
      });
    }
  });
}
