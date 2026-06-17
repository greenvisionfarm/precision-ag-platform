/**
 * View: Владельцы — таблица владельцев.
 */
import { View } from "./view.js";
import { initOwnersTable, getOwnersTable } from "../tables.js";

export class OwnersView extends View {
  constructor() {
    super("view-owners", { navHref: "#owners" });
  }

  mount() {
    initOwnersTable();
  }

  update() {
    const table = getOwnersTable();
    if (table) table.ajax.reload(null, false);
  }

  unmount() {
    super.unmount();
  }
}
