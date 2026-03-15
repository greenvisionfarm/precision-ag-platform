// Глобальные переменные
let ownersList = [];
let fieldsTable = null;
let ownersTable = null;
let charts = {}; 

// --- 1. ROUTING & UI ---

function handleRoute() {
    const hash = window.location.hash || '#map';
    $('.view-section').hide();
    $('.nav-link').removeClass('active');

    if (hash === '#map') {
        $('#view-map').show();
        $('.nav-link[href="#map"]').addClass('active');
        MapManager.instance?.invalidateSize();
    } else if (hash === '#fields') {
        $('#view-fields').show();
        $('.nav-link[href="#fields"]').addClass('active');
        initFieldsTable();
    } else if (hash.startsWith('#field/')) {
        const fieldId = hash.split('/')[1];
        $('#view-field-detail').show();
        showFieldDetail(fieldId);
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

function showFieldDetail(id) {
    API.getField(id).then(field => {
        $('#field-detail-name').text(field.name);
        $('#field-detail-area').text(field.area);
        $('#field-detail-owner').text(field.owner);
        $('#field-detail-status').text(field.land_status);
        $('#field-detail-parcel').text(field.parcel_number);

        $('#detail-export-kmz').off('click').on('click', () => downloadKmzWithSettings(id));
        $('#detail-delete-field').off('click').on('click', () => {
            Swal.fire({ title: 'Удалить поле?', icon: 'warning', showCancelButton: true }).then(r => {
                if (r.isConfirmed) API.deleteField(id).then(() => window.location.hash = '#fields');
            });
        });

        MapManager.initDetailMap('field-detail-map', field.geometry, field.zones);
    }).fail(() => {
        Swal.fire('Ошибка', 'Данные не найдены', 'error');
        window.location.hash = '#fields';
    });
}

function openFieldModal(id) {
    // Показываем прелоадер
    Swal.fire({
        title: 'Загрузка...',
        allowOutsideClick: false,
        didOpen: () => Swal.showLoading()
    });

    API.getField(id).then(field => {
        const area = field.area;
        const owner = field.owner || 'Не назначен';
        const status = field.land_status || 'Не указан';
        const parcel = field.parcel_number || 'N/A';

        Swal.fire({
            title: field.name,
            html: `
                <div class="modal-detail-grid">
                    <div id="modal-field-map" style="height: 300px; border-radius: 8px; margin-bottom: 15px;"></div>
                    <table class="info-table" style="width: 100%; text-align: left;">
                        <tr><th>Площадь:</th><td>${area}</td></tr>
                        <tr><th>Владелец:</th><td>${owner}</td></tr>
                        <tr><th>Статус:</th><td>${status}</td></tr>
                        <tr><th>Кадастровый №:</th><td>${parcel}</td></tr>
                    </table>
                    <div style="margin-top: 20px; display: flex; gap: 10px; justify-content: center;">
                        <button id="modal-export-kmz" class="btn btn-primary btn-sm"><i class="fas fa-file-download"></i> Экспорт KMZ</button>
                        <button id="modal-go-to-detail" class="btn btn-outline-primary btn-sm"><i class="fas fa-external-link-alt"></i> На страницу поля</button>
                    </div>
                </div>
            `,
            width: '600px',
            showConfirmButton: false,
            showCloseButton: true,
            didOpen: () => {
                // Инициализируем карту в модальном окне с зонами
                MapManager.initDetailMap('modal-field-map', field.geometry, field.zones);
                
                $('#modal-export-kmz').on('click', () => {
                    Swal.close();
                    downloadKmzWithSettings(id);
                });
                
                $('#modal-go-to-detail').on('click', () => {
                    Swal.close();
                    window.location.hash = `#field/${id}`;
                });
            }
        });
    }).fail(() => {
        Swal.fire('Ошибка', 'Не удалось загрузить данные поля', 'error');
    });
}

// --- 2. MAP CALLBACKS ---

function loadMapData() {
    API.getFields().then(data => MapManager.renderFields(data, downloadKmzWithSettings, openFieldModal));
}

function onFieldCreated(e) {
    Swal.fire({ title: 'Название поля', input: 'text', inputValue: 'Новое поле', showCancelButton: true }).then(res => {
        if (res.isConfirmed && res.value) {
            API.addField(e.layer.toGeoJSON().geometry, res.value).then(() => {
                loadMapData();
                fieldsTable?.ajax.reload();
            });
        }
    });
}

function onFieldEdited(e) {
    e.layers.eachLayer(layer => {
        const id = layer.feature?.properties?.db_id;
        if (id) API.updateField(id, 'update_geometry', { geometry: layer.toGeoJSON().geometry }).then(() => {
            loadMapData();
            fieldsTable?.ajax.reload();
        });
    });
}

function onFieldDeleted(e) {
    e.layers.eachLayer(layer => {
        const id = layer.feature?.properties?.db_id;
        if (id) API.deleteField(id).then(() => { loadMapData(); fieldsTable?.ajax.reload(); });
    });
}

// --- 3. TABLES & DIALOGS ---

function downloadKmzWithSettings(fieldId) {
    Swal.fire({
        title: 'Настройки DJI KMZ',
        html: `
            <div style="text-align: left;">
                <div class="form-group mb-2">
                    <label>Высота полета (м):</label>
                    <input type="number" id="swal-h" class="swal2-input" value="100" min="20" max="150" style="margin: 5px 0;">
                    <small class="text-muted">Высота над точкой взлета. Для NDVI оптимально 100-120м.</small>
                </div>
                <div class="form-group mb-2">
                    <label>Фронтальное перекрытие (%):</label>
                    <input type="number" id="swal-oh" class="swal2-input" value="80" min="40" max="90" style="margin: 5px 0;">
                    <small class="text-muted">Наложение снимков по ходу движения. Нужно 75-80%.</small>
                </div>
                <div class="form-group mb-2">
                    <label>Боковое перекрытие (%):</label>
                    <input type="number" id="swal-ow" class="swal2-input" value="70" min="40" max="90" style="margin: 5px 0;">
                    <small class="text-muted">Наложение между проходами (галсами). Обычно 70-75%.</small>
                </div>
                <div class="form-group mb-2">
                    <label>Угол курса (град):</label>
                    <input type="number" id="swal-dir" class="swal2-input" value="0" min="0" max="360" style="margin: 5px 0;">
                    <small class="text-muted">Направление полета. 0 - север, 90 - восток.</small>
                </div>
            </div>`,
        focusConfirm: false,
        preConfirm: () => {
            return {
                height: document.getElementById('swal-h').value,
                oh: document.getElementById('swal-oh').value,
                ow: document.getElementById('swal-ow').value,
                dir: document.getElementById('swal-dir').value
            }
        }
    }).then(res => {
        if (res.isConfirmed) {
            const p = res.value;
            const url = '/api/field/export/kmz/' + fieldId + '?height=' + p.height + '&overlap_h=' + p.oh + '&overlap_w=' + p.ow + '&direction=' + p.dir;
            window.location.href = url;
        }
    });
}

function initFieldsTable() {
    API.getOwners().then(res => {
        ownersList = res.data;
        if (fieldsTable) { fieldsTable.ajax.reload(); return; }
        fieldsTable = $('#fields-table').DataTable({
            ajax: "/api/fields_data",
            columns: [
                { data: "id" },
                { data: "name", render: (d, t, r) => `<span class="editable-name" data-id="${r.id}">${d}</span>` },
                { data: "area" },
                { data: "owner_id", render: (d, t, r) => {
                    let opts = '<option value="">Не назначен</option>';
                    ownersList.forEach(o => { opts += `<option value="${o.id}" ${o.id == d ? 'selected' : ''}>${o.name}</option>`; });
                    return `<select class="owner-select" data-id="${r.id}">${opts}</select>`;
                }},
                { data: "land_status", render: (d, t, r) => {
                    let opts = '<option value="">Не указан</option>';
                    ["Собственность", "Аренда", "Субаренда"].forEach(s => { opts += `<option value="${s}" ${s === d ? 'selected' : ''}>${s}</option>`; });
                    return `<select class="status-select" data-id="${r.id}">${opts}</select>`;
                }},
                { data: "parcel_number", render: (d, t, r) => `<span class="editable-parcel" data-id="${r.id}">${d || 'N/A'}</span>` },
                { data: null, render: (d, t, r) => `<div class="btn-group"><button onclick="downloadKmzWithSettings(${r.id})" class="btn btn-outline-primary btn-sm"><i class="fas fa-cog"></i></button><button class="btn-save-details btn-success btn-sm" data-id="${r.id}" style="display:none;"><i class="fas fa-save"></i></button><button class="btn-delete btn-danger btn-sm" data-id="${r.id}"><i class="fas fa-trash"></i></button></div>` }
            ],
            language: {
                "processing": "Подождите...",
                "search": "Поиск:",
                "lengthMenu": "Показать _MENU_ записей",
                "info": "Записи с _START_ до _END_ из _TOTAL_ записей",
                "infoEmpty": "Записи с 0 до 0 из 0 записей",
                "infoFiltered": "(отфильтровано из _MAX_ записей)",
                "loadingRecords": "Загрузка записей...",
                "zeroRecords": "Записи отсутствуют.",
                "emptyTable": "В таблице отсутствуют данные",
                "paginate": {
                    "first": "Первая",
                    "previous": "Предыдущая",
                    "next": "Следующая",
                    "last": "Последняя"
                },
                "aria": {
                    "sortAscending": ": активировать для сортировки столбца по возрастанию",
                    "sortDescending": ": активировать для сортировки столбца по убыванию"
                }
            }
        });
        setupTableEvents();
    });
}

function setupTableEvents() {
    const tb = $('#fields-table tbody');
    tb.on('click', 'td', function(e) {
        if ($(e.target).closest('.btn-group, select, input, .editable-name, .editable-parcel').length) return;
        const r = fieldsTable.row($(this).closest('tr')).data();
        if (r?.id) window.location.hash = `#field/${r.id}`;
    });
    tb.on('change', '.owner-select, .status-select', function() { $(this).closest('tr').find('.btn-save-details').show(); });
    tb.on('click', '.btn-save-details', function() {
        const b = $(this); const id = b.data('id'); const r = b.closest('tr');
        API.updateField(id, 'assign_owner', { owner_id: r.find('.owner-select').val() });
        API.updateField(id, 'update_details', { land_status: r.find('.status-select').val(), parcel_number: r.find('.editable-parcel').text() }).then(() => b.hide());
    });
    tb.on('click', '.editable-name', function() {
        const s = $(this); if (s.find('input').length) return;
        const i = $('<input>').val(s.text()); s.html(i);
        i.focus().on('blur keypress', function(e) {
            if (e.type === 'keypress' && e.which !== 13) return;
            const n = $(this).val();
            API.updateField(s.data('id'), 'rename', { new_name: n }).then(() => { s.text(n); fieldsTable.ajax.reload(null, false); });
        });
    });
    tb.on('click', '.btn-delete', function() {
        const id = $(this).data('id');
        Swal.fire({ title: 'Удалить?', icon: 'warning', showCancelButton: true }).then(r => {
            if (r.isConfirmed) API.deleteField(id).then(() => { fieldsTable.ajax.reload(null, false); loadMapData(); });
        });
    });
}

function initOwnersTable() {
    if (ownersTable) { ownersTable.ajax.reload(); return; }
    ownersTable = $('#owners-table').DataTable({
        ajax: "/api/owners",
        columns: [ { data: "id" }, { data: "name" }, { data: null, render: (d, t, r) => `<button class="btn btn-danger btn-sm btn-delete-owner" data-id="${r.id}"><i class="fas fa-trash"></i></button>` } ],
        language: { url: "//cdn.datatables.net/plug-ins/1.11.5/i18n/ru.json" }
    });
    $('#owners-table tbody').on('click', '.btn-delete-owner', function() {
        const id = $(this).data('id');
        Swal.fire({ title: 'Удалить?', icon: 'warning', showCancelButton: true }).then(r => {
            if (r.isConfirmed) API.deleteOwner(id).then(() => { ownersTable.ajax.reload(); fieldsTable?.ajax.reload(); });
        });
    });
    $('#add-owner-form').on('submit', function(e) {
        e.preventDefault();
        API.addOwner($('#owner-name').val()).then(() => { $('#owner-name').val(''); ownersTable.ajax.reload(); });
    });
}

// --- 4. STATISTICS & THEME ---

function initStatsView() {
    API.getFieldsData().then(res => {
        const data = res.data;
        let total = 0; const sMap = {}; const oMap = {};
        data.forEach(f => {
            const a = (JSON.parse(f.properties || '{}').area_sq_m || 0) / 10000;
            total += a;
            sMap[f.land_status || "N/A"] = (sMap[f.land_status || "N/A"] || 0) + a;
            oMap[f.owner || "N/A"] = (oMap[f.owner || "N/A"] || 0) + a;
        });
        $('#stat-total-fields').text(data.length);
        $('#stat-total-area').text(total.toFixed(2) + ' га');
        renderPieChart('chart-land-status', sMap);
        renderPieChart('chart-owners', oMap);
    });
}

function renderPieChart(id, map) {
    const ctx = document.getElementById(id).getContext('2d');
    if (charts[id]) charts[id].destroy();
    charts[id] = new Chart(ctx, {
        type: 'pie', data: { labels: Object.keys(map), datasets: [{ data: Object.values(map), backgroundColor: ['#007bff', '#28a745', '#ffc107', '#dc3545', '#6610f2'] }] },
        options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: 'bottom', labels: { color: getComputedStyle(document.documentElement).getPropertyValue('--text-color').trim() } } } }
    });
}

function initTheme() {
    const saved = localStorage.getItem('theme') || 'light';
    $('html').attr('data-theme', saved);
    $('#theme-toggle-btn').on('click', () => {
        const curr = $('html').attr('data-theme');
        const next = curr === 'dark' ? 'light' : 'dark';
        $('html').attr('data-theme', next);
        localStorage.setItem('theme', next);
        MapManager.updateTheme(next === 'dark');
        if (window.location.hash === '#stats') initStatsView();
    });
}

$(document).ready(() => {
    initTheme();
    MapManager.initMainMap('map', onFieldCreated, onFieldEdited, onFieldDeleted);
    loadMapData();
    $(window).on('hashchange', handleRoute);
    handleRoute();
    $('#sidebar-toggle').on('click', () => {
        $('body').toggleClass('sidebar-open');
        $('#sidebar').toggleClass('open');
        setTimeout(() => MapManager.instance?.invalidateSize(), 300);
    });
    $('#shapefile-input').on('change', function() { $('#upload-button').toggle(this.files.length > 0); });
    $('#upload-form').on('submit', function(e) {
        e.preventDefault();
        $('#upload-status').text('Загрузка...');
        $.ajax({ url: '/upload', type: 'POST', data: new FormData(this), processData: false, contentType: false,
            success: () => { $('#upload-status').text('Успех!'); loadMapData(); fieldsTable?.ajax.reload(); this.reset(); $('#upload-button').hide(); setTimeout(() => $('#upload-status').text(''), 3000); },
            error: () => $('#upload-status').text('Ошибка')
        });
    });

    $('#raster-input').on('change', function() { $('#raster-upload-button').toggle(this.files.length > 0); });
    $('#raster-upload-form').on('submit', function(e) {
        e.preventDefault();
        const statusDiv = $('#raster-upload-status');
        const btn = $('#raster-upload-button');

        statusDiv.html('<i class="fas fa-spinner fa-spin"></i> Загрузка файла...').show();
        btn.prop('disabled', true);

        $.ajax({
            url: '/upload',
            type: 'POST',
            data: new FormData(this),
            processData: false,
            contentType: false,
            success: (res) => {
                if (res.task_id) {
                    statusDiv.html(`<i class="fas fa-cog fa-spin"></i> Файл на сервере. Анализ NDVI...`);
                    pollTaskStatus(res.task_id, res.field_id);
                } else {
                    statusDiv.html('<span class="text-success">Готово!</span>');
                    btn.prop('disabled', false);
                    this.reset();
                    if (res.field_id) window.location.hash = `#field/${res.field_id}`;
                }
            },
            error: (xhr) => {
                const err = xhr.responseJSON?.error || 'Ошибка загрузки';
                statusDiv.html(`<span class="text-danger">${err}</span>`);
                btn.prop('disabled', false);
            }
        });
    });

    function pollTaskStatus(taskId, fieldId) {
        const statusDiv = $('#raster-upload-status');
        const interval = setInterval(() => {
            $.getJSON(`/api/task/${taskId}`, function(res) {
                if (res.status === 'completed') {
                    clearInterval(interval);
                    statusDiv.html('<span class="text-success"><i class="fas fa-check"></i> Анализ завершен!</span>');
                    setTimeout(() => {
                        statusDiv.hide();
                        $('#raster-upload-button').prop('disabled', false).hide();
                        $('#raster-upload-form')[0].reset();
                        if (window.location.hash === `#field/${fieldId}`) {
                            showFieldDetail(fieldId);
                        } else {
                            window.location.hash = `#field/${fieldId}`;
                        }
                        loadMapData(); // Обновить геометрию на главной карте
                    }, 2000);
                } else if (res.status === 'error') {
                    clearInterval(interval);
                    statusDiv.html(`<span class="text-danger"><i class="fas fa-exclamation-triangle"></i> Ошибка: ${res.message}</span>`);
                    $('#raster-upload-button').prop('disabled', false);
                }
            });
        }, 3000);
    }
});
