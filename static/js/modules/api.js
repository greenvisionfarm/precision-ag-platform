/**
 * Обработчик ошибок API.
 * @param {jqXHR} xhr - Объект XMLHttpRequest.
 * @param {string} status - Статус ошибки.
 * @param {string} error - Текст ошибки.
 */
export function handleApiError(xhr, status, error) {
  const errorMsg = xhr.responseJSON?.error || error || 'Неизвестная ошибка';
  console.error(`API Error: ${xhr.status} ${status}`, errorMsg);

  // Показываем уведомление пользователю
  if (typeof window.showMessage !== 'undefined') {
    window.showMessage(`Ошибка: ${errorMsg}`, 'error');
  } else {
    // Fallback: используем alert если showMessage недоступна
    alert(`Ошибка: ${errorMsg}`);
  }

  return Promise.reject({ xhr, status, error });
}

const API = {
  getFields: () => $.getJSON("/api/fields").catch(handleApiError),
  getFieldsData: () => $.getJSON("/api/fields_data").catch(handleApiError),
  getField: (id) => $.getJSON(`/api/field/${id}`).catch(handleApiError),
  getOwners: () => $.getJSON("/api/owners").catch(handleApiError),

  addOwner: (name) => $.ajax({
    url: "/api/owner/add", type: "POST", contentType: "application/json",
    data: JSON.stringify({ name: name })
  }).catch(handleApiError),

  deleteOwner: (id) => $.ajax({ 
    url: `/api/owner/delete/${id}`, type: "DELETE" 
  }).catch(handleApiError),

  addField: (geometry, name) => $.ajax({
    url: "/api/field/add", type: "POST", contentType: "application/json",
    data: JSON.stringify({ geometry: geometry, name: name })
  }).catch(handleApiError),

  deleteField: (id) => $.ajax({ 
    url: `/api/field/delete/${id}`, type: "DELETE" 
  }).catch(handleApiError),

  updateField: (id, action, data) => $.ajax({
    url: `/api/field/${action}/${id}`, type: "PUT", contentType: "application/json",
    data: JSON.stringify(data)
  }).catch(handleApiError),
  
  /**
   * Загрузка файла (GeoTIFF или Shapefile).
   * @param {FormData} formData - Данные формы с файлом.
   * @returns {Promise} Promise с результатом загрузки.
   */
  uploadFile: (formData) => $.ajax({
    url: "/upload",
    type: "POST",
    data: formData,
    processData: false,
    contentType: false
  }).catch(handleApiError),
  
  /**
   * Получение статуса фоновой задачи.
   * @param {string} taskId - ID задачи.
   * @returns {Promise} Promise со статусом задачи.
   */
  getTaskStatus: (taskId) => $.getJSON(`/api/task/${taskId}`).catch(handleApiError),
  
  /**
   * Экспорт поля в KMZ.
   * @param {number} fieldId - ID поля.
   * @param {Object} params - Параметры экспорта (height, overlap_h, overlap_w, direction).
   * @returns {Promise} Promise с данными KMZ.
   */
  exportKmz: (fieldId, params = {}) => $.ajax({
    url: `/api/field/export/kmz/${fieldId}`,
    type: "GET",
    data: params,
    xhrFields: { responseType: 'arraybuffer' }
  }).catch(handleApiError),
  
  /**
   * Массовый экспорт всех полей в KMZ (ZIP).
   * @param {Object} params - Параметры экспорта.
   * @returns {Promise} Promise с ZIP-архивом.
   */
  exportAllKmz: (params = {}) => $.ajax({
    url: "/api/field/export/kmz/all",
    type: "GET",
    data: params,
    xhrFields: { responseType: 'arraybuffer' }
  }).catch(handleApiError),

  /**
   * Получение списка сканов поля.
   * @param {number} fieldId - ID поля.
   * @returns {Promise} Promise со списком сканов.
   */
  getFieldScans: (fieldId) => $.getJSON(`/api/field/${fieldId}/scans`).catch(handleApiError),

  /**
   * Получение зон скана.
   * @param {number} scanId - ID скана.
   * @returns {Promise} Promise с зонами.
   */
  getScanZones: (scanId) => $.getJSON(`/api/scan/${scanId}/zones`).catch(handleApiError),
};

export default API;
window.API = API;
window.handleApiError = handleApiError;
