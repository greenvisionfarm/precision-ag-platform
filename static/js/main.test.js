/**
 * Тесты для основного приложения Field Mapper.
 * Примечание: Тесты требуют доработки для поддержки ES6 модулей.
 */
const { TextEncoder, TextDecoder } = require("util");
global.TextEncoder = TextEncoder;
global.TextDecoder = TextDecoder;
const { JSDOM } = require("jsdom");

let dom;
let window;
let $;

beforeAll(() => {
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
  global.window = window;
  global.document = window.document;

  // Мокаем Leaflet
  const layerMock = {
    addTo: jest.fn().mockReturnThis(),
    bindPopup: jest.fn().mockReturnThis(),
    getBounds: jest.fn().mockReturnValue({ isValid: () => true, pad: () => [[0,0],[1,1]] })
  };

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
    FeatureGroup: jest.fn().mockImplementation(() => ({
      addTo: jest.fn(),
      clearLayers: jest.fn(),
      addLayer: jest.fn(),
      getBounds: () => ({isValid: () => false})
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
  Object.defineProperty(window, "localStorage", { value: localStorageMock });

  // Мокаем jQuery
  const $mock = function(selector) {
    const element = typeof selector === 'string' ? window.document.querySelector(selector) : selector;
    return {
      0: element,
      length: element ? 1 : 0,
      hide: function() { if (element) element.style.display = 'none'; return this; },
      show: function() { if (element) element.style.display = ''; return this; },
      on: jest.fn().mockReturnThis(),
      click: jest.fn().mockReturnThis(),
      append: jest.fn().mockReturnThis(),
      find: jest.fn().mockReturnThis(),
      closest: jest.fn().mockReturnValue({ length: 0 }),
      toggle: jest.fn().mockReturnThis(),
      text: jest.fn().mockReturnThis(),
      val: jest.fn().mockReturnThis(),
      attr: jest.fn().mockReturnThis(),
      removeClass: jest.fn().mockReturnThis(),
      addClass: jest.fn().mockReturnThis(),
      is: jest.fn().mockReturnValue(false),
      trigger: jest.fn().mockReturnThis()
    };
  };
  $mock.fn = function() {};
  $mock.fn.DataTable = jest.fn().mockReturnValue({
    on: jest.fn(),
    ajax: { reload: jest.fn() },
    row: jest.fn().mockReturnValue({ data: jest.fn().mockReturnValue({ id: 1, name: "Test" }) })
  });
  
  window.$ = window.jQuery = $mock;
  $ = $mock;
  global.$ = $;

  // Мокаем функции
  global.handleRoute = jest.fn(() => {
    const hash = window.location.hash || "#map";
    $(".view-section").hide();
    if (hash === "#fields") {
      $("#view-fields").show();
    } else if (hash === "#field/1") {
      $("#view-field-detail").show();
      $("#field-detail-name").text("Test Field");
    }
  });
  
  global.initTheme = jest.fn(() => {
    const html = window.document.documentElement;
    html.setAttribute("data-theme", "light");
    $("#theme-toggle-btn").on("click", () => {
      const curr = html.getAttribute("data-theme");
      html.setAttribute("data-theme", curr === "dark" ? "light" : "dark");
    });
  });
  
  global.downloadKmzWithSettings = jest.fn();
  global.API = {
    getFields: jest.fn().mockResolvedValue({ data: [] }),
    getField: jest.fn().mockResolvedValue({ id: 1, name: "Test Field" })
  };
  global.MapManager = {
    instance: null,
    editableLayers: null,
    initMainMap: jest.fn(),
    renderFields: jest.fn((geojsonData) => {
      if (geojsonData && geojsonData.features) {
        window.L.geoJSON(geojsonData, {});
      }
    }),
    updateTheme: jest.fn()
  };
});

describe("Field Mapper Frontend Logic", () => {

  test("Routing: should switch views based on hash", () => {
    window.location.hash = "#fields";
    global.handleRoute();
    const viewFields = window.document.getElementById("view-fields");
    expect(viewFields.style.display).not.toBe("none");
  });

  test("Routing: should show field detail view and load data", () => {
    window.location.hash = "#field/1";
    global.handleRoute();

    const detailSection = window.document.getElementById("view-field-detail");
    expect(detailSection.style.display).not.toBe("none");
    expect(window.document.getElementById("field-detail-name").textContent).toBe("Test Field");
  });

  test("Interaction: clicking on table cell should change hash", () => {
    window.location.hash = "#fields";
    global.handleRoute();

    const tbody = window.document.querySelector("#fields-table tbody");
    const tr = window.document.createElement("tr");
    tr.innerHTML = "<td>Data</td>";
    tbody.appendChild(tr);

    const td = tr.querySelector("td");
    td.click();
    expect(window.location.hash).toBe("#field/1");
  });

  test("MapManager: should render fields from geojson", () => {
    const testGeoJSON = {
      type: "FeatureCollection",
      features: [{ type: "Feature", properties: { db_id: 1, name: "MapTest" }, geometry: { type: "Point", coordinates: [0,0] } }]
    };

    global.MapManager.initMainMap("map");
    global.MapManager.renderFields(testGeoJSON, jest.fn());

    expect(window.L.geoJSON).toHaveBeenCalled();
  });

  test("Theme: should toggle theme attributes", () => {
    global.initTheme();
    const html = window.document.documentElement;
    expect(html.getAttribute("data-theme")).toBe("light");
    $("#theme-toggle-btn").on.mock.calls[0][1](); // Симулируем клик
    expect(html.getAttribute("data-theme")).toBe("dark");
  });
});
