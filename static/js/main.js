// Глобальные переменные
let mapInstance = null;
let editableLayers = null;
let baseLayers = {};
let ownersList = [];
let fieldsTable = null;
let ownersTable = null;

// --- 1. ROUTING & UI ---

function handleRoute() {
    const hash = window.location.hash || '#map';
    
    // Скрываем все views
    $('.view-section').hide();
    $('.nav-link').removeClass('active');

    // Активируем нужную
    if (hash === '#map') {
        $('#view-map').show();
        $('.nav-link[href="#map"]').addClass('active');
        if (mapInstance) mapInstance.invalidateSize();
    } else if (hash === '#fields') {
        $('#view-fields').show();
        $('.nav-link[href="#fields"]').addClass('active');
        initFieldsTable(); // Инициализируем или обновляем таблицу
    } else if (hash === '#owners') {
        $('#view-owners').show();
        $('.nav-link[href="#owners"]').addClass('active');
        initOwnersTable();
    }
}

// --- 2. MAP LOGIC ---

function initMap() {
    if ($('#map').length === 0 || mapInstance) return;

    mapInstance = L.map('map').setView([48.66, 19.69], 8); // Словакия

    baseLayers.light = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; OpenStreetMap'
    });

    baseLayers.dark = L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
        attribution: '&copy; CARTO',
        subdomains: 'abcd',
        maxZoom: 20
    });

    const currentTheme = localStorage.getItem('theme') || 'light';
    (currentTheme === 'dark' ? baseLayers.dark : baseLayers.light).addTo(mapInstance);

    editableLayers = new L.FeatureGroup();
    mapInstance.addLayer(editableLayers);

    // Инструменты рисования
    const drawControl = new L.Control.Draw({
        edit: { featureGroup: editableLayers },
        draw: {
            polygon: {
                allowIntersection: false,
                showArea: true,
                shapeOptions: { color: '#007BFF' }
            },
            polyline: false, rectangle: false, circle: false, marker: false, circlemarker: false
        }
    });
    mapInstance.addControl(drawControl);

    // События карты
    mapInstance.on(L.Draw.Event.CREATED, onFieldCreated);
    mapInstance.on(L.Draw.Event.EDITED, onFieldEdited);
    mapInstance.on(L.Draw.Event.DELETED, onFieldDeleted);

    // Геолокация
    mapInstance.locate({setView: true, maxZoom: 16});
    mapInstance.on('locationfound', e => {
        L.marker(e.latlng).addTo(mapInstance).bindPopup("Вы здесь!");
    });

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
                    layer.bindPopup(`<b>${props.name || 'Поле'}</b><br>Площадь: ${area}`);
                    editableLayers.addLayer(layer);
                }
            });
            if (editableLayers.getBounds().isValid()) mapInstance.fitBounds(editableLayers.getBounds());
        }
    });
}

// Обработчики рисования
function onFieldCreated(e) {
    const layer = e.layer;
    const name = prompt("Название поля:", "Новое поле");
    if (!name) return;

    $.ajax({
        url: '/api/field/add', type: 'POST', contentType: 'application/json',
        data: JSON.stringify({ geometry: layer.toGeoJSON().geometry, name: name }),
        success: () => { loadMapData(); loadFieldsData(); }
    });
}

function onFieldEdited(e) {
    e.layers.eachLayer(layer => {
        const id = layer.feature?.properties?.db_id;
        if (id) {
            $.ajax({
                url: `/api/field/update_geometry/${id}`, type: 'PUT', contentType: 'application/json',
                data: JSON.stringify({ geometry: layer.toGeoJSON().geometry }),
                success: () => { loadMapData(); loadFieldsData(); }
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
                success: () => { loadMapData(); loadFieldsData(); }
            });
        }
    });
}

// --- 3. TABLES LOGIC ---

function loadOwners() {
    return $.getJSON('/api/owners', function(response) {
        ownersList = response.data;
    });
}

function initFieldsTable() {
    loadOwners().then(() => {
        if (fieldsTable) {
            fieldsTable.ajax.reload();
            return;
        }

        fieldsTable = $('#fields-table').DataTable({
            ajax: "/api/fields_data",
            columns: [
                { data: "id" },
                { 
                    data: "name",
                    render: (data, type, row) => `<span class="editable-name" data-id="${row.id}">${data}</span>`
                },
                { data: "area" },
                { 
                    data: "owner_id",
                    render: (data, type, row) => {
                        let opts = '<option value="">Не назначен</option>';
                        ownersList.forEach(o => {
                            opts += `<option value="${o.id}" ${o.id == data ? 'selected' : ''}>${o.name}</option>`;
                        });
                        return `<select class="owner-select" data-id="${row.id}">${opts}</select>`;
                    }
                },
                {
                    data: "land_status",
                    render: (data, type, row) => {
                        const statuses = ["Собственность", "Аренда", "Субаренда"];
                        let opts = '<option value="">Не указан</option>';
                        statuses.forEach(s => {
                            opts += `<option value="${s}" ${s === data ? 'selected' : ''}>${s}</option>`;
                        });
                        return `<select class="status-select" data-id="${row.id}">${opts}</select>`;
                    }
                },
                { 
                    data: "parcel_number",
                    render: (data, type, row) => `<span class="editable-parcel" data-id="${row.id}">${data || 'N/A'}</span>`
                },
                {
                    data: null,
                    render: (data, type, row) => `
                        <button class="btn-save-details btn-success btn-sm" data-id="${row.id}" style="display:none;">Сохранить</button>
                        <button class="btn-delete btn-danger btn-sm" data-id="${row.id}">Удалить</button>
                    `
                }
            ],
            language: { url: "//cdn.datatables.net/plug-ins/1.11.5/i18n/ru.json" }
        });

        setupTableEvents();
    });
}

function setupTableEvents() {
    const tbody = $('#fields-table tbody');

    // Показать кнопку сохранения при изменении
    tbody.on('change', '.owner-select, .status-select', function() {
        $(this).closest('tr').find('.btn-save-details').show();
    });

    // Сохранение
    tbody.on('click', '.btn-save-details', function() {
        const btn = $(this);
        const id = btn.data('id');
        const row = btn.closest('tr');
        
        const payload = {
            owner_id: row.find('.owner-select').val(),
            land_status: row.find('.status-select').val(),
            parcel_number: row.find('.editable-parcel').text()
        };

        // Сохраняем владельца (старый эндпоинт)
        $.ajax({
            url: `/api/field/assign_owner/${id}`, type: 'PUT', contentType: 'application/json',
            data: JSON.stringify({ owner_id: payload.owner_id })
        });

        // Сохраняем детали
        $.ajax({
            url: `/api/field/update_details/${id}`, type: 'PUT', contentType: 'application/json',
            data: JSON.stringify({ land_status: payload.land_status, parcel_number: payload.parcel_number }),
            success: () => { btn.hide(); alert('Сохранено!'); }
        });
    });

    // Инлайн редактирование имени
    tbody.on('click', '.editable-name', function() {
        const span = $(this);
        if (span.find('input').length) return;
        const input = $('<input>').val(span.text());
        span.html(input);
        input.focus().on('blur keypress', function(e) {
            if (e.type === 'keypress' && e.which !== 13) return;
            const newName = $(this).val();
            $.ajax({
                url: `/api/field/rename/${span.data('id')}`, type: 'PUT', contentType: 'application/json',
                data: JSON.stringify({ new_name: newName }),
                success: () => { span.text(newName); fieldsTable.ajax.reload(null, false); }
            });
        });
    });

    // Удаление
    tbody.on('click', '.btn-delete', function() {
        if (confirm('Удалить поле?')) {
            $.ajax({
                url: `/api/field/delete/${$(this).data('id')}`, type: 'DELETE',
                success: () => { fieldsTable.ajax.reload(null, false); loadMapData(); }
            });
        }
    });
}

function loadFieldsData() {
    if (fieldsTable) fieldsTable.ajax.reload(null, false);
}

function initOwnersTable() {
    if (ownersTable) {
        ownersTable.ajax.reload();
        return;
    }
    ownersTable = $('#owners-table').DataTable({
        ajax: "/api/owners",
        columns: [ { data: "id" }, { data: "name" } ],
        language: { url: "//cdn.datatables.net/plug-ins/1.11.5/i18n/ru.json" }
    });

    $('#add-owner-form').off('submit').on('submit', function(e) {
        e.preventDefault();
        const name = $('#owner-name').val();
        $.ajax({
            url: '/api/owner/add', type: 'POST', contentType: 'application/json',
            data: JSON.stringify({ name: name }),
            success: () => { 
                alert('Владелец добавлен'); 
                $('#owner-name').val(''); 
                ownersTable.ajax.reload(); 
            }
        });
    });
}

// --- 4. THEME & INIT ---

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
    });
}

$(document).ready(function() {
    initTheme();
    
    // Инициализация карты сразу (она всегда в DOM, просто скрывается)
    initMap();

    // Роутинг
    $(window).on('hashchange', handleRoute);
    handleRoute(); // Первый запуск

    // Сайдбар
    $('#sidebar-toggle').on('click', () => {
        $('body').toggleClass('sidebar-open');
        $('#sidebar').toggleClass('open');
        setTimeout(() => mapInstance?.invalidateSize(), 300);
    });

    // Загрузка файла (общая)
    $('#shapefile-input').on('change', function() {
        $('#upload-button').toggle(this.files.length > 0);
    });

    $('#upload-form').on('submit', function(e) {
        e.preventDefault();
        const form = this;
        const formData = new FormData(form);
        $('#upload-status').text('Загрузка...').css('color', 'var(--primary-color)');
        
        $.ajax({
            url: '/upload', type: 'POST', data: formData, processData: false, contentType: false,
            success: () => { 
                $('#upload-status').text('Успех!').css('color', 'var(--success-color)'); 
                loadMapData(); 
                if (fieldsTable) fieldsTable.ajax.reload(null, false);
                
                // Очистка формы
                form.reset();
                $('#upload-button').hide();
                
                // Убираем сообщение через 3 секунды
                setTimeout(() => $('#upload-status').text(''), 3000);
            },
            error: () => {
                $('#upload-status').text('Ошибка загрузки').css('color', 'var(--danger-color)');
            }
        });
    });
});
