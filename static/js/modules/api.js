/**
 * API client — централизованный доступ к бэкенду.
 * Использует fetch с единым обработчиком ошибок.
 */

function handleApiError(status, message) {
  if (status === 401) {
    if (window.AuthModule) window.AuthModule.openLogin();
    return Promise.reject({ status, message });
  }

  console.error(`API Error: ${status}`, message);

  if (typeof window.showMessage !== "undefined") {
    window.showMessage(`Ошибка: ${message}`, "error");
  } else {
    alert(`Ошибка: ${message}`);
  }

  return Promise.reject({ status, message });
}

async function fetchApi(url, options = {}) {
  const defaults = {
    credentials: "include",
    headers: {},
  };

  if (options.body && typeof options.body === "object" && !(options.body instanceof FormData)) {
    defaults.headers["Content-Type"] = "application/json";
    options.body = JSON.stringify(options.body);
  }

  const config = { ...defaults, ...options, headers: { ...defaults.headers, ...options.headers } };

  try {
    const resp = await fetch(url, config);

    if (!resp.ok) {
      let message = resp.statusText;
      try {
        const err = await resp.json();
        message = err.error || err.message || message;
      } catch {}
      return handleApiError(resp.status, message);
    }

    const ct = resp.headers.get("content-type") || "";
    if (ct.includes("application/json")) {
      return resp.json();
    }
    return resp;
  } catch (e) {
    return handleApiError(0, e.message || "Сетевая ошибка");
  }
}

class APIClient {
  getFields() { return fetchApi("/api/fields"); }
  getFieldsData() { return fetchApi("/api/fields_data"); }
  getField(id) { return fetchApi(`/api/field/${id}`); }

  addField(geometry, name) {
    return fetchApi("/api/field/add", { method: "POST", body: { geometry, name } });
  }

  deleteField(id) {
    return fetchApi(`/api/field/delete/${id}`, { method: "DELETE" });
  }

  updateField(id, action, data) {
    return fetchApi(`/api/field/${action}/${id}`, { method: "PUT", body: data });
  }

  getOwners() { return fetchApi("/api/owners"); }

  addOwner(name) {
    return fetchApi("/api/owner/add", { method: "POST", body: { name } });
  }

  deleteOwner(id) {
    return fetchApi(`/api/owner/delete/${id}`, { method: "DELETE" });
  }

  uploadFile(formData) {
    return fetchApi("/upload", { method: "POST", body: formData });
  }

  getTaskStatus(taskId) {
    return fetchApi(`/api/task/${taskId}`);
  }

  getFieldScans(fieldId) {
    return fetchApi(`/api/field/${fieldId}/scans`);
  }

  compareScans(fieldId, scan1Id, scan2Id) {
    return fetchApi(`/api/field/${fieldId}/compare?scan1=${scan1Id}&scan2=${scan2Id}`);
  }

  deleteScan(fieldId, scanId) {
    return fetchApi(`/api/field/${fieldId}/scans/${scanId}`, { method: "DELETE" });
  }

  getScanZones(scanId) {
    return fetchApi(`/api/scan/${scanId}/zones`);
  }

  updateScanCrop(scanId, cropType) {
    return fetchApi(`/api/scan/${scanId}/update_crop`, { method: "POST", body: { crop_type: cropType } });
  }

  getCrops() { return fetchApi("/api/crops"); }

  async exportKmz(fieldId, params = {}) {
    const qs = new URLSearchParams(params).toString();
    const url = `/api/field/export/kmz/${fieldId}${qs ? "?" + qs : ""}`;
    const resp = await fetchApi(url);
    return resp.blob ? resp.blob() : resp;
  }

  async exportAllKmz(params = {}) {
    const qs = new URLSearchParams(params).toString();
    const url = `/api/field/export/kmz/all${qs ? "?" + qs : ""}`;
    const resp = await fetchApi(url);
    return resp.blob ? resp.blob() : resp;
  }

  async exportIsoxml(fieldId, params = {}) {
    const resp = await fetchApi(`/api/field/export/isoxml/${fieldId}`, { method: "POST", body: params });
    return resp.blob ? resp.blob() : resp;
  }

  async exportTaskData(fieldId, params = {}) {
    const resp = await fetchApi(`/api/field/export/taskdata/${fieldId}`, { method: "POST", body: params });
    return resp.blob ? resp.blob() : resp;
  }
}

const API = new APIClient();

export { handleApiError, fetchApi };
export default API;
window.API = API;
window.handleApiError = handleApiError;
