const fs = require('fs');
const path = require('path');
const { TextEncoder, TextDecoder } = require('util');
global.TextEncoder = TextEncoder;
global.TextDecoder = TextDecoder;
const { JSDOM } = require('jsdom');

let dom;
let window;
let $;

beforeAll(() => {
    const mainCode = fs.readFileSync(path.resolve(__dirname, 'main.js'), 'utf8');
    
    dom = new JSDOM(`
        <!DOCTYPE html>
        <html data-theme="light">
        <body>
            <div id="view-map" class="view-section" style="display: none;"></div>
            <div id="view-fields" class="view-section" style="display: none;">
                <table id="fields-table">
                    <tbody></tbody>
                </table>
            </div>
            
            <div id="view-field-detail" class="view-section" style="display: none;">
                <h1 id="field-detail-name"></h1>
                <div id="field-detail-map" style="height:100px;"></div>
                <div id="field-detail-area"></div>
                <div id="field-detail-owner"></div>
                <div id="field-detail-status"></div>
                <div id="field-detail-parcel"></div>
                <a href="#fields" class="back-link"></a>
            </div>

            <a href="#map" class="nav-link"></a>
            <button id="theme-toggle-btn"></button>
            <div id="map" style="height: 100px;"></div>
        </body>
        </html>
    `, { 
        url: "http://localhost/#map",
        runScripts: "dangerously",
        resources: "usable"
    });

    window = dom.window;
    
    // Мокаем Leaflet
    const layerMock = { 
        addTo: jest.fn().mockReturnThis(), 
        getBounds: jest.fn().mockReturnValue({ isValid: () => true, pad: () => [[0,0],[1,1]] }) 
    };
    layerMock.getBounds.mockReturnValue({
        getSouthWest: () => ({lat: 0, lng: 0}),
        getNorthEast: () => ({lat: 1, lng: 1})
    });

    window.L = { 
        map: jest.fn().mockReturnValue({ 
            setView: jest.fn().mockReturnThis(), 
            addLayer: jest.fn(), 
            addControl: jest.fn(), 
            on: jest.fn(), 
            locate: jest.fn(), 
            invalidateSize: jest.fn(),
            removeLayer: jest.fn(),
            remove: jest.fn(),
            fitBounds: jest.fn()
        }),
        tileLayer: jest.fn().mockReturnValue({ addTo: jest.fn() }),
        FeatureGroup: jest.fn().mockImplementation(() => ({ addTo: jest.fn(), clearLayers: jest.fn(), getBounds: () => ({isValid: () => false}) })),
        Control: { Draw: jest.fn() },
        Draw: { Event: { CREATED: 'c', EDITED: 'e', DELETED: 'd' } },
        geoJSON: jest.fn().mockReturnValue(layerMock)
    };
    
    window.Chart = jest.fn();
    window.Swal = { fire: jest.fn().mockResolvedValue({ isConfirmed: true, value: {} }) };
    
    const localStorageMock = (function() {
        let store = {};
        return {
            getItem: (key) => store[key] || null,
            setItem: (key, value) => { store[key] = value.toString(); },
            clear: () => { store = {}; }
        };
    })();
    Object.defineProperty(window, 'localStorage', { value: localStorageMock });

    const jqueryCode = fs.readFileSync(require.resolve('jquery'), 'utf8');
    const jqScript = window.document.createElement("script");
    jqScript.textContent = jqueryCode;
    window.document.head.appendChild(jqScript);
    $ = window.$;

    // Мокаем $.getJSON
    $.getJSON = jest.fn().mockImplementation((url, callback) => {
        let responseData = { data: [] };
        if (url.includes('/api/field/')) {
            responseData = { id: 1, name: "Test Field", area: "10 га", owner: "Jan", land_status: "A", parcel_number: "777", geometry: {type: "Point", coordinates: [0,0]} };
        }
        if (callback) callback(responseData);
        return {
            then: (successCb) => { if (successCb) successCb(responseData); return { fail: jest.fn() }; },
            fail: (failCb) => { return { then: jest.fn() }; }
        };
    });

    // Мокаем DataTables
    const dtMock = {
        on: jest.fn(),
        ajax: { reload: jest.fn() },
        row: jest.fn().mockReturnValue({ data: jest.fn().mockReturnValue({ id: 1, name: "Test" }) })
    };
    $.fn.DataTable = jest.fn().mockReturnValue(dtMock);
    window.fieldsTable = dtMock; // Чтобы setupTableEvents видел его

    const script = window.document.createElement("script");
    script.textContent = mainCode;
    window.document.head.appendChild(script);

    global.handleRoute = window.handleRoute;
    global.initTheme = window.initTheme;
    global.downloadKmzWithSettings = window.downloadKmzWithSettings;
    global.window = window;
    global.$ = $;
});

describe('Field Mapper Frontend Logic', () => {

    test('Routing: should switch views based on hash', () => {
        window.location.hash = '#fields';
        handleRoute();
        expect(window.document.getElementById('view-fields').style.display).not.toBe('none');
    });

    test('Routing: should show field detail view and load data', () => {
        window.location.hash = '#field/1';
        handleRoute();
        
        const detailSection = window.document.getElementById('view-field-detail');
        expect(detailSection.style.display).not.toBe('none');
        expect(window.document.getElementById('field-detail-name').textContent).toBe('Test Field');
    });

    test('Interaction: clicking on table cell should change hash', () => {
        window.location.hash = '#fields';
        handleRoute();
        
        const tbody = $('#fields-table tbody');
        const tr = $('<tr><td>Data</td></tr>');
        tbody.append(tr);
        
        tr.find('td').click();
        expect(window.location.hash).toBe('#field/1');
    });

    test('Theme: should toggle theme attributes', () => {
        initTheme();
        const html = window.document.documentElement;
        expect(html.getAttribute('data-theme')).toBe('light');
        $('#theme-toggle-btn').click();
        expect(html.getAttribute('data-theme')).toBe('dark');
    });
});
