/**
 * View: Список полей — DataTables с инлайн-редактированием.
 */
import { View } from "./view.js";
import { initFieldsTable, getFieldsTable } from "../tables.js";

export class FieldsView extends View {
  constructor() {
    super("view-fields", { navHref: "#fields" });
  }

  mount() {
    initFieldsTable();
  }

  update() {
    const table = getFieldsTable();
    if (table) table.ajax.reload(null, false);
  }

  unmount() {
    super.unmount();
  }

  /**
     * Принудительная перезагрузка таблицы (вызывается из других view).
     */
  reload() {
    const table = getFieldsTable();
    if (table) table.ajax.reload(null, false);
  }
}
