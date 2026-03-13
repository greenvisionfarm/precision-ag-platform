const fs = require('fs');
const path = require('path');
const { TextEncoder, TextDecoder } = require('util');
global.TextEncoder = TextEncoder;
global.TextDecoder = TextDecoder;
const { JSDOM } = require('jsdom');

describe('Field Click to Detail Modal', () => {
    let dom;
    let window;
    let $;
    let MapManager;
    let layerMock;

    beforeAll(() => {
        const apiCode = fs.readFileSync(path.resolve(__dirname, 'modules/api.js'), 'utf8');
        const mapCode = fs.readFileSync(path.resolve(__dirname, 'modules/map_manager.js'), 'utf8');
        const mainCode = fs.readFileSync(path.resolve(__dirname, 'main.js'), 'utf8');

        dom = new JSDOM(`
            <!DOCTYPE html>
            <html>
            <body>
                <div id="map"></div>
                <div id="view-field-detail" style="display:none;">
                    <div id="field-detail-name"></div>
                    <div id="field-detail-map"></div>
                </div>
            </body>
            </html>
        `, { url: "http://localhost/", runScripts: "dangerously" });

        window = dom.window;
        global.window = window;
        global.document = window.document;

        // Mock Leaflet
        layerMock = {
            on: jest.fn(),
            addTo: jest.fn().mockReturnThis(),
            bindPopup: jest.fn().mockReturnThis()
        };

        window.L = {
            DomEvent: { stopPropagation: jest.fn() },
            map: jest.fn().mockReturnValue({
                setView: jest.fn().mockReturnThis(),
                addLayer: jest.fn(),
                addControl: jest.fn(),
                on: jest.fn(),
                locate: jest.fn()
            }),
            tileLayer: jest.fn().mockReturnValue({ addTo: jest.fn() }),
            FeatureGroup: jest.fn().mockImplementation(() => ({
                addTo: jest.fn(),
                clearLayers: jest.fn(),
                addLayer: jest.fn(),
                getBounds: () => ({ isValid: () => false })
            })),
            Control: { Draw: jest.fn() },
            Draw: { Event: { CREATED: 'c', EDITED: 'e', DELETED: 'd' } },
            geoJSON: jest.fn().mockImplementation((data, options) => {
                if (options && options.onEachFeature && data.features) {
                    data.features.forEach(f => options.onEachFeature(f, layerMock));
                }
                return layerMock;
            })
        };

        // Mock jQuery
        const jqueryCode = fs.readFileSync(require.resolve('jquery'), 'utf8');
        const jqScript = window.document.createElement("script");
        jqScript.textContent = jqueryCode;
        window.document.head.appendChild(jqScript);
        $ = window.$;
        global.$ = $;

        // Mock Swal
        window.Swal = { fire: jest.fn() };

        // Load modules
        const apiScript = window.document.createElement("script");
        apiScript.textContent = apiCode;
        window.document.head.appendChild(apiScript);

        const mapScript = window.document.createElement("script");
        mapScript.textContent = mapCode;
        window.document.head.appendChild(mapScript);

        const mainScript = window.document.createElement("script");
        mainScript.textContent = mainCode;
        window.document.head.appendChild(mainScript);

        MapManager = window.MapManager;
    });

    beforeEach(() => {
        jest.clearAllMocks();
    });

    test('MapManager.renderFields should attach click event to layers', () => {
        const testGeoJSON = {
            type: "FeatureCollection",
            features: [{ type: "Feature", properties: { db_id: 123, name: "Test" }, geometry: { type: "Point", coordinates: [0,0] } }]
        };

        MapManager.initMainMap('map');
        MapManager.renderFields(testGeoJSON, jest.fn(), jest.fn());

        // Проверяем, что на слой повесили событие 'click'
        expect(layerMock.on).toHaveBeenCalledWith('click', expect.any(Function));
    });

    test('Clicking a field should call openFieldModal (or equivalent logic)', () => {
        const testGeoJSON = {
            type: "FeatureCollection",
            features: [{ type: "Feature", properties: { db_id: 123, name: "Test" }, geometry: { type: "Point", coordinates: [0,0] } }]
        };

        const onFieldClick = jest.fn();
        MapManager.renderFields(testGeoJSON, jest.fn(), onFieldClick);
        
        // Получаем функцию-обработчик клика из мока
        const clickHandler = layerMock.on.mock.calls.find(call => call[0] === 'click')[1];
        
        clickHandler({ stopPropagation: jest.fn() });
        
        expect(onFieldClick).toHaveBeenCalledWith(123);
    });
});
