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
            <div id="view-fields" class="view-section" style="display: none;"></div>
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
    window.L = { 
        map: jest.fn().mockReturnValue({ 
            setView: jest.fn().mockReturnThis(), 
            addLayer: jest.fn(), 
            addControl: jest.fn(), 
            on: jest.fn(), 
            locate: jest.fn(), 
            invalidateSize: jest.fn(),
            removeLayer: jest.fn()
        }),
        tileLayer: jest.fn().mockReturnValue({ addTo: jest.fn() }),
        FeatureGroup: jest.fn().mockImplementation(() => ({ addTo: jest.fn(), clearLayers: jest.fn() })),
        Control: { Draw: jest.fn() },
        Draw: { Event: { CREATED: 'c', EDITED: 'e', DELETED: 'd' } },
        geoJSON: jest.fn()
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

    test('Theme: should toggle theme attributes', () => {
        initTheme();
        const html = window.document.documentElement;
        expect(html.getAttribute('data-theme')).toBe('light');
        $('#theme-toggle-btn').click();
        expect(html.getAttribute('data-theme')).toBe('dark');
    });

    test('DJI Export: should trigger SweetAlert2 dialog', () => {
        downloadKmzWithSettings(1);
        expect(window.Swal.fire).toHaveBeenCalled();
    });
});
