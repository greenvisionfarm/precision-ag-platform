/**
 * Утилиты и вспомогательные функции.
 */

/**
 * Показывает уведомление пользователю.
 * @param {string} message - Текст сообщения.
 * @param {'success'|'error'|'info'|'warning'} type - Тип уведомления.
 */
export function showMessage(message, type = 'info') {
  const icons = {
    success: 'success',
    error: 'error',
    info: 'info',
    warning: 'warning'
  };

  Swal.fire({
    toast: true,
    position: 'top-end',
    icon: icons[type] || 'info',
    title: message,
    showConfirmButton: false,
    timer: 3000,
    timerProgressBar: true
  });
}

/**
 * Показывает диалог подтверждения.
 * @param {string} title - Заголовок диалога.
 * @param {string} confirmText - Текст кнопки подтверждения.
 * @param {string} cancelText - Текст кнопки отмены.
 * @returns {Promise<boolean>} true если подтверждено.
 */
export function showConfirm(title, confirmText = 'Yes', cancelText = 'No') {
  return Swal.fire({
    title: title,
    icon: 'warning',
    showCancelButton: true,
    confirmButtonText: confirmText,
    cancelButtonText: cancelText,
    reverseButtons: true
  }).then(result => result.isConfirmed);
}

/**
 * Форматирует площадь в зависимости от значения.
 * @param {number} areaSqMeters - Площадь в квадратных метрах.
 * @returns {string} Форматированная строка.
 */
export function formatArea(areaSqMeters) {
  if (areaSqMeters >= 10000) {
    return `${(areaSqMeters / 10000).toFixed(2)} га`;
  }
  return `${Math.round(areaSqMeters)} м²`;
}
