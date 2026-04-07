"""
Handlers для аутентификации и управления пользователями.
"""
import json
import logging
from datetime import datetime
from typing import Any, Dict, Optional

import tornado.web

from src.models.auth import Company, User, UserRole
from src.utils.auth import get_current_user_from_token, session_manager
from src.utils.i18n import t
from src.utils.validators import validate_email

logger = logging.getLogger(__name__)


def _to_iso(value) -> Optional[str]:
    """Конвертирует значение в ISO формат строки."""
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return value.isoformat()


class AuthHandler(tornado.web.RequestHandler):
    """Базовый класс для handlers аутентификации."""
    
    def get_current_user(self) -> Optional[User]:
        """
        Получает текущего пользователя из токена в cookie или заголовке.
        
        Returns:
            Пользователь или None
        """
        # Пробуем получить токен из cookie
        token = self.get_secure_cookie('session_token')
        if not token:
            # Пробуем из заголовка Authorization
            auth_header = self.request.headers.get('Authorization', '')
            if auth_header.startswith('Bearer '):
                token = auth_header[7:].encode('utf-8')
        
        if not token:
            return None
        
        try:
            return get_current_user_from_token(token.decode('utf-8'))
        except Exception as e:
            logger.error(f"Ошибка получения пользователя: {e}")
            return None
    
    def set_auth_cookie(self, token: str, remember: bool = False) -> None:
        """
        Устанавливает cookie с токеном сессии.
        
        Args:
            token: Токен сессии
            remember: Если True, cookie будет действовать 30 дней
        """
        expires_days = 30 if remember else 1
        self.set_secure_cookie(
            'session_token',
            token,
            expires_days=expires_days,
            httponly=True,
            samesite='Lax'
        )
    
    def clear_auth_cookie(self) -> None:
        """Очищает cookie с токеном сессии."""
        self.clear_cookie('session_token')
    
    def write_error(self, status_code: int, **kwargs: Any) -> None:
        """
        Форматирует ответ об ошибке в JSON формате.
        """
        self.set_header('Content-Type', 'application/json')
        exc_info = kwargs.get('exc_info')
        
        error_response = {
            'error': True,
            'status': status_code,
            'message': self._reason,
        }
        
        if exc_info and isinstance(exc_info[1], Exception):
            error_response['details'] = str(exc_info[1])
        
        self.write(json.dumps(error_response))


class LoginHandler(AuthHandler):
    """
    Handler для входа пользователя.
    POST /api/auth/login
    """
    
    def post(self) -> None:
        """
        Аутентифицирует пользователя и создаёт сессию.
        
        Request body:
            email: str
            password: str
            remember: bool (optional)
        """
        try:
            data = json.loads(self.request.body)
        except json.JSONDecodeError:
            self.set_status(400)
            self.write({'error': True, 'message': 'Invalid JSON'})
            return
        
        email = data.get('email', '').strip().lower()
        password = data.get('password', '')
        remember = data.get('remember', False)
        
        # Валидация
        if not email or not password:
            self.set_status(400)
            self.write({'error': True, 'message': t('auth.invalid_credentials', 'ru')})
            return
        
        if not validate_email(email):
            self.set_status(400)
            self.write({'error': True, 'message': 'Invalid email format'})
            return
        
        # Поиск пользователя
        try:
            user = User.get(User.email == email)
        except User.DoesNotExist:
            logger.warning(f"Попытка входа с несуществующим email: {email}")
            self.set_status(401)
            self.write({'error': True, 'message': t('auth.invalid_credentials', 'ru')})
            return
        
        # Проверка пароля
        if not user.verify_password(password):
            logger.warning(f"Неверный пароль для пользователя: {email}")
            self.set_status(401)
            self.write({'error': True, 'message': t('auth.invalid_credentials', 'ru')})
            return
        
        # Проверка активности
        if not user.is_active:
            self.set_status(403)
            self.write({'error': True, 'message': 'Account is deactivated'})
            return
        
        if not user.company.is_active:
            self.set_status(403)
            self.write({'error': True, 'message': 'Company is deactivated'})
            return
        
        # Обновляем last_login
        user.last_login = datetime.now()
        user.save()
        
        # Создаём токен сессии
        token = session_manager.create_token(user, expires_hours=24 if not remember else 720)
        
        # Устанавливаем cookie
        self.set_auth_cookie(token, remember)
        
        # Возвращаем данные пользователя
        self.set_header('Content-Type', 'application/json')
        self.write({
            'success': True,
            'message': t('auth.login_success', user.language),
            'user': {
                'id': user.id,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'role': user.role,
                'language': user.language,
                'company': {
                    'id': user.company.id,
                    'name': user.company.name,
                    'slug': user.company.slug,
                }
            }
        })


class RegisterHandler(AuthHandler):
    """
    Handler для регистрации нового пользователя и компании.
    POST /api/auth/register
    """
    
    def post(self) -> None:
        """
        Регистрирует нового пользователя и создаёт компанию.
        
        Request body:
            email: str
            password: str
            company_name: str
            first_name: str (optional)
            last_name: str (optional)
            language: str (optional, default: 'ru')
        """
        try:
            data = json.loads(self.request.body)
        except json.JSONDecodeError:
            self.set_status(400)
            self.write({'error': True, 'message': 'Invalid JSON'})
            return
        
        email = data.get('email', '').strip().lower()
        password = data.get('password', '')
        company_name = data.get('company_name', '').strip()
        first_name = data.get('first_name', '').strip()
        last_name = data.get('last_name', '').strip()
        language = data.get('language', 'ru')
        
        # Валидация
        if not email or not password or not company_name:
            self.set_status(400)
            self.write({'error': True, 'message': 'Email, password and company name are required'})
            return
        
        if not validate_email(email):
            self.set_status(400)
            self.write({'error': True, 'message': 'Invalid email format'})
            return
        
        if len(password) < 6:
            self.set_status(400)
            self.write({'error': True, 'message': 'Password must be at least 6 characters'})
            return
        
        if language not in ['ru', 'en', 'sk']:
            language = 'ru'
        
        try:
            # Проверяем, существует ли пользователь
            if User.select().where(User.email == email).exists():
                self.set_status(409)
                self.write({'error': True, 'message': 'Email already registered'})
                return
            
            # Создаём компанию
            slug = company_name.lower().replace(' ', '-').replace('--', '-')
            company = Company.create(
                name=company_name,
                slug=slug,
                settings_json=json.dumps({
                    'language': language,
                    'created_at': datetime.now().isoformat(),
                })
            )
            
            # Создаём пользователя с ролью OWNER
            user = User.create_user(
                email=email,
                password=password,
                company=company,
                first_name=first_name or None,
                last_name=last_name or None,
                role=UserRole.OWNER,
                language=language
            )
            
            # Создаём сессию
            token = session_manager.create_token(user, expires_hours=24)
            self.set_auth_cookie(token)
            
            logger.info(f"Зарегистрирован новый пользователь: {email} (company: {company.name})")
            
            self.set_header('Content-Type', 'application/json')
            self.write({
                'success': True,
                'message': t('auth.registration_success', language),
                'user': {
                    'id': user.id,
                    'email': user.email,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'role': user.role,
                    'language': user.language,
                    'company': {
                        'id': company.id,
                        'name': company.name,
                        'slug': company.slug,
                    }
                }
            })
            
        except Exception as e:
            logger.error(f"Ошибка регистрации: {e}")
            self.set_status(500)
            self.write({'error': True, 'message': 'Registration failed'})


class LogoutHandler(AuthHandler):
    """
    Handler для выхода пользователя.
    POST /api/auth/logout
    """
    
    def post(self) -> None:
        """
        Уничтожает сессию пользователя.
        """
        token = self.get_secure_cookie('session_token')
        if token:
            session_manager.invalidate_token(token.decode('utf-8'))
        
        self.clear_auth_cookie()
        
        self.set_header('Content-Type', 'application/json')
        self.write({
            'success': True,
            'message': 'Logged out successfully'
        })


class ProfileHandler(AuthHandler):
    """
    Handler для управления профилем пользователя.
    GET/PUT /api/auth/profile
    """
    
    @tornado.web.authenticated
    def get(self) -> None:
        """
        Возвращает данные профиля текущего пользователя.
        """
        user = self.get_current_user()
        if not user:
            self.set_status(401)
            self.write({'error': True, 'message': 'Unauthorized'})
            return
        
        self.set_header('Content-Type', 'application/json')
        self.write({
            'user': {
                'id': user.id,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'role': user.role,
                'language': user.language,
                'is_verified': user.is_verified,
                'created_at': _to_iso(user.created_at),
                'last_login': _to_iso(user.last_login),
                'company': {
                    'id': user.company.id,
                    'name': user.company.name,
                    'slug': user.company.slug,
                    'settings': json.loads(user.company.settings_json or '{}'),
                }
            }
        })
    
    @tornado.web.authenticated
    def put(self) -> None:
        """
        Обновляет данные профиля пользователя.
        
        Request body:
            first_name: str (optional)
            last_name: str (optional)
            language: str (optional)
            password: str (optional)
            new_password: str (optional, требуется password)
        """
        user = self.get_current_user()
        if not user:
            self.set_status(401)
            self.write({'error': True, 'message': 'Unauthorized'})
            return
        
        try:
            data = json.loads(self.request.body)
        except json.JSONDecodeError:
            self.set_status(400)
            self.write({'error': True, 'message': 'Invalid JSON'})
            return
        
        # Обновляемые поля
        if 'first_name' in data:
            user.first_name = data['first_name'].strip()
        
        if 'last_name' in data:
            user.last_name = data['last_name'].strip()
        
        if 'language' in data and data['language'] in ['ru', 'en', 'sk']:
            user.language = data['language']
        
        # Смена пароля
        if 'password' in data and 'new_password' in data:
            if not user.verify_password(data['password']):
                self.set_status(400)
                self.write({'error': True, 'message': 'Current password is incorrect'})
                return
            
            if len(data['new_password']) < 6:
                self.set_status(400)
                self.write({'error': True, 'message': 'New password must be at least 6 characters'})
                return
            
            password_hash, salt = User.hash_password(data['new_password'])
            user.password_hash = password_hash
            user.password_salt = salt
        
        user.save()
        
        self.set_header('Content-Type', 'application/json')
        self.write({
            'success': True,
            'message': t('profile.update_success', user.language),
            'user': {
                'id': user.id,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'language': user.language,
            }
        })


class CompanyHandler(AuthHandler):
    """
    Handler для управления компанией.
    GET/PUT /api/auth/company
    """
    
    @tornado.web.authenticated
    def get(self) -> None:
        """
        Возвращает данные компании текущего пользователя.
        """
        user = self.get_current_user()
        if not user:
            self.set_status(401)
            self.write({'error': True, 'message': 'Unauthorized'})
            return
        
        company = user.company
        settings = json.loads(company.settings_json or '{}')
        
        # Получаем список пользователей компании
        users_list = []
        for u in company.users.where(User.is_active == True):
            users_list.append({
                'id': u.id,
                'email': u.email,
                'first_name': u.first_name,
                'last_name': u.last_name,
                'role': u.role,
                'language': u.language,
            })
        
        self.set_header('Content-Type', 'application/json')
        self.write({
            'company': {
                'id': company.id,
                'name': company.name,
                'slug': company.slug,
                'created_at': _to_iso(company.created_at),
                'settings': settings,
                'users': users_list,
            }
        })
    
    @tornado.web.authenticated
    def put(self) -> None:
        """
        Обновляет настройки компании.
        Доступно только OWNER и ADMIN.
        
        Request body:
            name: str (optional)
            settings: dict (optional)
        """
        user = self.get_current_user()
        if not user:
            self.set_status(401)
            self.write({'error': True, 'message': 'Unauthorized'})
            return
        
        if not user.has_permission(UserRole.ADMIN):
            self.set_status(403)
            self.write({'error': True, 'message': 'Forbidden'})
            return
        
        try:
            data = json.loads(self.request.body)
        except json.JSONDecodeError:
            self.set_status(400)
            self.write({'error': True, 'message': 'Invalid JSON'})
            return
        
        company = user.company
        
        if 'name' in data:
            company.name = data['name'].strip()
        
        if 'settings' in data and isinstance(data['settings'], dict):
            company.settings_json = json.dumps(data['settings'])
        
        company.save()
        
        self.set_header('Content-Type', 'application/json')
        self.write({
            'success': True,
            'company': {
                'id': company.id,
                'name': company.name,
                'slug': company.slug,
                'settings': json.loads(company.settings_json or '{}'),
            }
        })
