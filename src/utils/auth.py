"""
Утилиты для аутентификации и сессий.
"""
import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta
from typing import Optional

from src.models.auth import User


class SessionManager:
    """
    Менеджер сессий для управления токенами доступа.
    Использует HMAC-SHA256 для генерации и проверки токенов.
    """
    
    def __init__(self, secret_key: Optional[str] = None):
        """
        Инициализирует менеджер сессий.
        
        Args:
            secret_key: Секретный ключ для подписи токенов.
                       Если None, используется SESSION_SECRET из окружения
                       или генерируется новый.
        """
        self.secret_key = secret_key or os.environ.get(
            'SESSION_SECRET', 
            secrets.token_hex(32)
        )
        # Хранилище сессий: token -> {user_id, expires_at, data}
        self._sessions: dict[str, dict] = {}
    
    def create_token(self, user: User, expires_hours: int = 24) -> str:
        """
        Создаёт токен сессии для пользователя.
        
        Args:
            user: Пользователь, для которого создаётся токен
            expires_hours: Время действия токена в часах
            
        Returns:
            Строка токена
        """
        # Генерируем случайную часть токена
        random_part = secrets.token_hex(32)
        
        # Создаём timestamp истечения
        expires_at = datetime.now() + timedelta(hours=expires_hours)
        expires_timestamp = int(expires_at.timestamp())
        
        # Создаём payload: user_id:expires_timestamp:random_part
        payload = f"{user.id}:{expires_timestamp}:{random_part}"
        
        # Подписываем payload
        signature = self._sign(payload)
        
        # Токен: payload.signature
        token = f"{payload}.{signature}"
        
        # Сохраняем сессию
        self._sessions[token] = {
            'user_id': user.id,
            'expires_at': expires_at,
            'data': {
                'email': user.email,
                'company_id': user.company.id,
                'role': user.role,
            }
        }
        
        return token
    
    def verify_token(self, token: str) -> Optional[dict]:
        """
        Проверяет токен и возвращает данные сессии.
        
        Args:
            token: Токен для проверки
            
        Returns:
            Данные сессии или None если токен невалидный
        """
        try:
            # Разделяем токен на payload и signature
            parts = token.split('.')
            if len(parts) != 2:
                return None
            
            payload, signature = parts
            
            # Проверяем подпись
            if not self._verify_signature(payload, signature):
                return None
            
            # Разбираем payload
            payload_parts = payload.split(':')
            if len(payload_parts) != 3:
                return None
            
            user_id, expires_timestamp, _ = payload_parts
            expires_at = datetime.fromtimestamp(int(expires_timestamp))
            
            # Проверяем истечение
            if datetime.now() > expires_at:
                # Удаляем истёкшую сессию
                self._sessions.pop(token, None)
                return None
            
            # Проверяем, есть ли сессия в хранилище
            if token in self._sessions:
                return self._sessions[token]
            
            # Если сессии нет в хранилище, но токен валидный,
            # создаём новую запись (для stateless режима)
            user = User.get_or_none(User.id == int(user_id))
            if not user or not user.is_active:
                return None
            
            session_data = {
                'user_id': user.id,
                'expires_at': expires_at,
                'data': {
                    'email': user.email,
                    'company_id': user.company.id,
                    'role': user.role,
                }
            }
            
            # Кэшируем сессию
            self._sessions[token] = session_data
            
            return session_data
            
        except (ValueError, TypeError):
            return None
    
    def invalidate_token(self, token: str) -> None:
        """
        Уничтожает сессию (logout).
        
        Args:
            token: Токен для уничтожения
        """
        self._sessions.pop(token, None)
    
    def _sign(self, payload: str) -> str:
        """
        Создаёт HMAC подпись для payload.
        
        Args:
            payload: Данные для подписи
            
        Returns:
            Hex подпись
        """
        return hmac.new(
            self.secret_key.encode('utf-8'),
            payload.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
    
    def _verify_signature(self, payload: str, signature: str) -> bool:
        """
        Проверяет HMAC подпись.
        
        Args:
            payload: Подписанные данные
            signature: Подпись для проверки
            
        Returns:
            True если подпись валидна
        """
        expected = self._sign(payload)
        return hmac.compare_digest(expected, signature)
    
    def cleanup_expired(self) -> int:
        """
        Удаляет истёкшие сессии.
        
        Returns:
            Количество удалённых сессий
        """
        now = datetime.now()
        expired = [
            token for token, data in self._sessions.items()
            if data['expires_at'] < now
        ]
        
        for token in expired:
            del self._sessions[token]
        
        return len(expired)


# Глобальный экземляр менеджера сессий
session_manager = SessionManager()


def get_current_user_from_token(token: str) -> Optional[User]:
    """
    Получает пользователя из токена сессии.
    
    Args:
        token: Токен сессии
        
    Returns:
        Пользователь или None
    """
    session_data = session_manager.verify_token(token)
    if not session_data:
        return None
    
    try:
        from src.models.auth import User, Company
        user = User.get(User.id == session_data['user_id'])
        return user
    except Exception:
        return None
