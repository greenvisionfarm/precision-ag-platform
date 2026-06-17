"""
Handlers для аутентификации и управления пользователями.
"""
import json
import logging
import re
from datetime import datetime
from typing import Any, Dict, Optional

from src.middleware.auth import AuthenticatedRequestHandler
from src.models.auth import Company, User, UserRole
from src.utils.auth import session_manager
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


class LoginHandler(AuthenticatedRequestHandler):
    """
    Handler для входа пользователя.
    POST /api/auth/login
    """

    _require_auth = False
    
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


class RegisterHandler(AuthenticatedRequestHandler):
    """
    Handler для регистрации нового пользователя и компании.
    POST /api/auth/register
    """

    _require_auth = False
    
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
            
            # Создаём компанию с уникальным slug
            slug = company_name.lower().replace(' ', '-').replace('--', '-')
            slug = re.sub(r'[^\w-]', '', slug)
            if not slug:
                slug = 'company'
            
            # Гарантируем уникальность slug
            base_slug = slug
            counter = 1
            while Company.select().where(Company.slug == slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1

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


class LogoutHandler(AuthenticatedRequestHandler):
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


class ProfileHandler(AuthenticatedRequestHandler):
    """
    Handler для управления профилем пользователя.
    GET/PUT /api/auth/profile
    """
    
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


class CompanyHandler(AuthenticatedRequestHandler):
    """
    Handler для управления компанией.
    GET/PUT /api/auth/company
    """
    
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
            # Обновляем slug при смене имени
            new_slug = company.name.lower().replace(' ', '-').replace('--', '-')
            new_slug = re.sub(r'[^\w-]', '', new_slug)
            if new_slug and new_slug != company.slug:
                base_slug = new_slug
                counter = 1
                while Company.select().where((Company.slug == new_slug) & (Company.id != company.id)).exists():
                    new_slug = f"{base_slug}-{counter}"
                    counter += 1
                company.slug = new_slug
        
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
