/**
 * View: Карта — главная карта с полями.
 */
import { View } from "../view.js";
import { loadMapData } from "../map-callbacks.js";

export class MapView extends View {
  constructor() {
    super("view-map", { navHref: "#map" });
  }

  mount() {
    // Карта уже инициализирована в main.js через MapManager
    // Здесь только загружаем данные
    this._invalidate();
    this._loadData();
  }

  update() {
    this._invalidate();
  }

  _invalidate() {
    // Даём Leaflet пересчитать размер после show
    setTimeout(() => {
      if (window.MapManager?.instance) {
        window.MapManager.instance.invalidateSize();
      }
    }, 50);
  }

  _loadData() {
    loadMapData();
  }
}
