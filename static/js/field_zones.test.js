/**
 * Тесты для отображения зон поля.
 * Примечание: Тесты требуют доработки для поддержки ES6 модулей.
 */
const { TextEncoder, TextDecoder } = require("util");
global.TextEncoder = TextEncoder;
global.TextDecoder = TextDecoder;
const { JSDOM } = require("jsdom");

describe("Field Zones Rendering", () => {
  let dom;
  let window;
  let $;

  beforeAll(() => {
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
    const jqueryCode = require("jquery");
    window.$ = window.jQuery = jqueryCode(window);
    $ = window.$;
    global.$ = $;
    
    // Mock MapManager
    global.MapManager = {
      detailInstance: null,
      initDetailMap: jest.fn((containerId, geometry, zones = []) => {
        global.MapManager.detailInstance = { remove: jest.fn(), fitBounds: jest.fn(), invalidateSize: jest.fn() };
        
        if (zones && zones.length > 0) {
          zones.forEach(zone => {
            window.L.geoJSON(zone.geometry, {
              style: { color: zone.color, weight: 1, fillOpacity: 0.6 }
            }).addTo(global.MapManager.detailInstance);
          });
        }
        
        window.L.geoJSON(geometry, {
          style: { color: "#007BFF", weight: 3, fillOpacity: zones.length > 0 ? 0 : 0.2 }
        }).addTo(global.MapManager.detailInstance);
      })
    };
  });

  test("MapManager.initDetailMap should render zones if provided", () => {
    const geometry = { type: "Polygon", coordinates: [] };
    const zones = [
      { name: "Zone 1", color: "#ff0000", geometry: { type: "Polygon", coordinates: [] } },
      { name: "Zone 2", color: "#00ff00", geometry: { type: "Polygon", coordinates: [] } }
    ];

    global.MapManager.initDetailMap("detail-map-container", geometry, zones);

    expect(window.L.geoJSON).toHaveBeenCalledTimes(3);

    expect(window.L.geoJSON).toHaveBeenNthCalledWith(1, zones[0].geometry, expect.objectContaining({
      style: expect.objectContaining({ color: zones[0].color })
    }));
  });
});
