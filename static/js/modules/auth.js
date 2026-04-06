/**
 * Модуль аутентификации и управления пользователем.
 * Обрабатывает вход, регистрацию, logout и настройки профиля.
 */

const AuthModule = (function() {
    'use strict';

    // Состояние
    let currentUser = null;
    let currentLanguage = 'ru';

    // DOM элементы
    let loginModal, registerModal, settingsModal;
    let loginForm, registerForm, profileForm;

    /**
     * Инициализация модуля
     */
    function init() {
        // Создаём модальные окна
        createModals();
        
        // Загружаем данные пользователя
        loadCurrentUser();
        
        // Навешиваем обработчики
        setupEventListeners();
    }

    /**
     * Создаёт HTML модальных окон
     */
    function createModals() {
        // Login Modal
        loginModal = document.createElement('div');
        loginModal.className = 'modal-overlay';
        loginModal.id = 'login-modal';
        loginModal.innerHTML = `
            <div class="modal">
                <div class="modal-header">
                    <h2 data-i18n="auth.login">Вход</h2>
                    <button class="modal-close" onclick="AuthModule.closeLogin()">&times;</button>
                </div>
                <div id="login-alert" class="alert"></div>
                <form id="login-form" class="auth-form">
                    <div class="form-group">
                        <label for="login-email" data-i18n="auth.email">Email</label>
                        <input type="email" id="login-email" name="email" required>
                    </div>
                    <div class="form-group">
                        <label for="login-password" data-i18n="auth.password">Пароль</label>
                        <input type="password" id="login-password" name="password" required>
                    </div>
                    <div class="form-options">
                        <label class="checkbox-label">
                            <input type="checkbox" name="remember">
                            <span data-i18n="auth.remember_me">Запомнить меня</span>
                        </label>
                        <a href="#" class="forgot-password" data-i18n="auth.forgot_password">Забыли пароль?</a>
                    </div>
                    <button type="submit" class="btn btn-primary btn-block" data-i18n="auth.login">Войти</button>
                </form>
                <div class="auth-switch">
                    <span data-i18n="auth.no_account">Нет аккаунта?</span>
                    <a href="#" onclick="AuthModule.openRegister()"><span data-i18n="auth.register">Регистрация</span></a>
                </div>
            </div>
        `;
        document.body.appendChild(loginModal);

        // Register Modal
        registerModal = document.createElement('div');
        registerModal.className = 'modal-overlay';
        registerModal.id = 'register-modal';
        registerModal.innerHTML = `
            <div class="modal">
                <div class="modal-header">
                    <h2 data-i18n="auth.register">Регистрация</h2>
                    <button class="modal-close" onclick="AuthModule.closeRegister()">&times;</button>
                </div>
                <div id="register-alert" class="alert"></div>
                <form id="register-form" class="auth-form">
                    <div class="form-group">
                        <label for="register-company" data-i18n="profile.company">Название компании</label>
                        <input type="text" id="register-company" name="company_name" required>
                    </div>
                    <div class="form-group">
                        <label for="register-email" data-i18n="auth.email">Email</label>
                        <input type="email" id="register-email" name="email" required>
                    </div>
                    <div class="form-group">
                        <label for="register-password" data-i18n="auth.password">Пароль</label>
                        <input type="password" id="register-password" name="password" required minlength="6">
                    </div>
                    <div class="form-group">
                        <label for="register-first-name">Имя</label>
                        <input type="text" id="register-first-name" name="first_name">
                    </div>
                    <div class="form-group">
                        <label for="register-last-name">Фамилия</label>
                        <input type="text" id="register-last-name" name="last_name">
                    </div>
                    <div class="form-group">
                        <label for="register-language" data-i18n="settings.language">Язык</label>
                        <select id="register-language" name="language">
                            <option value="ru">Русский</option>
                            <option value="en">English</option>
                            <option value="sk">Slovenčina</option>
                        </select>
                    </div>
                    <button type="submit" class="btn btn-primary btn-block" data-i18n="auth.register">Зарегистрироваться</button>
                </form>
                <div class="auth-switch">
                    <span data-i18n="auth.have_account">Уже есть аккаунт?</span>
                    <a href="#" onclick="AuthModule.openLogin()"><span data-i18n="auth.login">Войти</span></a>
                </div>
            </div>
        `;
        document.body.appendChild(registerModal);

        // Settings Modal
        settingsModal = document.createElement('div');
        settingsModal.className = 'modal-overlay';
        settingsModal.id = 'settings-modal';
        settingsModal.innerHTML = `
            <div class="modal" style="max-width: 500px;">
                <div class="modal-header">
                    <h2 data-i18n="settings.title">Настройки</h2>
                    <button class="modal-close" onclick="AuthModule.closeSettings()">&times;</button>
                </div>
                <div id="settings-alert" class="alert"></div>
                
                <div class="settings-tabs">
                    <button class="settings-tab active" data-tab="profile" data-i18n="profile.title">Профиль</button>
                    <button class="settings-tab" data-tab="company" data-i18n="profile.company">Компания</button>
                    <button class="settings-tab" data-tab="language" data-i18n="settings.language">Язык</button>
                </div>

                <!-- Profile Tab -->
                <div class="settings-tab-content active" data-content="profile">
                    <div class="profile-card" id="profile-info"></div>
                    <form id="profile-form">
                        <div class="form-group">
                            <label for="profile-first-name">Имя</label>
                            <input type="text" id="profile-first-name" name="first_name">
                        </div>
                        <div class="form-group">
                            <label for="profile-last-name">Фамилия</label>
                            <input type="text" id="profile-last-name" name="last_name">
                        </div>
                        <div class="form-group">
                            <label for="profile-language" data-i18n="settings.language">Язык</label>
                            <select id="profile-language" name="language">
                                <option value="ru">Русский</option>
                                <option value="en">English</option>
                                <option value="sk">Slovenčina</option>
                            </select>
                        </div>
                        <button type="submit" class="btn btn-primary" data-i18n="profile.save">Сохранить</button>
                    </form>
                </div>

                <!-- Company Tab -->
                <div class="settings-tab-content" data-content="company">
                    <div class="profile-card" id="company-info"></div>
                </div>

                <!-- Language Tab -->
                <div class="settings-tab-content" data-content="language">
                    <div class="language-selector">
                        <div class="language-option" data-lang="ru">
                            <div class="language-flag">🇷🇺</div>
                            <div class="language-name">Русский</div>
                            <div class="language-native">Русский</div>
                        </div>
                        <div class="language-option" data-lang="en">
                            <div class="language-flag">🇬🇧</div>
                            <div class="language-name">English</div>
                            <div class="language-native">English</div>
                        </div>
                        <div class="language-option" data-lang="sk">
                            <div class="language-flag">🇸🇰</div>
                            <div class="language-name">Slovak</div>
                            <div class="language-native">Slovenčina</div>
                        </div>
                    </div>
                </div>
            </div>
        `;
        document.body.appendChild(settingsModal);

        // Получаем ссылки на формы
        loginForm = document.getElementById('login-form');
        registerForm = document.getElementById('register-form');
        profileForm = document.getElementById('profile-form');
    }

    /**
     * Загружает данные текущего пользователя
     */
    async function loadCurrentUser() {
        try {
            const response = await fetch('/api/auth/profile', { credentials: 'include' });
            if (response.ok) {
                const data = await response.json();
                currentUser = data.user;
                currentLanguage = currentUser.language || 'ru';
                updateUserMenu();
                updatePageLanguage(currentLanguage);
            } else {
                // Не авторизован — показываем форму входа
                updateUserMenu();
            }
        } catch (error) {
            // Пользователь не авторизован
            currentUser = null;
            updateUserMenu();
        }
    }

    /**
     * Обновляет меню пользователя в sidebar
     */
    function updateUserMenu() {
        const sidebar = document.getElementById('sidebar');
        if (!sidebar) return;

        // Удаляем существующее меню если есть
        const existingMenu = sidebar.querySelector('.user-menu');
        if (existingMenu) {
            existingMenu.remove();
        }

        if (!currentUser) {
            // Кнопка входа
            const loginBtn = document.createElement('button');
            loginBtn.className = 'btn btn-primary btn-block';
            loginBtn.textContent = 'Войти';
            loginBtn.onclick = openLogin;
            
            const menuContainer = document.createElement('div');
            menuContainer.className = 'user-menu';
            menuContainer.appendChild(loginBtn);
            sidebar.appendChild(menuContainer);
            return;
        }

        // Меню пользователя
        const initials = `${currentUser.first_name?.[0] || ''}${currentUser.last_name?.[0] || ''}`.toUpperCase() || 'U';
        
        const userMenu = document.createElement('div');
        userMenu.className = 'user-menu';
        userMenu.innerHTML = `
            <div class="user-dropdown" id="user-dropdown">
                <div class="user-dropdown-item" onclick="AuthModule.openSettings()">
                    <i class="fas fa-user"></i>
                    <span data-i18n="nav.profile">Профиль</span>
                </div>
                <div class="user-dropdown-item" onclick="AuthModule.openSettings('company')">
                    <i class="fas fa-building"></i>
                    <span data-i18n="profile.company">Компания</span>
                </div>
                <div class="user-dropdown-item" onclick="AuthModule.openSettings('language')">
                    <i class="fas fa-language"></i>
                    <span data-i18n="settings.language">Язык</span>
                </div>
                <div style="border-top: 1px solid #e0e0e0; margin: 5px 0;"></div>
                <div class="user-dropdown-item" onclick="AuthModule.logout()">
                    <i class="fas fa-sign-out-alt"></i>
                    <span data-i18n="nav.logout">Выйти</span>
                </div>
            </div>
            <button class="user-menu-toggle" onclick="AuthModule.toggleUserDropdown()">
                <div class="user-avatar">${initials}</div>
                <div class="user-info">
                    <div class="user-name">${currentUser.first_name || currentUser.email}</div>
                    <div class="user-company">${currentUser.company.name}</div>
                </div>
                <i class="fas fa-chevron-up"></i>
            </button>
        `;
        sidebar.appendChild(userMenu);
    }

    /**
     * Переключает выпадающее меню пользователя
     */
    function toggleUserDropdown() {
        const dropdown = document.getElementById('user-dropdown');
        if (dropdown) {
            dropdown.classList.toggle('active');
        }
    }

    /**
     * Открывает модальное окно входа
     */
    function openLogin() {
        loginModal.classList.add('active');
        document.getElementById('login-email').focus();
    }

    /**
     * Закрывает модальное окно входа
     */
    function closeLogin() {
        loginModal.classList.remove('active');
        hideAlert('login-alert');
    }

    /**
     * Открывает модальное окно регистрации
     */
    function openRegister() {
        closeLogin();
        registerModal.classList.add('active');
        document.getElementById('register-email').focus();
    }

    /**
     * Закрывает модальное окно регистрации
     */
    function closeRegister() {
        registerModal.classList.remove('active');
        hideAlert('register-alert');
    }

    /**
     * Открывает модальное окно настроек
     */
    function openSettings(tab = 'profile') {
        // Закрываем dropdown
        const dropdown = document.getElementById('user-dropdown');
        if (dropdown) {
            dropdown.classList.remove('active');
        }

        settingsModal.classList.add('active');
        
        // Переключаем вкладку
        document.querySelectorAll('.settings-tab').forEach(t => {
            t.classList.toggle('active', t.dataset.tab === tab);
        });
        document.querySelectorAll('.settings-tab-content').forEach(c => {
            c.classList.toggle('active', c.dataset.content === tab);
        });

        // Загружаем данные профиля
        if (tab === 'profile') {
            loadProfileData();
        } else if (tab === 'company') {
            loadCompanyData();
        }
    }

    /**
     * Закрывает модальное окно настроек
     */
    function closeSettings() {
        settingsModal.classList.remove('active');
        hideAlert('settings-alert');
    }

    /**
     * Загружает данные профиля
     */
    async function loadProfileData() {
        if (!currentUser) return;
        
        document.getElementById('profile-first-name').value = currentUser.first_name || '';
        document.getElementById('profile-last-name').value = currentUser.last_name || '';
        document.getElementById('profile-language').value = currentUser.language || 'ru';

        const profileInfo = document.getElementById('profile-info');
        profileInfo.innerHTML = `
            <div class="profile-row">
                <span class="profile-label" data-i18n="auth.email">Email</span>
                <span class="profile-value">${currentUser.email}</span>
            </div>
            <div class="profile-row">
                <span class="profile-label" data-i18n="profile.role">Роль</span>
                <span class="profile-value">${translateRole(currentUser.role)}</span>
            </div>
            <div class="profile-row">
                <span class="profile-label" data-i18n="profile.created_at">Дата регистрации</span>
                <span class="profile-value">${formatDate(currentUser.created_at)}</span>
            </div>
        `;
    }

    /**
     * Загружает данные компании
     */
    async function loadCompanyData() {
        try {
            const response = await fetch('/api/auth/company');
            if (response.ok) {
                const data = await response.json();
                const company = data.company;
                
                const companyInfo = document.getElementById('company-info');
                companyInfo.innerHTML = `
                    <div class="profile-row">
                        <span class="profile-label" data-i18n="profile.company">Название</span>
                        <span class="profile-value">${company.name}</span>
                    </div>
                    <div class="profile-row">
                        <span class="profile-label" data-i18n="fields.created">Создано</span>
                        <span class="profile-value">${formatDate(company.created_at)}</span>
                    </div>
                    <div class="profile-row">
                        <span class="profile-label">Пользователей</span>
                        <span class="profile-value">${company.users.length}</span>
                    </div>
                `;
            }
        } catch (error) {
            console.error('Error loading company:', error);
        }
    }

    /**
     * Устанавливает обработчики событий
     */
    function setupEventListeners() {
        // Login form
        loginForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            await handleLogin(new FormData(loginForm));
        });

        // Register form
        registerForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            await handleRegister(new FormData(registerForm));
        });

        // Profile form
        profileForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            await handleProfileUpdate(new FormData(profileForm));
        });

        // Language selector
        document.querySelectorAll('.language-option').forEach(option => {
            option.addEventListener('click', () => {
                const lang = option.dataset.lang;
                selectLanguage(lang);
            });
        });

        // Settings tabs
        document.querySelectorAll('.settings-tab').forEach(tab => {
            tab.addEventListener('click', () => {
                const targetTab = tab.dataset.tab;
                openSettings(targetTab);
            });
        });

        // Закрытие по клику вне модального окна
        [loginModal, registerModal, settingsModal].forEach(modal => {
            modal.addEventListener('click', (e) => {
                if (e.target === modal) {
                    closeLogin();
                    closeRegister();
                    closeSettings();
                }
            });
        });
    }

    /**
     * Обрабатывает вход пользователя
     */
    async function handleLogin(formData) {
        const alertEl = document.getElementById('login-alert');

        try {
            const response = await fetch('/api/auth/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify({
                    email: formData.get('email'),
                    password: formData.get('password'),
                    remember: formData.get('remember') === 'on'
                })
            });

            const data = await response.json();

            if (response.ok) {
                currentUser = data.user;
                currentLanguage = currentUser.language || 'ru';
                closeLogin();
                updateUserMenu();
                updatePageLanguage(currentLanguage);
                showAlert(alertEl, data.message, 'success');
                
                // Перезагружаем страницу для применения авторизации
                setTimeout(() => location.reload(), 1000);
            } else {
                showAlert(alertEl, data.message || 'Ошибка входа', 'error');
            }
        } catch (error) {
            showAlert(alertEl, 'Ошибка сети', 'error');
        }
    }

    /**
     * Обрабатывает регистрацию
     */
    async function handleRegister(formData) {
        const alertEl = document.getElementById('register-alert');

        try {
            const response = await fetch('/api/auth/register', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify({
                    email: formData.get('email'),
                    password: formData.get('password'),
                    company_name: formData.get('company_name'),
                    first_name: formData.get('first_name'),
                    last_name: formData.get('last_name'),
                    language: formData.get('language')
                })
            });

            const data = await response.json();

            if (response.ok) {
                currentUser = data.user;
                currentLanguage = currentUser.language || 'ru';
                closeRegister();
                updateUserMenu();
                updatePageLanguage(currentLanguage);
                showAlert(alertEl, data.message, 'success');
                
                // Перезагружаем страницу
                setTimeout(() => location.reload(), 1000);
            } else {
                showAlert(alertEl, data.message || 'Ошибка регистрации', 'error');
            }
        } catch (error) {
            showAlert(alertEl, 'Ошибка сети', 'error');
        }
    }

    /**
     * Обрабатывает обновление профиля
     */
    async function handleProfileUpdate(formData) {
        const alertEl = document.getElementById('settings-alert');
        
        try {
            const response = await fetch('/api/auth/profile', {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    first_name: formData.get('first_name'),
                    last_name: formData.get('last_name'),
                    language: formData.get('language')
                })
            });

            const data = await response.json();

            if (response.ok) {
                currentUser = { ...currentUser, ...data.user };
                currentLanguage = currentUser.language;
                updateUserMenu();
                updatePageLanguage(currentLanguage);
                showAlert(alertEl, data.message, 'success');
            } else {
                showAlert(alertEl, data.message || 'Ошибка обновления', 'error');
            }
        } catch (error) {
            showAlert(alertEl, 'Ошибка сети', 'error');
        }
    }

    /**
     * Выполняет logout
     */
    async function logout() {
        try {
            await fetch('/api/auth/logout', { method: 'POST' });
        } catch (error) {
            console.error('Logout error:', error);
        }
        
        currentUser = null;
        updateUserMenu();
        location.reload();
    }

    /**
     * Выбирает язык
     */
    function selectLanguage(lang) {
        // Обновляем UI
        document.querySelectorAll('.language-option').forEach(opt => {
            opt.classList.toggle('active', opt.dataset.lang === lang);
        });

        // Сохраняем
        currentLanguage = lang;
        updatePageLanguage(lang);

        // Обновляем профиль если открыт
        if (currentUser) {
            handleProfileUpdate(new FormData(profileForm));
        }
    }

    /**
     * Обновляет язык на странице
     */
    function updatePageLanguage(lang) {
        document.documentElement.lang = lang;
        
        // Обновляем все элементы с data-i18n
        document.querySelectorAll('[data-i18n]').forEach(el => {
            const key = el.dataset.i18n;
            const translation = translate(key, lang);
            if (translation) {
                el.textContent = translation;
            }
        });
    }

    /**
     * Показывает уведомление
     */
    function showAlert(element, message, type = 'info') {
        element.textContent = message;
        element.className = `alert alert-${type} active`;
        setTimeout(() => {
            element.classList.remove('active');
        }, 5000);
    }

    /**
     * Скрывает уведомление
     */
    function hideAlert(elementId) {
        const element = document.getElementById(elementId);
        if (element) {
            element.classList.remove('active');
        }
    }

    /**
     * Переводит ключ
     */
    function translate(key, lang) {
        const translations = {
            'auth.login': { ru: 'Вход', en: 'Login', sk: 'Prihlásenie' },
            'auth.register': { ru: 'Регистрация', en: 'Register', sk: 'Registrácia' },
            'auth.email': { ru: 'Email', en: 'Email', sk: 'Email' },
            'auth.password': { ru: 'Пароль', en: 'Password', sk: 'Heslo' },
            'auth.remember_me': { ru: 'Запомнить меня', en: 'Remember me', sk: 'Zapamätať si ma' },
            'auth.forgot_password': { ru: 'Забыли пароль?', en: 'Forgot password?', sk: 'Zabudli ste heslo?' },
            'auth.no_account': { ru: 'Нет аккаунта?', en: 'No account?', sk: 'Nemáte účet?' },
            'auth.have_account': { ru: 'Уже есть аккаунт?', en: 'Already have an account?', sk: 'Už máte účet?' },
            'profile.title': { ru: 'Профиль', en: 'Profile', sk: 'Profil' },
            'profile.company': { ru: 'Компания', en: 'Company', sk: 'Spoločnosť' },
            'profile.role': { ru: 'Роль', en: 'Role', sk: 'Rola' },
            'profile.created_at': { ru: 'Дата регистрации', en: 'Registration date', sk: 'Dátum registrácie' },
            'settings.title': { ru: 'Настройки', en: 'Settings', sk: 'Nastavenia' },
            'settings.language': { ru: 'Язык', en: 'Language', sk: 'Jazyk' },
            'nav.profile': { ru: 'Профиль', en: 'Profile', sk: 'Profil' },
            'nav.logout': { ru: 'Выйти', en: 'Logout', sk: 'Odhlásiť sa' },
            'profile.save': { ru: 'Сохранить', en: 'Save', sk: 'Uložiť' },
            'fields.created': { ru: 'Создано', en: 'Created', sk: 'Vytvorené' },
        };
        
        return translations[key]?.[lang] || key;
    }

    /**
     * Переводит роль
     */
    function translateRole(role) {
        const roles = {
            'owner': { ru: 'Владелец', en: 'Owner', sk: 'Majiteľ' },
            'admin': { ru: 'Администратор', en: 'Admin', sk: 'Administrátor' },
            'agronomist': { ru: 'Агроном', en: 'Agronomist', sk: 'Agronóm' },
            'operator': { ru: 'Оператор', en: 'Operator', sk: 'Operátor' },
            'viewer': { ru: 'Наблюдатель', en: 'Viewer', sk: 'Pozorovateľ' },
        };
        return roles[role]?.[currentLanguage] || role;
    }

    /**
     * Форматирует дату
     */
    function formatDate(dateString) {
        if (!dateString) return '-';
        const date = new Date(dateString);
        return date.toLocaleDateString(currentLanguage === 'ru' ? 'ru-RU' : currentLanguage === 'sk' ? 'sk-SK' : 'en-US');
    }

    // Публичный API
    return {
        init,
        openLogin,
        closeLogin,
        openRegister,
        closeRegister,
        openSettings,
        closeSettings,
        toggleUserDropdown,
        logout,
        getCurrentUser: () => currentUser,
        getCurrentLanguage: () => currentLanguage,
        isLoggedIn: () => currentUser !== null,
    };

})();

// Инициализация после загрузки DOM
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => AuthModule.init());
} else {
    AuthModule.init();
}
