/**
 * Callback'и для взаимодействия с картой.
 */
import { showMessage } from './utils.js';
import API from './api.js';

/**
 * Загружает данные полей на карту.
 */
export function loadMapData() {
  console.log('[map-callbacks] loadMapData вызвана');
  // Отслеживаем вызовы через глобальный флаг для отладки
  window._loadMapDataCalls = (window._loadMapDataCalls || 0) + 1;
  const callNum = window._loadMapDataCalls;
  console.log(`[map-callbacks] Вызов #${callNum}`);

  const promise = API.getFields();
  console.log(`[map-callbacks] Вызов #${callNum}: API.getFields вернул promise`);

  promise.then(data => {
    console.log(`[map-callbacks] Вызов #${callNum}: .then — data.type=${data?.type}, features=${data?.features?.length}`);
    console.log(`[map-callbacks] Вызов #${callNum}: window.MapManager=${!!window.MapManager}, renderFields=${typeof window.MapManager?.renderFields}`);
    console.log(`[map-callbacks] Вызов #${callNum}: editableLayers=${!!window.MapManager?.editableLayers}`);
    try {
      window.MapManager.renderFields(data, window.downloadKmzWithSettings, window.openFieldModal);
      console.log(`[map-callbacks] Вызов #${callNum}: renderFields завершён, layers=${window.MapManager.editableLayers?.getLayers?.().length}`);
    } catch (e) {
      console.error(`[map-callbacks] Вызов #${callNum}: renderFields бросил ошибку:`, e);
    }
  }).catch(err => {
    console.error(`[map-callbacks] Вызов #${callNum}: loadMapData ошибка:`, err);
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
