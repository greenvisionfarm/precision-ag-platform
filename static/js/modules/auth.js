/**
 * Модуль аутентификации и управления пользователем.
 * Обрабатывает вход, регистрацию, logout и настройки профиля.
 */

const TRANSLATIONS = {
  "auth.login": { ru: "Вход", en: "Login", sk: "Prihlásenie" },
  "auth.register": { ru: "Регистрация", en: "Register", sk: "Registrácia" },
  "auth.email": { ru: "Email", en: "Email", sk: "Email" },
  "auth.password": { ru: "Пароль", en: "Password", sk: "Heslo" },
  "auth.remember_me": { ru: "Запомнить меня", en: "Remember me", sk: "Zapamätať si ma" },
  "auth.forgot_password": { ru: "Забыли пароль?", en: "Forgot password?", sk: "Zabudli ste heslo?" },
  "auth.no_account": { ru: "Нет аккаунта?", en: "No account?", sk: "Nemáte účet?" },
  "auth.have_account": { ru: "Уже есть аккаунт?", en: "Already have an account?", sk: "Už máte účet?" },
  "profile.title": { ru: "Профиль", en: "Profile", sk: "Profil" },
  "profile.company": { ru: "Компания", en: "Company", sk: "Spoločnosť" },
  "profile.role": { ru: "Роль", en: "Role", sk: "Rola" },
  "profile.created_at": { ru: "Дата регистрации", en: "Registration date", sk: "Dátum registrácie" },
  "settings.title": { ru: "Настройки", en: "Settings", sk: "Nastavenia" },
  "settings.language": { ru: "Язык", en: "Language", sk: "Jazyk" },
  "nav.profile": { ru: "Профиль", en: "Profile", sk: "Profil" },
  "nav.logout": { ru: "Выйти", en: "Logout", sk: "Odhlásiť sa" },
  "profile.save": { ru: "Сохранить", en: "Save", sk: "Uložiť" },
  "fields.created": { ru: "Создано", en: "Created", sk: "Vytvorené" },
};

const ROLES = {
  owner: { ru: "Владелец", en: "Owner", sk: "Majiteľ" },
  admin: { ru: "Администратор", en: "Admin", sk: "Administrátor" },
  agronomist: { ru: "Агроном", en: "Agronomist", sk: "Agronóm" },
  operator: { ru: "Оператор", en: "Operator", sk: "Operátor" },
  viewer: { ru: "Наблюдатель", en: "Viewer", sk: "Pozorovateľ" },
};

class AuthModule {
  constructor() {
    this.currentUser = null;
    this.currentLanguage = "ru";
    this.loginModal = null;
    this.registerModal = null;
    this.settingsModal = null;
    this.loginForm = null;
    this.registerForm = null;
    this.profileForm = null;
  }

  init() {
    this._createModals();
    this._loadCurrentUser();
    this._setupEventListeners();
  }

  // --- Public API ---

  openLogin() {
    this.loginModal.classList.add("active");
    document.getElementById("login-email").focus();
  }

  closeLogin() {
    this.loginModal.classList.remove("active");
    this._hideAlert("login-alert");
  }

  openRegister() {
    this.closeLogin();
    this.registerModal.classList.add("active");
    document.getElementById("register-email").focus();
  }

  closeRegister() {
    this.registerModal.classList.remove("active");
    this._hideAlert("register-alert");
  }

  openSettings(tab = "profile") {
    const dropdown = document.getElementById("user-dropdown");
    if (dropdown) dropdown.classList.remove("active");

    this.settingsModal.classList.add("active");

    document.querySelectorAll(".settings-tab").forEach(t => {
      t.classList.toggle("active", t.dataset.tab === tab);
    });
    document.querySelectorAll(".settings-tab-content").forEach(c => {
      c.classList.toggle("active", c.dataset.content === tab);
    });

    if (tab === "profile") this._loadProfileData();
    else if (tab === "company") this._loadCompanyData();
  }

  closeSettings() {
    this.settingsModal.classList.remove("active");
    this._hideAlert("settings-alert");
  }

  toggleUserDropdown() {
    const dropdown = document.getElementById("user-dropdown");
    if (dropdown) dropdown.classList.toggle("active");
  }

  async logout() {
    try {
      await fetch("/api/auth/logout", { method: "POST" });
    } catch (_) { /* ignore */ }
    this.currentUser = null;
    this._updateUserMenu();
    location.reload();
  }

  async loadCurrentUser() {
    return this._loadCurrentUser();
  }

  getCurrentUser() { return this.currentUser; }
  getCurrentLanguage() { return this.currentLanguage; }
  isLoggedIn() { return this.currentUser !== null; }

  // --- Private: Modals ---

  _createModals() {
    this.loginModal = this._createElement("login-modal", `
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
    `);

    this.registerModal = this._createElement("register-modal", `
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
    `);

    this.settingsModal = this._createElement("settings-modal", `
      <div class="modal">
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
        <div class="settings-tab-content" data-content="company">
          <div class="profile-card" id="company-info"></div>
        </div>
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
    `);

    this.loginForm = document.getElementById("login-form");
    this.registerForm = document.getElementById("register-form");
    this.profileForm = document.getElementById("profile-form");
  }

  _createElement(id, html) {
    const el = document.createElement("div");
    el.className = "modal-overlay";
    el.id = id;
    el.innerHTML = html;
    document.body.appendChild(el);
    return el;
  }

  // --- Private: User ---

  async _loadCurrentUser() {
    try {
      const resp = await fetch("/api/auth/profile", { credentials: "include" });
      if (resp.ok) {
        const data = await resp.json();
        this.currentUser = data.user;
        this.currentLanguage = this.currentUser.language || "ru";
        this._updateUserMenu();
        this._updatePageLanguage(this.currentLanguage);
      } else {
        this._updateUserMenu();
      }
    } catch (_) {
      this.currentUser = null;
      this._updateUserMenu();
    }
  }

  _updateUserMenu() {
    const sidebar = document.getElementById("sidebar");
    if (!sidebar) return;

    const existing = sidebar.querySelector(".user-menu");
    if (existing) existing.remove();

    if (!this.currentUser) {
      const btn = document.createElement("button");
      btn.className = "btn btn-primary btn-block";
      btn.textContent = "Войти";
      btn.onclick = () => this.openLogin();
      const container = document.createElement("div");
      container.className = "user-menu";
      container.appendChild(btn);
      sidebar.appendChild(container);
      return;
    }

    const u = this.currentUser;
    const initials = `${u.first_name?.[0] || ""}${u.last_name?.[0] || ""}`.toUpperCase() || "U";

    const menu = document.createElement("div");
    menu.className = "user-menu";
    menu.innerHTML = `
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
        <div class="auth-divider"></div>
        <div class="user-dropdown-item" onclick="AuthModule.logout()">
          <i class="fas fa-sign-out-alt"></i>
          <span data-i18n="nav.logout">Выйти</span>
        </div>
      </div>
      <button class="user-menu-toggle" onclick="AuthModule.toggleUserDropdown()">
        <div class="user-avatar">${initials}</div>
        <div class="user-info">
          <div class="user-name">${u.first_name || u.email}</div>
          <div class="user-company">${u.company.name}</div>
        </div>
        <i class="fas fa-chevron-up"></i>
      </button>
    `;
    sidebar.appendChild(menu);
  }

  // --- Private: Events ---

  _setupEventListeners() {
    this.loginForm.addEventListener("submit", (e) => {
      e.preventDefault();
      this._handleLogin(new FormData(this.loginForm));
    });

    this.registerForm.addEventListener("submit", (e) => {
      e.preventDefault();
      this._handleRegister(new FormData(this.registerForm));
    });

    this.profileForm.addEventListener("submit", (e) => {
      e.preventDefault();
      this._handleProfileUpdate(new FormData(this.profileForm));
    });

    document.querySelectorAll(".language-option").forEach(opt => {
      opt.addEventListener("click", () => this._selectLanguage(opt.dataset.lang));
    });

    document.querySelectorAll(".settings-tab").forEach(tab => {
      tab.addEventListener("click", () => this.openSettings(tab.dataset.tab));
    });

    [this.loginModal, this.registerModal, this.settingsModal].forEach(modal => {
      modal.addEventListener("click", (e) => {
        if (e.target === modal) {
          this.closeLogin();
          this.closeRegister();
          this.closeSettings();
        }
      });
    });
  }

  // --- Private: Auth handlers ---

  async _handleLogin(formData) {
    const alertEl = document.getElementById("login-alert");
    try {
      const resp = await fetch("/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({
          email: formData.get("email"),
          password: formData.get("password"),
          remember: formData.get("remember") === "on"
        })
      });
      const data = await resp.json();
      if (resp.ok) {
        this.currentUser = data.user;
        this.currentLanguage = this.currentUser.language || "ru";
        this.closeLogin();
        this._updateUserMenu();
        this._updatePageLanguage(this.currentLanguage);
        this._showAlert(alertEl, data.message, "success");
        setTimeout(() => location.reload(), 1000);
      } else {
        this._showAlert(alertEl, data.message || "Ошибка входа", "error");
      }
    } catch (_) {
      this._showAlert(alertEl, "Ошибка сети", "error");
    }
  }

  async _handleRegister(formData) {
    const alertEl = document.getElementById("register-alert");
    try {
      const resp = await fetch("/api/auth/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({
          email: formData.get("email"),
          password: formData.get("password"),
          company_name: formData.get("company_name"),
          first_name: formData.get("first_name"),
          last_name: formData.get("last_name"),
          language: formData.get("language")
        })
      });
      const data = await resp.json();
      if (resp.ok) {
        this.currentUser = data.user;
        this.currentLanguage = this.currentUser.language || "ru";
        this.closeRegister();
        this._updateUserMenu();
        this._updatePageLanguage(this.currentLanguage);
        this._showAlert(alertEl, data.message, "success");
        setTimeout(() => location.reload(), 1000);
      } else {
        this._showAlert(alertEl, data.message || "Ошибка регистрации", "error");
      }
    } catch (_) {
      this._showAlert(alertEl, "Ошибка сети", "error");
    }
  }

  async _handleProfileUpdate(formData) {
    const alertEl = document.getElementById("settings-alert");
    try {
      const resp = await fetch("/api/auth/profile", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          first_name: formData.get("first_name"),
          last_name: formData.get("last_name"),
          language: formData.get("language")
        })
      });
      const data = await resp.json();
      if (resp.ok) {
        this.currentUser = { ...this.currentUser, ...data.user };
        this.currentLanguage = this.currentUser.language;
        this._updateUserMenu();
        this._updatePageLanguage(this.currentLanguage);
        this._showAlert(alertEl, data.message, "success");
      } else {
        this._showAlert(alertEl, data.message || "Ошибка обновления", "error");
      }
    } catch (_) {
      this._showAlert(alertEl, "Ошибка сети", "error");
    }
  }

  // --- Private: Profile/Company data ---

  async _loadProfileData() {
    if (!this.currentUser) return;
    const u = this.currentUser;
    document.getElementById("profile-first-name").value = u.first_name || "";
    document.getElementById("profile-last-name").value = u.last_name || "";
    document.getElementById("profile-language").value = u.language || "ru";

    document.getElementById("profile-info").innerHTML = `
      <div class="profile-row">
        <span class="profile-label" data-i18n="auth.email">Email</span>
        <span class="profile-value">${u.email}</span>
      </div>
      <div class="profile-row">
        <span class="profile-label" data-i18n="profile.role">Роль</span>
        <span class="profile-value">${this._translateRole(u.role)}</span>
      </div>
      <div class="profile-row">
        <span class="profile-label" data-i18n="profile.created_at">Дата регистрации</span>
        <span class="profile-value">${this._formatDate(u.created_at)}</span>
      </div>
    `;
  }

  async _loadCompanyData() {
    try {
      const resp = await fetch("/api/auth/company");
      if (resp.ok) {
        const data = await resp.json();
        const c = data.company;
        document.getElementById("company-info").innerHTML = `
          <div class="profile-row">
            <span class="profile-label" data-i18n="profile.company">Название</span>
            <span class="profile-value">${c.name}</span>
          </div>
          <div class="profile-row">
            <span class="profile-label" data-i18n="fields.created">Создано</span>
            <span class="profile-value">${this._formatDate(c.created_at)}</span>
          </div>
          <div class="profile-row">
            <span class="profile-label">Пользователей</span>
            <span class="profile-value">${c.users.length}</span>
          </div>
        `;
      }
    } catch (_) { /* ignore */ }
  }

  // --- Private: i18n ---

  _selectLanguage(lang) {
    document.querySelectorAll(".language-option").forEach(opt => {
      opt.classList.toggle("active", opt.dataset.lang === lang);
    });
    this.currentLanguage = lang;
    this._updatePageLanguage(lang);
    if (this.currentUser) {
      this._handleProfileUpdate(new FormData(this.profileForm));
    }
  }

  _updatePageLanguage(lang) {
    document.documentElement.lang = lang;
    document.querySelectorAll("[data-i18n]").forEach(el => {
      const key = el.dataset.i18n;
      const t = TRANSLATIONS[key]?.[lang];
      if (t) el.textContent = t;
    });
  }

  _translate(key, lang) {
    return TRANSLATIONS[key]?.[lang] || key;
  }

  _translateRole(role) {
    return ROLES[role]?.[this.currentLanguage] || role;
  }

  _formatDate(dateString) {
    if (!dateString) return "-";
    const d = new Date(dateString);
    const locale = this.currentLanguage === "ru" ? "ru-RU" : this.currentLanguage === "sk" ? "sk-SK" : "en-US";
    return d.toLocaleDateString(locale);
  }

  // --- Private: Alerts ---

  _showAlert(element, message, type = "info") {
    element.textContent = message;
    element.className = `alert alert-${type} active`;
    setTimeout(() => element.classList.remove("active"), 5000);
  }

  _hideAlert(elementId) {
    const el = document.getElementById(elementId);
    if (el) el.classList.remove("active");
  }
}

// Singleton + backward compatibility
const authModule = new AuthModule();
window.AuthModule = authModule;

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", () => authModule.init());
} else {
  authModule.init();
}
