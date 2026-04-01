"""
Middleware для проверки авторизации и tenant isolation.
"""
import logging
from functools import wraps
from typing import Callable, Optional

import tornado.web

from src.models.auth import User, UserRole
from src.utils.auth import get_current_user_from_token

logger = logging.getLogger(__name__)


def require_auth(handler_method: Callable) -> Callable:
    """
    Декоратор для проверки авторизации пользователя.
    Если пользователь не авторизован, возвращает 401.
    
    Usage:
        @require_auth
        def get(self, *args, **kwargs):
            ...
    """
    @wraps(handler_method)
    def wrapper(self, *args, **kwargs):
        user = self.get_current_user()
        if not user:
            self.set_status(401)
            self.write({'error': True, 'message': 'Unauthorized'})
            return
        
        # Сохраняем пользователя в request для удобства
        self._current_user = user
        return handler_method(self, *args, **kwargs)
    
    return wrapper


def require_role(required_role: str) -> Callable:
    """
    Декоратор для проверки роли пользователя.
    Если у пользователя недостаточно прав, возвращает 403.
    
    Usage:
        @require_role(UserRole.ADMIN)
        def post(self, *args, **kwargs):
            ...
    """
    def decorator(handler_method: Callable) -> Callable:
        @wraps(handler_method)
        def wrapper(self, *args, **kwargs):
            user = self.get_current_user()
            if not user:
                self.set_status(401)
                self.write({'error': True, 'message': 'Unauthorized'})
                return
            
            if not user.has_permission(required_role):
                self.set_status(403)
                self.write({
                    'error': True,
                    'message': f'Forbidden. Required role: {required_role}'
                })
                return
            
            self._current_user = user
            return handler_method(self, *args, **kwargs)
        
        return wrapper
    return decorator


def require_owner(handler_method: Callable) -> Callable:
    """
    Декоратор для проверки, что пользователь является OWNER компании.
    """
    @wraps(handler_method)
    def wrapper(self, *args, **kwargs):
        user = self.get_current_user()
        if not user:
            self.set_status(401)
            self.write({'error': True, 'message': 'Unauthorized'})
            return
        
        if not user.is_owner():
            self.set_status(403)
            self.write({'error': True, 'message': 'Forbidden. Owner role required.'})
            return
        
        self._current_user = user
        return handler_method(self, *args, **kwargs)
    
    return wrapper


class AuthenticatedRequestHandler(tornado.web.RequestHandler):
    """
    Базовый класс для всех handlers, требующих авторизации.
    Автоматически проверяет авторизацию и предоставляет доступ к пользователю.
    """
    
    def prepare(self) -> None:
        """
        Вызывается перед каждым запросом.
        Проверяет авторизацию пользователя.
        """
        user = self.get_current_user()
        
        if not user:
            # Для API запросов возвращаем JSON ошибку
            if self.request.path.startswith('/api/'):
                self.set_status(401)
                self.write({'error': True, 'message': 'Unauthorized'})
                self.finish()
                return
            else:
                # Для обычных запросов редиректим на страницу входа
                self.redirect('/login')
                return
        
        # Проверяем, активна ли компания
        if not user.company.is_active:
            self.set_status(403)
            self.write({'error': True, 'message': 'Company is deactivated'})
            self.finish()
            return
        
        # Сохраняем пользователя для доступа в handlers
        self._current_user = user
    
    def get_current_user(self) -> Optional[User]:
        """
        Получает текущего пользователя из токена.
        Переопределяет метод из RequestHandler.
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
    
    @property
    def current_user(self) -> Optional[User]:
        """
        Возвращает текущего пользователя.
        """
        return getattr(self, '_current_user', None)
    
    @property
    def current_company_id(self) -> Optional[int]:
        """
        Возвращает ID компании текущего пользователя.
        """
        user = self.current_user
        return user.company.id if user else None


def get_user_company_filter(user: Optional[User]):
    """
    Возвращает Peewee выражение для фильтрации данных по компании.
    
    Usage:
        fields = Field.select().where(get_user_company_filter(current_user))
    """
    if not user:
        # Если пользователь не авторизован, возвращаем условие, которое всегда ложно
        return (Field.id == -1)
    
    return (Field.company == user.company)


# Импортируем Field здесь, чтобы избежать циклического импорта
from src.models.field import Field
