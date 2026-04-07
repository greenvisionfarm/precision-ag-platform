/**
 * Инициализация и управление таблицами (DataTables).
 */
import { openFieldModal } from './modals.js';
import { showMessage } from './utils.js';
import API from './api.js';

let ownersList = [];
let fieldsTable = null;
let ownersTable = null;

/**
 * Инициализирует таблицу полей.
 */
export function initFieldsTable() {
  // Не загружаем данные если пользователь не авторизован
  if (!window.AuthModule?.isLoggedIn()) {
    return;
  }

  API.getOwners().then(res => {
    ownersList = res.data;
    if (fieldsTable) {
      fieldsTable.ajax.reload();
      return;
    }

    fieldsTable = $("#fields-table").DataTable({
      ajax: {
        url: "/api/fields_data",
        error: function(xhr, error, thrown) {
          // Если 401 — значит сессия истекла, предлагаем войти
          if (xhr.status === 401) {
            window.AuthModule?.openLogin();
          }
        }
      },
      columns: [
        { data: "id" },
        { 
          data: "name", 
          render: (d, t, r) => `<span class="editable-name" data-id="${r.id}">${d}</span>` 
        },
        { data: "area" },
        { 
          data: "owner_id", 
          render: (d, t, r) => {
            let opts = "<option value=\"\">Не назначен</option>";
            ownersList.forEach(o => { 
              opts += `<option value="${o.id}" ${o.id == d ? "selected" : ""}>${o.name}</option>`; 
            });
            return `<select class="owner-select" data-id="${r.id}">${opts}</select>`;
          }
        },
        { 
          data: "land_status", 
          render: (d, t, r) => {
            let opts = "<option value=\"\">Не указан</option>";
            ["Собственность", "Аренда", "Субаренда"].forEach(s => { 
              opts += `<option value="${s}" ${s === d ? "selected" : ""}>${s}</option>`; 
            });
            return `<select class="status-select" data-id="${r.id}">${opts}</select>`;
          }
        },
        { 
          data: "parcel_number", 
          render: (d, t, r) => `<span class="editable-parcel" data-id="${r.id}">${d || "N/A"}</span>` 
        },
        { 
          data: null, 
          render: (d, t, r) => `<div class="btn-group">
            <button onclick="window.downloadKmzWithSettings(${r.id})" class="btn btn-outline-primary btn-sm"><i class="fas fa-cog"></i></button>
            <button class="btn-save-details btn-success btn-sm" data-id="${r.id}" style="display:none;"><i class="fas fa-save"></i></button>
            <button class="btn-delete btn-danger btn-sm" data-id="${r.id}"><i class="fas fa-trash"></i></button>
          </div>` 
        }
      ],
      language: {
        "processing": "Подождите...",
        "search": "Поиск:",
        "lengthMenu": "Показать _MENU_ записей",
        "info": "Записи с _START_ до _END_ из _TOTAL_ записей",
        "infoEmpty": "Записи с 0 до 0 из 0 записей",
        "infoFiltered": "(отфильтровано из _MAX_ записей)",
        "loadingRecords": "Загрузка записей...",
        "zeroRecords": "Записи отсутствуют.",
        "emptyTable": "В таблице отсутствуют данные",
        "paginate": {
          "first": "Первая",
          "previous": "Предыдущая",
          "next": "Следующая",
          "last": "Последняя"
        },
        "aria": {
          "sortAscending": ": активировать для сортировки столбца по возрастанию",
          "sortDescending": ": активировать для сортировки столбца по убыванию"
        }
      }
    });
    
    setupTableEvents();
  });
}

/**
 * Настраивает события таблицы полей.
 */
function setupTableEvents() {
  const tb = $("#fields-table tbody");
  
  tb.on("click", "td", function(e) {
    if ($(e.target).closest(".btn-group, select, input, .editable-name, .editable-parcel").length) return;
    const r = fieldsTable.row($(this).closest("tr")).data();
    if (r?.id) {
      openFieldModal(r.id);
    }
  });
  
  tb.on("change", ".owner-select, .status-select", function() {
    $(this).closest("tr").find(".btn-save-details").show();
  });
  
  tb.on("click", ".btn-save-details", function() {
    const b = $(this); 
    const id = b.data("id"); 
    const r = b.closest("tr");
    
    window.API.updateField(id, "assign_owner", { 
      owner_id: r.find(".owner-select").val() 
    });
    
    window.API.updateField(id, "update_details", { 
      land_status: r.find(".status-select").val(), 
      parcel_number: r.find(".editable-parcel").text() 
    }).then(() => b.hide());
  });
  
  tb.on("click", ".editable-name", function() {
    const s = $(this); 
    if (s.find("input").length) return;
    
    const i = $("<input>").val(s.text()); 
    s.html(i);
    
    i.focus().on("blur keypress", function(e) {
      if (e.type === "keypress" && e.which !== 13) return;
      const n = $(this).val();
      
      window.API.updateField(s.data("id"), "rename", { new_name: n }).then(() => { 
        s.text(n); 
        fieldsTable.ajax.reload(null, false); 
      });
    });
  });
  
  tb.on("click", ".btn-delete", function() {
    const id = $(this).data("id");
    Swal.fire({ title: "Удалить?", icon: "warning", showCancelButton: true }).then(r => {
      if (r.isConfirmed) {
        window.API.deleteField(id).then(() => { 
          fieldsTable.ajax.reload(null, false); 
          window.loadMapData?.();
        });
      }
    });
  });
}

/**
 * Инициализирует таблицу владельцев.
 */
export function initOwnersTable() {
  if (ownersTable) { 
    ownersTable.ajax.reload(); 
    return; 
  }
  
  ownersTable = $("#owners-table").DataTable({
    ajax: "/api/owners",
    columns: [ 
      { data: "id" }, 
      { data: "name" }, 
      { 
        data: null, 
        render: (d, t, r) => `<button class="btn btn-danger btn-sm btn-delete-owner" data-id="${r.id}"><i class="fas fa-trash"></i></button>` 
      } 
    ],
    language: {
      processing: "Обработка...",
      search: "Поиск:",
      lengthMenu: "Показать _MENU_ записей",
      info: "Записи с _START_ до _END_ из _TOTAL_",
      infoEmpty: "Нет записей",
      infoFiltered: "(отфильтровано из _MAX_)",
      loadingRecords: "Загрузка...",
      zeroRecords: "Ничего не найдено",
      emptyTable: "В таблице отсутствуют данные",
      paginate: { first: "Первая", previous: "Предыдущая", next: "Следующая", last: "Последняя" },
      aria: { sortAscending: ": активировать для сортировки столбца по возрастанию", sortDescending: ": активировать для сортировки столбца по убыванию" }
    }
  });
  
  $("#owners-table tbody").on("click", ".btn-delete-owner", function() {
    const id = $(this).data("id");
    Swal.fire({ title: "Удалить?", icon: "warning", showCancelButton: true }).then(r => {
      if (r.isConfirmed) {
        window.API.deleteOwner(id).then(() => { 
          ownersTable.ajax.reload(); 
          fieldsTable?.ajax.reload(); 
        });
      }
    });
  });
  
  $("#add-owner-form").on("submit", function(e) {
    e.preventDefault();
    window.API.addOwner($("#owner-name").val()).then(() => { 
      $("#owner-name").val(""); 
      ownersTable.ajax.reload(); 
    });
  });
}

/**
 * Возвращает текущий список владельцев.
 * @returns {Array} Список владельцев.
 */
export function getOwnersList() {
  return ownersList;
}

/**
 * Возвращает экземпляр таблицы полей.
 * @returns {DataTables.Api|null} Экземпляр DataTables.
 */
export function getFieldsTable() {
  return fieldsTable;
}

/**
 * Возвращает экземпляр таблицы владельцев.
 * @returns {DataTables.Api|null} Экземпляр DataTables.
 */
export function getOwnersTable() {
  return ownersTable;
}
