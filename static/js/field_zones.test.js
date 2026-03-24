const fs = require("fs");
const path = require("path");
const { TextEncoder, TextDecoder } = require("util");
global.TextEncoder = TextEncoder;
global.TextDecoder = TextDecoder;
const { JSDOM } = require("jsdom");

describe("Field Zones Rendering", () => {
  let dom;
  let window;
  let $;
  let MapManager;

  beforeAll(() => {
    const mapCode = fs.readFileSync(path.resolve(__dirname, "modules/map_manager.js"), "utf8");

    dom = new JSDOM(`
            <!DOCTYPE html>
            <html>
            <body>
                <div id="detail-map-container" style="height: 100px;"></div>
            </body>
            </html>
        `, { url: "http://localhost/", runScripts: "dangerously" });

    window = dom.window;
    global.window = window;
    global.document = window.document;

    // Mock Leaflet
    const layerMock = {
      addTo: jest.fn().mockReturnThis(),
      getBounds: jest.fn().mockReturnValue({
        isValid: () => true,
        getSouthWest: () => ({lat: 0, lng: 0}),
        getNorthEast: () => ({lat: 1, lng: 1})
      })
    };

    window.L = {
      map: jest.fn().mockReturnValue({
        setView: jest.fn().mockReturnThis(),
        addLayer: jest.fn(),
        remove: jest.fn(),
        fitBounds: jest.fn(),
        invalidateSize: jest.fn()
      }),
      tileLayer: jest.fn().mockReturnValue({ addTo: jest.fn() }),
      geoJSON: jest.fn().mockReturnValue(layerMock),
      DomEvent: { stopPropagation: jest.fn() }
    };

    // Mock jQuery
    const jqueryCode = fs.readFileSync(require.resolve("jquery"), "utf8");
    const jqScript = window.document.createElement("script");
    jqScript.textContent = jqueryCode;
    window.document.head.appendChild(jqScript);
    $ = window.$;
    global.$ = $;

    const mapScript = window.document.createElement("script");
    mapScript.textContent = mapCode;
    window.document.head.appendChild(mapScript);

    MapManager = window.MapManager;
  });

  test("MapManager.initDetailMap should render zones if provided", () => {
    const geometry = { type: "Polygon", coordinates: [] };
    const zones = [
      { name: "Zone 1", color: "#ff0000", geometry: { type: "Polygon", coordinates: [] } },
      { name: "Zone 2", color: "#00ff00", geometry: { type: "Polygon", coordinates: [] } }
    ];

    MapManager.initDetailMap("detail-map-container", geometry, zones);

    // Проверяем, что L.geoJSON был вызван для каждой зоны + 1 раз для основного контура
    // Итого 3 вызова
    expect(window.L.geoJSON).toHaveBeenCalledTimes(3);
        
    // Первый вызов должен быть для первой зоны
    expect(window.L.geoJSON).toHaveBeenNthCalledWith(1, zones[0].geometry, expect.objectContaining({
      style: expect.objectContaining({ color: zones[0].color })
    }));
  });
});
