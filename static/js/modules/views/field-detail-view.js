/**
 * View: Детали поля — обёртка над field-detail.js с lifecycle.
 * Полный разбив на подмодули будет в T3.4.
 */
import { View } from "./view.js";
import { showFieldDetail as _showFieldDetail } from "../field-detail.js";

export class FieldDetailView extends View {
  constructor() {
    super("view-field-detail", { navHref: "#fields" });
  }

  mount(params) {
    this._fieldId = params.id;
    if (this._fieldId) {
      _showFieldDetail(this._fieldId);
    }
  }

  update(params) {
    const newId = params.id;
    if (newId && newId !== this._fieldId) {
      this._fieldId = newId;
      _showFieldDetail(newId);
    }
  }

  unmount() {
    // Очищаем polling если был запущен
    // ( field-detail.js хранит processingPollInterval в замыкании,
    //   полная очистка будет после разбиения на подмодули )
    this._fieldId = null;
    super.unmount();
  }
}
