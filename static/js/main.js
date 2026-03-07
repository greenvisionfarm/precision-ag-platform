let userLocationMarker = null; // Маркер для местоположения пользователя
let mapInstance = null; // Сохраняем экземпляр карты
let editableLayers = null; // Группа слоев для редактирования Leaflet.draw

function loadFieldsAndRenderMap() {
    // Очищаем editableLayers перед загрузкой новых данных
    if (editableLayers) {
        editableLayers.clearLayers();
    }

    $.getJSON('/api/fields', function(data) {
        console.log("Данные полей получены:", data);

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
                            const areaHa = (areaSqM / 10000).toFixed(2); // Переводим в гектары и округляем
                            popupContent += `<br><b>Площадь:</b> ${areaHa} га`;
                        }
                        layer.bindPopup(popupContent);
                    }
                    // Добавляем каждый загруженный слой в editableLayers
                    editableLayers.addLayer(layer);
                }
            }); // Не добавляем напрямую на карту, так как editableLayers уже на карте

            if (editableLayers.getBounds().isValid()) {
                mapInstance.fitBounds(editableLayers.getBounds());
            }
        } else {
            console.log("Нет данных для отображения.");
        }
    }).fail(function(jqXHR, textStatus, errorThrown) {
        console.error("Ошибка при загрузке данных полей: " + textStatus, errorThrown);
        $('#upload-status').text("Ошибка загрузки данных карты.").css('color', 'red');
    });
}

$(document).ready(function() {
    if ($('#map').length) {
        mapInstance = L.map('map').setView([54.5, 38.0], 5);

        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        }).addTo(mapInstance);

        mapInstance.locate({setView: true, maxZoom: 16});

        mapInstance.on('locationfound', function(e) {
            console.log("Местоположение пользователя найдено:", e.latlng);
            if (userLocationMarker) {
                mapInstance.removeLayer(userLocationMarker);
            }
            userLocationMarker = L.marker(e.latlng).addTo(mapInstance)
                .bindPopup("Вы здесь!").openPopup();
            L.circle(e.latlng, e.accuracy).addTo(mapInstance);
        });

        mapInstance.on('locationerror', function(e) {
            console.error("Ошибка определения местоположения:", e.message);
        });

        // --- НАЧАЛО ИСПРАВЛЕНИЯ: Leaflet.draw для удаления ---
        editableLayers = new L.FeatureGroup();
        mapInstance.addLayer(editableLayers);

        const drawControl = new L.Control.Draw({
            edit: {
                featureGroup: editableLayers,
                remove: true, // Включаем инструмент удаления
                edit: false   // Отключаем инструмент редактирования (пока)
            },
            draw: {
                polygon: false, // Отключаем инструменты рисования (пока)
                polyline: false,
                rectangle: false,
                circle: false,
                marker: false,
                circlemarker: false
            }
        });
        mapInstance.addControl(drawControl);

        mapInstance.on(L.Draw.Event.DELETED, function (e) {
            const layers = e.layers;
            layers.eachLayer(function (layer) {
                const fieldId = layer.feature.properties.db_id;
                if (fieldId) {
                    console.log("Попытка удалить поле с ID:", fieldId);
                    $.ajax({
                        url: `/api/field/delete/${fieldId}`,
                        type: 'DELETE',
                        success: function(response) {
                            console.log("Поле успешно удалено:", response);
                            // Перезагружаем карту, чтобы обновить отображение
                            loadFieldsAndRenderMap();
                            // Если есть таблица, ее тоже нужно обновить
                            if ($.fn.DataTable.isDataTable('#fields-table')) {
                                $('#fields-table').DataTable().ajax.reload();
                            }
                        },
                        error: function(jqXHR, textStatus, errorThrown) {
                            const errorMsg = jqXHR.responseJSON && jqXHR.responseJSON.error ? jqXHR.responseJSON.error : 'Неизвестная ошибка при удалении.';
                            console.error("Ошибка при удалении поля:", errorMsg, jqXHR);
                            alert("Ошибка при удалении поля: " + errorMsg);
                            // Если ошибка, возможно, стоит перезагрузить карту, чтобы вернуть удаленный слой
                            loadFieldsAndRenderMap();
                        }
                    });
                } else {
                    console.warn("Удален слой без db_id. Возможно, это не поле из БД.");
                }
            });
        });
        // --- КОНЕЦ ИСПРАВЛЕНИЯ: Leaflet.draw для удаления ---

        loadFieldsAndRenderMap();
    }


    // Управление видимостью кнопки загрузки
    $('#shapefile-input').on('change', function() {
        const uploadButton = $('#upload-button');
        const uploadStatus = $('#upload-status');
        
        if (this.files && this.files.length > 0) {
            uploadButton.show();
        } else {
            uploadButton.hide();
        }
        // Очищаем статус при выборе нового файла
        uploadStatus.text('');
    });


    // Обработчик формы загрузки (всегда активен, так как форма в сайдбаре)
    $('#upload-form').on('submit', function(e) {
        e.preventDefault();

        const form = $(this);
        const formData = new FormData(form[0]);
        const uploadStatus = $('#upload-status');

        uploadStatus.text('Загрузка...').css('color', 'blue');
        console.log("Начало отправки файла...");

        $.ajax({
            url: '/upload',
            type: 'POST',
            data: formData,
            processData: false,
            contentType: false,
            beforeSend: function() {
                console.log("AJAX запрос на /upload отправляется.");
            },
            success: function(response) {
                uploadStatus.text(response.message || 'Файл успешно загружен!').css('color', 'green');
                console.log("Загрузка успешна:", response);
                // Если мы на странице карты, перезагружаем поля
                if (mapInstance) {
                    loadFieldsAndRenderMap();
                }
                location.reload();
            },
            error: function(jqXHR, textStatus, errorThrown) {
                const errorMsg = jqXHR.responseJSON && jqXHR.responseJSON.error ? jqXHR.responseJSON.error : 'Неизвестная ошибка.';
                uploadStatus.text('Ошибка загрузки: ' + errorMsg).css('color', 'red');
                console.error("Ошибка загрузки:", textStatus, errorThrown, jqXHR.responseJSON);
                console.error("Полный объект ошибки AJAX:", jqXHR);
            }
        });
    });

    // Обработчик кнопки переключения сайдбара
    $('#sidebar-toggle').on('click', function() {
        $('body').toggleClass('sidebar-open');
        $('#sidebar').toggleClass('open');
        if (mapInstance) {
            mapInstance.invalidateSize();
        }
    });
});
