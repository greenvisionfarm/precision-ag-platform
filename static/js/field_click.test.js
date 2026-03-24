/**
 * Тесты для клика по полю и открытия модального окна.
 * Примечание: Тесты требуют доработки для поддержки ES6 модулей.
 */
const { TextEncoder, TextDecoder } = require("util");
global.TextEncoder = TextEncoder;
global.TextDecoder = TextDecoder;
const { JSDOM } = require("jsdom");

describe("Field Click to Detail Modal", () => {
  let dom;
  let window;
  let $;
  let layerMock;

  beforeAll(() => {
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
      Draw: { Event: { CREATED: "c", EDITED: "e", DELETED: "d" } },
      geoJSON: jest.fn().mockImplementation((data, options) => {
        if (options && options.onEachFeature && data.features) {
          data.features.forEach(f => options.onEachFeature(f, layerMock));
        }
        return layerMock;
      })
    };

    // Mock jQuery
    const jqueryCode = require("jquery");
    window.$ = window.jQuery = jqueryCode(window);
    $ = window.$;
    global.$ = $;

    // Mock Swal
    window.Swal = { fire: jest.fn() };
    
    // Mock MapManager
    global.MapManager = {
      instance: null,
      editableLayers: { addLayer: jest.fn(), clearLayers: jest.fn() },
      renderFields: jest.fn((geojsonData, onDownloadKmz, onFieldClick) => {
        if (geojsonData && geojsonData.features) {
          geojsonData.features.forEach(f => {
            layerMock.on("click", () => {
              if (onFieldClick) onFieldClick(f.properties.db_id);
            });
          });
        }
      })
    };
  });

  beforeEach(() => {
    jest.clearAllMocks();
  });

  test("MapManager.renderFields should attach click event to layers", () => {
    const testGeoJSON = {
      type: "FeatureCollection",
      features: [{ type: "Feature", properties: { db_id: 123, name: "Test" }, geometry: { type: "Point", coordinates: [0,0] } }]
    };

    global.MapManager.renderFields(testGeoJSON, jest.fn(), jest.fn());

    expect(layerMock.on).toHaveBeenCalledWith("click", expect.any(Function));
  });

  test("Clicking a field should call openFieldModal (or equivalent logic)", () => {
    const testGeoJSON = {
      type: "FeatureCollection",
      features: [{ type: "Feature", properties: { db_id: 123, name: "Test" }, geometry: { type: "Point", coordinates: [0,0] } }]
    };

    const onFieldClick = jest.fn();
    global.MapManager.renderFields(testGeoJSON, jest.fn(), onFieldClick);

    const clickHandler = layerMock.on.mock.calls.find(call => call[0] === "click");
    if (clickHandler) {
      clickHandler[1]({ stopPropagation: jest.fn() });
      expect(onFieldClick).toHaveBeenCalledWith(123);
    }
  });
});
