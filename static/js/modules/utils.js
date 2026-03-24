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
