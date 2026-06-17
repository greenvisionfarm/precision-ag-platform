/**
 * View: Загрузки — формы загрузки файлов.
 */
import { View } from "./view.js";
import { initShapefileUpload, initRasterUpload, initDroneUpload } from "../uploads.js";

export class UploadsView extends View {
  constructor() {
    super("view-uploads", { navHref: "#uploads" });
    this._initialized = false;
  }

  mount() {
    if (!this._initialized) {
      initShapefileUpload();
      initRasterUpload();
      initDroneUpload();
      this._initialized = true;
    }
  }

  update() {
    // Формы уже инициализированы, ничего не нужно
  }

  unmount() {
    super.unmount();
  }
}
