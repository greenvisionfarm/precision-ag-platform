/**
 * API client — централизованный доступ к бэкенду.
 * Использует jQuery $.ajax для обратной совместимости.
 */

function handleApiError(xhr, status, error) {
  if (xhr.status === 401) {
    if (window.AuthModule) window.AuthModule.openLogin();
    return Promise.reject({ xhr, status, error });
  }

  const errorMsg = xhr.responseJSON?.error || error || "Неизвестная ошибка";
  console.error(`API Error: ${xhr.status} ${status}`, errorMsg);

  if (typeof window.showMessage !== "undefined") {
    window.showMessage(`Ошибка: ${errorMsg}`, "error");
  } else {
    alert(`Ошибка: ${errorMsg}`);
  }

  return Promise.reject({ xhr, status, error });
}

class APIClient {
  // --- Fields ---
  getFields() { return $.getJSON("/api/fields").catch(handleApiError); }
  getFieldsData() { return $.getJSON("/api/fields_data").catch(handleApiError); }
  getField(id) { return $.getJSON(`/api/field/${id}`).catch(handleApiError); }

  addField(geometry, name) {
    return $.ajax({
      url: "/api/field/add", type: "POST", contentType: "application/json",
      data: JSON.stringify({ geometry, name })
    }).catch(handleApiError);
  }

  deleteField(id) {
    return $.ajax({ url: `/api/field/delete/${id}`, type: "DELETE" }).catch(handleApiError);
  }

  updateField(id, action, data) {
    return $.ajax({
      url: `/api/field/${action}/${id}`, type: "PUT", contentType: "application/json",
      data: JSON.stringify(data)
    }).catch(handleApiError);
  }

  // --- Owners ---
  getOwners() { return $.getJSON("/api/owners").catch(handleApiError); }

  addOwner(name) {
    return $.ajax({
      url: "/api/owner/add", type: "POST", contentType: "application/json",
      data: JSON.stringify({ name })
    }).catch(handleApiError);
  }

  deleteOwner(id) {
    return $.ajax({ url: `/api/owner/delete/${id}`, type: "DELETE" }).catch(handleApiError);
  }

  // --- Uploads ---
  uploadFile(formData) {
    return $.ajax({
      url: "/upload", type: "POST", data: formData,
      processData: false, contentType: false
    }).catch(handleApiError);
  }

  // --- Tasks ---
  getTaskStatus(taskId) {
    return $.getJSON(`/api/task/${taskId}`).catch(handleApiError);
  }

  // --- Scans ---
  getFieldScans(fieldId) {
    return $.getJSON(`/api/field/${fieldId}/scans`).catch(handleApiError);
  }

  compareScans(fieldId, scan1Id, scan2Id) {
    return $.getJSON(`/api/field/${fieldId}/compare?scan1=${scan1Id}&scan2=${scan2Id}`).catch(handleApiError);
  }

  deleteScan(fieldId, scanId) {
    return $.ajax({ url: `/api/field/${fieldId}/scans/${scanId}`, type: "DELETE" }).catch(handleApiError);
  }

  getScanZones(scanId) {
    return $.getJSON(`/api/scan/${scanId}/zones`).catch(handleApiError);
  }

  updateScanCrop(scanId, cropType) {
    return $.ajax({
      url: `/api/scan/${scanId}/update_crop`, type: "POST",
      contentType: "application/json", data: JSON.stringify({ crop_type: cropType })
    }).catch(handleApiError);
  }

  // --- Crops ---
  getCrops() { return $.getJSON("/api/crops").catch(handleApiError); }

  // --- Export ---
  exportKmz(fieldId, params = {}) {
    return $.ajax({
      url: `/api/field/export/kmz/${fieldId}`, type: "GET", data: params,
      xhrFields: { responseType: "blob" }
    }).catch(handleApiError);
  }

  exportAllKmz(params = {}) {
    return $.ajax({
      url: "/api/field/export/kmz/all", type: "GET", data: params,
      xhrFields: { responseType: "blob" }
    }).catch(handleApiError);
  }

  exportIsoxml(fieldId, params = {}) {
    return $.ajax({
      url: `/api/field/export/isoxml/${fieldId}`, type: "POST",
      contentType: "application/json", data: JSON.stringify(params),
      dataType: "binary", xhrFields: { responseType: "blob" }
    }).catch(handleApiError);
  }

  exportTaskData(fieldId, params = {}) {
    return $.ajax({
      url: `/api/field/export/taskdata/${fieldId}`, type: "POST",
      contentType: "application/json", data: JSON.stringify(params),
      xhrFields: { responseType: "blob" }
    }).catch(handleApiError);
  }
}

const API = new APIClient();

export { handleApiError };
export default API;
window.API = API;
window.handleApiError = handleApiError;
