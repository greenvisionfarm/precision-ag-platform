/**
 * Journal — журнал операций на поле.
 */
import { showMessage } from "./utils.js";

const CROP_LABELS = {
  wheat: "Пшеница", corn: "Кукуруза", sunflower: "Подсолнечник",
  soybean: "Соя", barley: "Ячмень", rapeseed: "Рапс",
  sugar_beet: "Сахарная свекла", potato: "Картофель", other: "Другое"
};

export function loadJournal(fieldId) {
  $.getJSON(`/api/field/${fieldId}/journal`).then(data => {
    const entries = data.entries || [];
    if (entries.length === 0) {
      $("#journal-entries").hide();
      $("#journal-empty").show();
      return;
    }
    $("#journal-empty").hide();
    $("#journal-entries").show();
    const $tbody = $("#journal-table-body").empty();
    entries.forEach(e => {
      const crop = CROP_LABELS[e.crop_type] || e.crop_type || "-";
      const plant = e.planting_date ? new Date(e.planting_date).toLocaleDateString("ru-RU") : "-";
      const product = e.product_name || "-";
      const rate = e.application_rate ? `${e.application_rate} кг/га` : "-";
      const yld = e.yield_amount ? `${e.yield_amount} ц/га` : "-";
      $tbody.append(`
        <tr>
          <td>${crop}${e.crop_variety ? " (" + e.crop_variety + ")" : ""}</td>
          <td>${plant}</td>
          <td>${product}</td>
          <td>${rate}</td>
          <td>${yld}</td>
          <td><button class="btn btn-sm btn-danger" onclick="deleteJournalEntry(${fieldId}, ${e.id})" title="Удалить"><i class="fas fa-trash"></i></button></td>
        </tr>
      `);
    });
  });
}

export function deleteJournalEntry(fieldId, entryId) {
  if (!confirm("Удалить запись журнала?")) return;
  $.ajax({ url: `/api/field/${fieldId}/journal/${entryId}`, type: "DELETE" })
    .then(() => { loadJournal(fieldId); showMessage("Запись удалена", "success"); });
}

export function initJournalAddHandler(getFieldId) {
  $(document).on("click", "#journal-add-btn", function() {
    const fieldId = getFieldId();
    if (!fieldId) return;

    Swal.fire({
      title: "Новая запись журнала",
      html: `
        <div class="kmz-settings-grid" style="text-align:left;">
          <div class="kmz-field">
            <label>Культура:</label>
            <select id="j-crop-type" class="swal2-select">
              <option value="wheat">Пшеница</option>
              <option value="corn">Кукуруза</option>
              <option value="sunflower">Подсолнечник</option>
              <option value="soybean">Соя</option>
              <option value="barley">Ячмень</option>
              <option value="rapeseed">Рапс</option>
              <option value="sugar_beet">Сахарная свекла</option>
              <option value="potato">Картофель</option>
              <option value="other">Другое</option>
            </select>
          </div>
          <div class="kmz-field">
            <label>Сорт:</label>
            <input type="text" id="j-crop-variety" class="swal2-input" placeholder="Не обязательно">
          </div>
          <div class="kmz-field">
            <label>Дата посадки:</label>
            <input type="date" id="j-planting-date" class="swal2-input">
          </div>
          <div class="kmz-field">
            <label>Дата уборки:</label>
            <input type="date" id="j-harvest-date" class="swal2-input">
          </div>
          <div class="kmz-field">
            <label>Продукт (удобрение):</label>
            <input type="text" id="j-product-name" class="swal2-input" placeholder="Напр. Аммиачная селитра">
          </div>
          <div class="kmz-field">
            <label>Норма (кг/га):</label>
            <input type="number" id="j-application-rate" class="swal2-input" placeholder="200">
          </div>
          <div class="kmz-field">
            <label>Урожайность (ц/га):</label>
            <input type="number" id="j-yield" class="swal2-input" placeholder="Опционально">
          </div>
          <div class="kmz-field" style="grid-column: span 2;">
            <label>Заметки:</label>
            <textarea id="j-notes" class="swal2-textarea" rows="2" placeholder="Дополнительная информация"></textarea>
          </div>
        </div>`,
      width: "700px",
      focusConfirm: false,
      preConfirm: () => {
        const crop = document.getElementById("j-crop-type").value;
        if (!crop) { Swal.showValidationMessage("Выберите культуру"); return false; }
        return {
          crop_type: crop,
          crop_variety: document.getElementById("j-crop-variety").value || null,
          planting_date: document.getElementById("j-planting-date").value || null,
          harvest_date: document.getElementById("j-harvest-date").value || null,
          product_name: document.getElementById("j-product-name").value || null,
          application_rate: parseFloat(document.getElementById("j-application-rate").value) || null,
          yield_amount: parseFloat(document.getElementById("j-yield").value) || null,
          notes: document.getElementById("j-notes").value || null,
        };
      }
    }).then(res => {
      if (!res.isConfirmed) return;
      $.ajax({
        url: `/api/field/${fieldId}/journal/add`,
        type: "POST",
        contentType: "application/json",
        data: JSON.stringify(res.value)
      }).then(() => {
        loadJournal(fieldId);
        showMessage("Запись добавлена", "success");
      });
    });
  });
}
