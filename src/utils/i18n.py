"""
Система локализации (i18n) для Field Mapper.
Поддерживает языки: русский (ru), английский (en), словацкий (sk).
"""
import json
import os
from typing import Optional
from typing import Any

# Переводы для всех поддерживаемых языков
TRANSLATIONS: dict[str, dict[str, str]] = {
    # Русский (по умолчанию)
    'ru': {
        # Навигация
        'nav.home': 'Главная',
        'nav.fields': 'Поля',
        'nav.owners': 'Владельцы',
        'nav.settings': 'Настройки',
        'nav.profile': 'Профиль',
        'nav.logout': 'Выйти',
        'nav.login': 'Войти',
        
        # Авторизация
        'auth.login': 'Вход',
        'auth.register': 'Регистрация',
        'auth.email': 'Email',
        'auth.password': 'Пароль',
        'auth.remember_me': 'Запомнить меня',
        'auth.forgot_password': 'Забыли пароль?',
        'auth.no_account': 'Нет аккаунта?',
        'auth.have_account': 'Уже есть аккаунт?',
        'auth.login_success': 'Успешный вход!',
        'auth.logout_success': 'Вы успешно вышли',
        'auth.invalid_credentials': 'Неверный email или пароль',
        'auth.registration_success': 'Регистрация успешна!',
        
        # Профиль
        'profile.title': 'Профиль',
        'profile.company': 'Компания',
        'profile.role': 'Роль',
        'profile.language': 'Язык',
        'profile.created_at': 'Дата регистрации',
        'profile.last_login': 'Последний вход',
        'profile.edit': 'Редактировать',
        'profile.save': 'Сохранить',
        'profile.update_success': 'Профиль обновлён',
        
        # Настройки
        'settings.title': 'Настройки',
        'settings.general': 'Общие',
        'settings.appearance': 'Внешний вид',
        'settings.notifications': 'Уведомления',
        'settings.dark_mode': 'Тёмная тема',
        'settings.language': 'Язык интерфейса',
        'settings.save': 'Сохранить',
        'settings.saved': 'Настройки сохранены',
        
        # Поля
        'fields.title': 'Поля',
        'fields.add': 'Добавить поле',
        'fields.edit': 'Редактировать',
        'fields.delete': 'Удалить',
        'fields.export': 'Экспорт',
        'fields.import': 'Импорт',
        'fields.name': 'Название',
        'fields.area': 'Площадь',
        'fields.owner': 'Владелец',
        'fields.created': 'Создано',
        'fields.actions': 'Действия',
        'fields.no_fields': 'Поля не найдены',
        'fields.confirm_delete': 'Вы уверены, что хотите удалить это поле?',
        
        # Сканы
        'scans.title': 'Сканы',
        'scans.upload': 'Загрузить скан',
        'scans.processing': 'Обработка...',
        'scans.processed': 'Обработан',
        'scans.pending': 'Ожидает',
        'scans.delete': 'Удалить скан',
        'scans.confirm_delete': 'Вы уверены, что хотите удалить этот скан?',
        
        # Зоны
        'zones.title': 'Зоны продуктивности',
        'zones.low': 'Низкая',
        'zones.medium': 'Средняя',
        'zones.high': 'Высокая',
        'zones.rate': 'Норма внесения',
        
        # Экспорт
        'export.title': 'Экспорт карт',
        'export.isoxml': 'ISOXML',
        'export.kmz': 'KMZ',
        'export.shapefile': 'Shapefile',
        'export.pdf': 'PDF',
        'export.generating': 'Генерация...',
        'export.download': 'Скачать',
        
        # Ошибки
        'error.title': 'Ошибка',
        'error.not_found': 'Не найдено',
        'error.server': 'Ошибка сервера',
        'error.network': 'Ошибка сети',
        'error.unauthorized': 'Не авторизован',
        'error.forbidden': 'Нет доступа',
        
        # Общее
        'common.save': 'Сохранить',
        'common.cancel': 'Отмена',
        'common.delete': 'Удалить',
        'common.edit': 'Редактировать',
        'common.add': 'Добавить',
        'common.close': 'Закрыть',
        'common.loading': 'Загрузка...',
        'common.success': 'Успешно',
        'common.error': 'Ошибка',
        'common.confirm': 'Подтвердить',
        'common.yes': 'Да',
        'common.no': 'Нет',
    },
    
    # English
    'en': {
        # Navigation
        'nav.home': 'Home',
        'nav.fields': 'Fields',
        'nav.owners': 'Owners',
        'nav.settings': 'Settings',
        'nav.profile': 'Profile',
        'nav.logout': 'Logout',
        'nav.login': 'Login',
        
        # Auth
        'auth.login': 'Login',
        'auth.register': 'Register',
        'auth.email': 'Email',
        'auth.password': 'Password',
        'auth.remember_me': 'Remember me',
        'auth.forgot_password': 'Forgot password?',
        'auth.no_account': 'No account?',
        'auth.have_account': 'Already have an account?',
        'auth.login_success': 'Login successful!',
        'auth.logout_success': 'You have been logged out',
        'auth.invalid_credentials': 'Invalid email or password',
        'auth.registration_success': 'Registration successful!',
        
        # Profile
        'profile.title': 'Profile',
        'profile.company': 'Company',
        'profile.role': 'Role',
        'profile.language': 'Language',
        'profile.created_at': 'Registration date',
        'profile.last_login': 'Last login',
        'profile.edit': 'Edit',
        'profile.save': 'Save',
        'profile.update_success': 'Profile updated',
        
        # Settings
        'settings.title': 'Settings',
        'settings.general': 'General',
        'settings.appearance': 'Appearance',
        'settings.notifications': 'Notifications',
        'settings.dark_mode': 'Dark mode',
        'settings.language': 'Interface language',
        'settings.save': 'Save',
        'settings.saved': 'Settings saved',
        
        # Fields
        'fields.title': 'Fields',
        'fields.add': 'Add field',
        'fields.edit': 'Edit',
        'fields.delete': 'Delete',
        'fields.export': 'Export',
        'fields.import': 'Import',
        'fields.name': 'Name',
        'fields.area': 'Area',
        'fields.owner': 'Owner',
        'fields.created': 'Created',
        'fields.actions': 'Actions',
        'fields.no_fields': 'No fields found',
        'fields.confirm_delete': 'Are you sure you want to delete this field?',
        
        # Scans
        'scans.title': 'Scans',
        'scans.upload': 'Upload scan',
        'scans.processing': 'Processing...',
        'scans.processed': 'Processed',
        'scans.pending': 'Pending',
        'scans.delete': 'Delete scan',
        'scans.confirm_delete': 'Are you sure you want to delete this scan?',
        
        # Zones
        'zones.title': 'Productivity zones',
        'zones.low': 'Low',
        'zones.medium': 'Medium',
        'zones.high': 'High',
        'zones.rate': 'Application rate',
        
        # Export
        'export.title': 'Export maps',
        'export.isoxml': 'ISOXML',
        'export.kmz': 'KMZ',
        'export.shapefile': 'Shapefile',
        'export.pdf': 'PDF',
        'export.generating': 'Generating...',
        'export.download': 'Download',
        
        # Errors
        'error.title': 'Error',
        'error.not_found': 'Not found',
        'error.server': 'Server error',
        'error.network': 'Network error',
        'error.unauthorized': 'Unauthorized',
        'error.forbidden': 'Forbidden',
        
        # Common
        'common.save': 'Save',
        'common.cancel': 'Cancel',
        'common.delete': 'Delete',
        'common.edit': 'Edit',
        'common.add': 'Add',
        'common.close': 'Close',
        'common.loading': 'Loading...',
        'common.success': 'Success',
        'common.error': 'Error',
        'common.confirm': 'Confirm',
        'common.yes': 'Yes',
        'common.no': 'No',
    },
    
    # Slovenčina
    'sk': {
        # Navigácia
        'nav.home': 'Domov',
        'nav.fields': 'Polia',
        'nav.owners': 'Vlastníci',
        'nav.settings': 'Nastavenia',
        'nav.profile': 'Profil',
        'nav.logout': 'Odhlásiť sa',
        'nav.login': 'Prihlásiť sa',
        
        # Autorizácia
        'auth.login': 'Prihlásenie',
        'auth.register': 'Registrácia',
        'auth.email': 'Email',
        'auth.password': 'Heslo',
        'auth.remember_me': 'Zapamätať si ma',
        'auth.forgot_password': 'Zabudli ste heslo?',
        'auth.no_account': 'Nemáte účet?',
        'auth.have_account': 'Už máte účet?',
        'auth.login_success': 'Prihlásenie úspešné!',
        'auth.logout_success': 'Boli ste odhlásení',
        'auth.invalid_credentials': 'Neplatný email alebo heslo',
        'auth.registration_success': 'Registrácia úspešná!',
        
        # Profil
        'profile.title': 'Profil',
        'profile.company': 'Spoločnosť',
        'profile.role': 'Rola',
        'profile.language': 'Jazyk',
        'profile.created_at': 'Dátum registrácie',
        'profile.last_login': 'Posledné prihlásenie',
        'profile.edit': 'Upraviť',
        'profile.save': 'Uložiť',
        'profile.update_success': 'Profil aktualizovaný',
        
        # Nastavenia
        'settings.title': 'Nastavenia',
        'settings.general': 'Všeobecné',
        'settings.appearance': 'Vzhľad',
        'settings.notifications': 'Upozornenia',
        'settings.dark_mode': 'Tmavý režim',
        'settings.language': 'Jazyk rozhrania',
        'settings.save': 'Uložiť',
        'settings.saved': 'Nastavenia uložené',
        
        # Polia
        'fields.title': 'Polia',
        'fields.add': 'Pridať pole',
        'fields.edit': 'Upraviť',
        'fields.delete': 'Odstrániť',
        'fields.export': 'Exportovať',
        'fields.import': 'Importovať',
        'fields.name': 'Názov',
        'fields.area': 'Plocha',
        'fields.owner': 'Vlastník',
        'fields.created': 'Vytvorené',
        'fields.actions': 'Akcie',
        'fields.no_fields': 'Nenašli sa žiadne polia',
        'fields.confirm_delete': 'Naozaj chcete odstrániť toto pole?',
        
        # Skény
        'scans.title': 'Skény',
        'scans.upload': 'Nahrať sken',
        'scans.processing': 'Spracovanie...',
        'scans.processed': 'Spracované',
        'scans.pending': 'Čaká sa',
        'scans.delete': 'Odstrániť sken',
        'scans.confirm_delete': 'Naozaj chcete odstrániť tento sken?',
        
        # Zóny
        'zones.title': 'Zóny produktivity',
        'zones.low': 'Nízka',
        'zones.medium': 'Stredná',
        'zones.high': 'Vysoká',
        'zones.rate': 'Miera aplikácie',
        
        # Export
        'export.title': 'Export máp',
        'export.isoxml': 'ISOXML',
        'export.kmz': 'KMZ',
        'export.shapefile': 'Shapefile',
        'export.pdf': 'PDF',
        'export.generating': 'Generovanie...',
        'export.download': 'Stiahnuť',
        
        # Chyby
        'error.title': 'Chyba',
        'error.not_found': 'Nenájdené',
        'error.server': 'Chyba servera',
        'error.network': 'Chyba siete',
        'error.unauthorized': 'Neoprávnený prístup',
        'error.forbidden': 'Prístup zamietnutý',
        
        # Bežné
        'common.save': 'Uložiť',
        'common.cancel': 'Zrušiť',
        'common.delete': 'Odstrániť',
        'common.edit': 'Upraviť',
        'common.add': 'Pridať',
        'common.close': 'Zavrieť',
        'common.loading': 'Načítavanie...',
        'common.success': 'Úspech',
        'common.error': 'Chyba',
        'common.confirm': 'Potvrdiť',
        'common.yes': 'Áno',
        'common.no': 'Nie',
    },
}


class I18n:
    """
    Класс для управления локализацией.
    """
    
    def __init__(self, default_language: str = 'ru'):
        """
        Инициализирует систему локализации.
        
        Args:
            default_language: Язык по умолчанию
        """
        self.default_language = default_language
        self.translations = TRANSLATIONS
    
    def t(self, key: str, language: Optional[str] = None) -> str:
        """
        Переводит строку на указанный язык.
        
        Args:
            key: Ключ перевода (например, 'nav.home')
            language: Код языка (ru/en/sk). Если None, используется язык по умолчанию.
            
        Returns:
            Переведённая строка или ключ, если перевод не найден
        """
        lang = language or self.default_language
        
        # Проверяем наличие языка и ключа
        if lang not in self.translations:
            lang = self.default_language
        
        return self.translations[lang].get(key, key)
    
    def get_supported_languages(self) -> list[dict[str, str]]:
        """
        Возвращает список поддерживаемых языков.
        
        Returns:
            Список словарей с кодом и названием языка
        """
        return [
            {'code': 'ru', 'name': 'Русский', 'native': 'Русский'},
            {'code': 'en', 'name': 'English', 'native': 'English'},
            {'code': 'sk', 'name': 'Slovak', 'native': 'Slovenčina'},
        ]
    
    def to_json(self) -> str:
        """
        Экспортирует все переводы в JSON формат.
        
        Returns:
            JSON строка со всеми переводами
        """
        return json.dumps({
            'languages': self.get_supported_languages(),
            'translations': self.translations,
        }, ensure_ascii=False, indent=2)


# Глобальный экземпляр
i18n = I18n()


def t(key: str, language: Optional[str] = None) -> str:
    """
    Удобная функция для перевода.
    
    Args:
        key: Ключ перевода
        language: Код языка
        
    Returns:
        Переведённая строка
    """
    return i18n.t(key, language)
