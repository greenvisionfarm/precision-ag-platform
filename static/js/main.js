let userLocationMarker = null; // Маркер для местоположения пользователя
let mapInstance = null; // Сохраняем экземпляр карты
let editableLayers = null; // Группа слоев для редактирования Leaflet.draw
let baseLayers = {}; // Объект для хранения базовых слоев (светлый/темный)

function loadFieldsAndRenderMap() {
    if (editableLayers) {
        editableLayers.clearLayers();
    }

    $.getJSON('/api/fields', function(data) {
        if (data.features && data.features.length > 0) {
            L.geoJSON(data, {
                style: function(feature) {
                    return {
                        color: "#007BFF",
                        weight: 2,
                        fillColor: "#007BFF",
                        fillOpacity: 0.3
                    };
                },
                onEachFeature: function(feature, layer) {
                    if (feature.properties) {
                        const fieldName = feature.properties.name || feature.properties.NAME || feature.properties.db_id || 'N/A';
                        let popupContent = `<b>Поле:</b> ${fieldName}`;

                        const areaSqM = feature.properties.area_sq_m;
                        if (typeof areaSqM === 'number') {
                            const areaHa = (areaSqM / 10000).toFixed(2);
                            popupContent += `<br><b>Площадь:</b> ${areaHa} га`;
                        }
                        layer.bindPopup(popupContent);
                    }
                    editableLayers.addLayer(layer);
                }
            });

            if (editableLayers.getBounds().isValid()) {
                mapInstance.fitBounds(editableLayers.getBounds());
            }
        }
    }).fail(function(jqXHR, textStatus, errorThrown) {
        console.error("Ошибка при загрузке данных полей: " + textStatus, errorThrown);
    });
}

function initTheme() {
    const savedTheme = localStorage.getItem('theme') || 'light';
    applyTheme(savedTheme);

    $('#theme-toggle-btn').on('click', function() {
        const currentTheme = document.documentElement.getAttribute('data-theme');
        const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
        applyTheme(newTheme);
    });
}

function applyTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('theme', theme);

    // Обновляем кнопку
    const btn = $('#theme-toggle-btn');
    if (theme === 'dark') {
        btn.find('.icon').text('☀️');
        btn.find('.text').text('Светлая тема');
    } else {
        btn.find('.icon').text('🌙');
        btn.find('.text').text('Темная тема');
    }

    // Обновляем карту, если она инициализирована
    if (mapInstance) {
        if (theme === 'dark') {
            mapInstance.removeLayer(baseLayers.light);
            baseLayers.dark.addTo(mapInstance);
        } else {
            mapInstance.removeLayer(baseLayers.dark);
            baseLayers.light.addTo(mapInstance);
        }
    }
}

$(document).ready(function() {
    initTheme();

    if ($('#map').length) {
        mapInstance = L.map('map').setView([54.5, 38.0], 5);

        baseLayers.light = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        });

        baseLayers.dark = L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
            subdomains: 'abcd',
            maxZoom: 20
        });

        // Применяем начальный слой в зависимости от темы
        const currentTheme = localStorage.getItem('theme') || 'light';
        if (currentTheme === 'dark') {
            baseLayers.dark.addTo(mapInstance);
        } else {
            baseLayers.light.addTo(mapInstance);
        }

        mapInstance.locate({setView: true, maxZoom: 16});

        mapInstance.on('locationfound', function(e) {
            if (userLocationMarker) {
                mapInstance.removeLayer(userLocationMarker);
            }
            userLocationMarker = L.marker(e.latlng).addTo(mapInstance)
                .bindPopup("Вы здесь!").openPopup();
            L.circle(e.latlng, e.accuracy).addTo(mapInstance);
        });

        editableLayers = new L.FeatureGroup();
        mapInstance.addLayer(editableLayers);

        const drawControl = new L.Control.Draw({
            edit: {
                featureGroup: editableLayers,
                remove: true,
                edit: true
            },
            draw: {
                polygon: {
                    allowIntersection: false,
                    showArea: true,
                    drawError: {
                        color: '#e1e100',
                        message: '<strong>Ошибка:</strong> полигоны не могут пересекаться!'
                    },
                    shapeOptions: {
                        color: '#007BFF'
                    }
                },
                polyline: false,
                rectangle: false,
                circle: false,
                marker: false,
                circlemarker: false
            }
        });
        mapInstance.addControl(drawControl);

        mapInstance.on(L.Draw.Event.CREATED, function (e) {
            const layer = e.layer;
            const geometry = layer.toGeoJSON().geometry;
            const name = prompt("Введите название поля:", "Новое поле");
            if (name === null) return;

            $.ajax({
                url: '/api/field/add',
                type: 'POST',
                contentType: 'application/json',
                data: JSON.stringify({
                    geometry: geometry,
                    name: name
                }),
                success: function(response) {
                    editableLayers.addLayer(layer);
                    loadFieldsAndRenderMap();
                },
                error: function(jqXHR) {
                    alert("Ошибка: " + (jqXHR.responseJSON?.error || 'Ошибка при добавлении.'));
                }
            });
        });

        mapInstance.on(L.Draw.Event.EDITED, function (e) {
            const layers = e.layers;
            layers.eachLayer(function (layer) {
                const fieldId = layer.feature?.properties.db_id;
                if (!fieldId) return;

                $.ajax({
                    url: `/api/field/update_geometry/${fieldId}`,
                    type: 'PUT',
                    contentType: 'application/json',
                    data: JSON.stringify({ geometry: layer.toGeoJSON().geometry }),
                    success: function() {
                        loadFieldsAndRenderMap();
                    },
                    error: function(jqXHR) {
                        alert("Ошибка: " + (jqXHR.responseJSON?.error || 'Ошибка при сохранении.'));
                    }
                });
            });
        });

        mapInstance.on(L.Draw.Event.DELETED, function (e) {
            const layers = e.layers;
            layers.eachLayer(function (layer) {
                const fieldId = layer.feature?.properties.db_id;
                if (fieldId) {
                    $.ajax({
                        url: `/api/field/delete/${fieldId}`,
                        type: 'DELETE',
                        success: function() {
                            loadFieldsAndRenderMap();
                            if ($.fn.DataTable.isDataTable('#fields-table')) {
                                $('#fields-table').DataTable().ajax.reload();
                            }
                        }
                    });
                }
            });
        });

        loadFieldsAndRenderMap();
    }

    // Сайдбар и форма загрузки
    $('#sidebar-toggle').on('click', function() {
        $('body').toggleClass('sidebar-open');
        $('#sidebar').toggleClass('open');
        if (mapInstance) mapInstance.invalidateSize();
    });

    $('#shapefile-input').on('change', function() {
        if (this.files?.length > 0) $('#upload-button').show();
        else $('#upload-button').hide();
        $('#upload-status').text('');
    });

    $('#upload-form').on('submit', function(e) {
        e.preventDefault();
        const formData = new FormData(this);
        const status = $('#upload-status');
        status.text('Загрузка...').css('color', 'blue');

        $.ajax({
            url: '/upload',
            type: 'POST',
            data: formData,
            processData: false,
            contentType: false,
            success: function(response) {
                status.text(response.message || 'Успех!').css('color', 'green');
                if (mapInstance) loadFieldsAndRenderMap();
                setTimeout(() => location.reload(), 1000);
            },
            error: function(jqXHR) {
                status.text('Ошибка: ' + (jqXHR.responseJSON?.error || 'Неизвестная ошибка.')).css('color', 'red');
            }
        });
    });
});
