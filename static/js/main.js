// Глобальные переменные
let mapInstance = null;
let editableLayers = null;
let baseLayers = {};
let ownersList = [];
let fieldsTable = null;
let ownersTable = null;
let charts = {}; // Для хранения экземпляров графиков (чтобы удалять перед перерисовкой)

// --- 1. ROUTING & UI ---

function handleRoute() {
    const hash = window.location.hash || '#map';
    
    $('.view-section').hide();
    $('.nav-link').removeClass('active');

    if (hash === '#map') {
        $('#view-map').show();
        $('.nav-link[href="#map"]').addClass('active');
        if (mapInstance) mapInstance.invalidateSize();
    } else if (hash === '#fields') {
        $('#view-fields').show();
        $('.nav-link[href="#fields"]').addClass('active');
        initFieldsTable();
    } else if (hash === '#owners') {
        $('#view-owners').show();
        $('.nav-link[href="#owners"]').addClass('active');
        initOwnersTable();
    } else if (hash === '#stats') {
        $('#view-stats').show();
        $('.nav-link[href="#stats"]').addClass('active');
        initStatsView();
    }
}

// --- 2. MAP LOGIC ---

function initMap() {
    if ($('#map').length === 0 || mapInstance) return;
    mapInstance = L.map('map').setView([48.66, 19.69], 8);
    baseLayers.light = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { attribution: '&copy; OpenStreetMap' });
    baseLayers.dark = L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', { attribution: '&copy; CARTO', subdomains: 'abcd', maxZoom: 20 });
    const currentTheme = localStorage.getItem('theme') || 'light';
    (currentTheme === 'dark' ? baseLayers.dark : baseLayers.light).addTo(mapInstance);
    editableLayers = new L.FeatureGroup();
    mapInstance.addLayer(editableLayers);
    const drawControl = new L.Control.Draw({
        edit: { featureGroup: editableLayers },
        draw: { polygon: { allowIntersection: false, showArea: true, shapeOptions: { color: '#007BFF' } }, polyline: false, rectangle: false, circle: false, marker: false, circlemarker: false }
    });
    mapInstance.addControl(drawControl);
    mapInstance.on(L.Draw.Event.CREATED, onFieldCreated);
    mapInstance.on(L.Draw.Event.EDITED, onFieldEdited);
    mapInstance.on(L.Draw.Event.DELETED, onFieldDeleted);
    mapInstance.locate({setView: true, maxZoom: 16});
    mapInstance.on('locationfound', e => { L.marker(e.latlng).addTo(mapInstance).bindPopup("Вы здесь!"); });
    loadMapData();
}

function loadMapData() {
    if (editableLayers) editableLayers.clearLayers();
    $.getJSON('/api/fields', function(data) {
        if (data.features) {
            L.geoJSON(data, {
                style: { color: "#007BFF", weight: 2, fillOpacity: 0.3 },
                onEachFeature: (feature, layer) => {
                    const props = feature.properties || {};
                    const area = props.area_sq_m ? (props.area_sq_m / 10000).toFixed(2) + ' га' : 'N/A';
                    layer.bindPopup(`
                        <b>${props.name || 'Поле'}</b><br>
                        Площадь: ${area}<br>
                        <hr>
                        <button onclick="downloadKmzWithSettings(${props.db_id})" class="btn btn-primary btn-sm" style="width:100%">
                            <i class="fas fa-file-download"></i> Скачать KMZ (DJI)
                        </button>
                    `);
                    editableLayers.addLayer(layer);
                }
            });
            if (editableLayers.getBounds().isValid()) mapInstance.fitBounds(editableLayers.getBounds());
        }
    });
}

function onFieldCreated(e) {
    const layer = e.layer;
    const name = prompt("Название поля:", "Новое поле");
    if (!name) return;
    $.ajax({
        url: '/api/field/add', type: 'POST', contentType: 'application/json',
        data: JSON.stringify({ geometry: layer.toGeoJSON().geometry, name: name }),
        success: () => { loadMapData(); if (fieldsTable) fieldsTable.ajax.reload(); }
    });
}

function onFieldEdited(e) {
    e.layers.eachLayer(layer => {
        const id = layer.feature?.properties?.db_id;
        if (id) {
            $.ajax({
                url: `/api/field/update_geometry/${id}`, type: 'PUT', contentType: 'application/json',
                data: JSON.stringify({ geometry: layer.toGeoJSON().geometry }),
                success: () => { loadMapData(); if (fieldsTable) fieldsTable.ajax.reload(); }
            });
        }
    });
}

function onFieldDeleted(e) {
    e.layers.eachLayer(layer => {
        const id = layer.feature?.properties?.db_id;
        if (id) {
            $.ajax({
                url: `/api/field/delete/${id}`, type: 'DELETE',
                success: () => { loadMapData(); if (fieldsTable) fieldsTable.ajax.reload(); }
            });
        }
    });
}

// --- 3. TABLES LOGIC ---

function downloadKmzWithSettings(fieldId) {
    Swal.fire({
        title: 'Параметры полета (DJI)',
        html: `
            <div style="text-align: left;">
                <label>Высота полета (м):</label>
                <input type="number" id="swal-height" class="swal2-input" value="100" min="20" max="120">
                <label>Фронтальное перекрытие (%):</label>
                <input type="number" id="swal-overlap-h" class="swal2-input" value="80" min="20" max="95">
                <label>Боковое перекрытие (%):</label>
                <input type="number" id="swal-overlap-w" class="swal2-input" value="70" min="20" max="95">
            </div>
        `,
        focusConfirm: false,
        showCancelButton: true,
        confirmButtonText: '<i class="fas fa-file-download"></i> Скачать',
        cancelButtonText: 'Отмена',
        preConfirm: () => {
            return {
                height: document.getElementById('swal-height').value,
                overlap_h: document.getElementById('swal-overlap-h').value,
                overlap_w: document.getElementById('swal-overlap-w').value
            }
        }
    }).then((result) => {
        if (result.isConfirmed) {
            const p = result.value;
            const url = `/api/field/export/kmz/${fieldId}?height=${p.height}&overlap_h=${p.overlap_h}&overlap_w=${p.overlap_w}`;
            window.location.href = url;
        }
    });
}

function loadOwners() {
    return $.getJSON('/api/owners', function(response) { ownersList = response.data; });
}

function initFieldsTable() {
    loadOwners().then(() => {
        if (fieldsTable) { fieldsTable.ajax.reload(); return; }
        fieldsTable = $('#fields-table').DataTable({
            ajax: "/api/fields_data",
            columns: [
                { data: "id" },
                { data: "name", render: (data, type, row) => `<span class="editable-name" data-id="${row.id}">${data}</span>` },
                { data: "area" },
                { data: "owner_id", render: (data, type, row) => {
                    let opts = '<option value="">Не назначен</option>';
                    ownersList.forEach(o => { opts += `<option value="${o.id}" ${o.id == data ? 'selected' : ''}>${o.name}</option>`; });
                    return `<select class="owner-select" data-id="${row.id}">${opts}</select>`;
                }},
                { data: "land_status", render: (data, type, row) => {
                    const statuses = ["Собственность", "Аренда", "Субаренда"];
                    let opts = '<option value="">Не указан</option>';
                    statuses.forEach(s => { opts += `<option value="${s}" ${s === data ? 'selected' : ''}>${s}</option>`; });
                    return `<select class="status-select" data-id="${row.id}">${opts}</select>`;
                }},
                { data: "parcel_number", render: (data, type, row) => `<span class="editable-parcel" data-id="${row.id}">${data || 'N/A'}</span>` },
                { data: null, render: (data, type, row) => `
                    <div class="btn-group">
                        <button onclick="downloadKmzWithSettings(${row.id})" class="btn btn-outline-primary btn-sm" title="Настройки DJI KMZ"><i class="fas fa-cog"></i></button>
                        <button class="btn-save-details btn-success btn-sm" data-id="${row.id}" style="display:none;" title="Сохранить"><i class="fas fa-save"></i></button>
                        <button class="btn-delete btn-danger btn-sm" data-id="${row.id}" title="Удалить"><i class="fas fa-trash"></i></button>
                    </div>
                `}
            ],
            language: { url: "//cdn.datatables.net/plug-ins/1.11.5/i18n/ru.json" }
        });
        setupTableEvents();
    });
}

function setupTableEvents() {
    const tbody = $('#fields-table tbody');
    tbody.on('change', '.owner-select, .status-select', function() { $(this).closest('tr').find('.btn-save-details').show(); });
    tbody.on('click', '.btn-save-details', function() {
        const btn = $(this); const id = btn.data('id'); const row = btn.closest('tr');
        const payload = { owner_id: row.find('.owner-select').val(), land_status: row.find('.status-select').val(), parcel_number: row.find('.editable-parcel').text() };
        $.ajax({ url: `/api/field/assign_owner/${id}`, type: 'PUT', contentType: 'application/json', data: JSON.stringify({ owner_id: payload.owner_id }) });
        $.ajax({
            url: `/api/field/update_details/${id}`, type: 'PUT', contentType: 'application/json', data: JSON.stringify({ land_status: payload.land_status, parcel_number: payload.parcel_number }),
            success: () => { btn.hide(); }
        });
    });
    tbody.on('click', '.editable-name', function() {
        const span = $(this); if (span.find('input').length) return;
        const input = $('<input>').val(span.text()); span.html(input);
        input.focus().on('blur keypress', function(e) {
            if (e.type === 'keypress' && e.which !== 13) return;
            const newName = $(this).val();
            $.ajax({ url: `/api/field/rename/${span.data('id')}`, type: 'PUT', contentType: 'application/json', data: JSON.stringify({ new_name: newName }), success: () => { span.text(newName); fieldsTable.ajax.reload(null, false); } });
        });
    });
    tbody.on('click', '.btn-delete', function() {
        if (confirm('Удалить поле?')) {
            $.ajax({ url: `/api/field/delete/${$(this).data('id')}`, type: 'DELETE', success: () => { fieldsTable.ajax.reload(null, false); loadMapData(); } });
        }
    });
}

function initOwnersTable() {
    if (ownersTable) { ownersTable.ajax.reload(); return; }
    ownersTable = $('#owners-table').DataTable({
        ajax: "/api/owners",
        columns: [ { data: "id" }, { data: "name" } ],
        language: { url: "//cdn.datatables.net/plug-ins/1.11.5/i18n/ru.json" }
    });
    $('#add-owner-form').off('submit').on('submit', function(e) {
        e.preventDefault();
        $.ajax({ url: '/api/owner/add', type: 'POST', contentType: 'application/json', data: JSON.stringify({ name: $('#owner-name').val() }), success: () => { $('#owner-name').val(''); ownersTable.ajax.reload(); } });
    });
}

// --- 4. STATISTICS LOGIC ---

function initStatsView() {
    $.getJSON('/api/fields_data', function(response) {
        const data = response.data;
        
        // 1. Общие цифры
        let totalArea = 0;
        const statusMap = {}; // Для диаграммы статусов
        const ownerMap = {};  // Для диаграммы владельцев

        data.forEach(field => {
            const props = JSON.parse(field.properties || '{}');
            const area = (props.area_sq_m || 0) / 10000;
            totalArea += area;

            // Группировка по статусу
            const status = field.land_status || "Не указан";
            statusMap[status] = (statusMap[status] || 0) + area;

            // Группировка по владельцу
            const owner = field.owner || "Не назначен";
            ownerMap[owner] = (ownerMap[owner] || 0) + area;
        });

        $('#stat-total-fields').text(data.length);
        $('#stat-total-area').text(totalArea.toFixed(2) + ' га');

        renderPieChart('chart-land-status', statusMap, 'Земля по статусу');
        renderPieChart('chart-owners', ownerMap, 'Земля по владельцам');
    });
}

function renderPieChart(canvasId, dataMap, title) {
    const ctx = document.getElementById(canvasId).getContext('2d');
    
    // Удаляем старый график, если есть
    if (charts[canvasId]) charts[canvasId].destroy();

    const labels = Object.keys(dataMap);
    const values = Object.values(dataMap);

    charts[canvasId] = new Chart(ctx, {
        type: 'pie',
        data: {
            labels: labels,
            datasets: [{
                data: values,
                backgroundColor: [
                    '#007bff', '#28a745', '#ffc107', '#dc3545', '#6610f2', '#fd7e14', '#20c997', '#17a2b8'
                ],
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { position: 'bottom', labels: { color: getComputedStyle(document.documentElement).getPropertyValue('--text-color').trim() } },
                tooltip: { callbacks: { label: (item) => `${item.label}: ${item.raw.toFixed(2)} га` } }
            }
        }
    });
}

// --- 5. THEME & INIT ---

function initTheme() {
    const saved = localStorage.getItem('theme') || 'light';
    $('html').attr('data-theme', saved);
    $('#theme-toggle-btn').on('click', () => {
        const current = $('html').attr('data-theme');
        const next = current === 'dark' ? 'light' : 'dark';
        $('html').attr('data-theme', next);
        localStorage.setItem('theme', next);
        if (mapInstance) {
            mapInstance.removeLayer(current === 'dark' ? baseLayers.dark : baseLayers.light);
            (next === 'dark' ? baseLayers.dark : baseLayers.light).addTo(mapInstance);
        }
        // Перерисовываем графики, чтобы обновить цвета легенд
        if (window.location.hash === '#stats') initStatsView();
    });
}

$(document).ready(function() {
    initTheme();
    initMap();
    $(window).on('hashchange', handleRoute);
    handleRoute();
    $('#sidebar-toggle').on('click', () => {
        $('body').toggleClass('sidebar-open');
        $('#sidebar').toggleClass('open');
        setTimeout(() => mapInstance?.invalidateSize(), 300);
    });
    $('#shapefile-input').on('change', function() { $('#upload-button').toggle(this.files.length > 0); });
    $('#upload-form').on('submit', function(e) {
        e.preventDefault();
        const form = this; const formData = new FormData(form);
        $('#upload-status').text('Загрузка...');
        $.ajax({
            url: '/upload', type: 'POST', data: formData, processData: false, contentType: false,
            success: () => { $('#upload-status').text('Успех!'); loadMapData(); if (fieldsTable) fieldsTable.ajax.reload(); form.reset(); $('#upload-button').hide(); setTimeout(() => $('#upload-status').text(''), 3000); },
            error: () => $('#upload-status').text('Ошибка')
        });
    });
});
