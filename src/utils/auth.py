"""
Утилиты для аутентификации и сессий.
Redis-backed session storage с HMAC-SHA256 подписью.
Fallback на in-memory dict если Redis недоступен.
"""
import hashlib
import hmac
import json
import logging
import os
import secrets
from datetime import datetime, timedelta
from typing import Optional

from src.models.auth import User

logger = logging.getLogger(__name__)


class SessionManager:
    """
    Менеджер сессий: HMAC-SHA256 подпись + Redis хранение.
    Stateless verification (подпись) + stateful storage (Redis).
    """

    def __init__(self, secret_key: Optional[str] = None):
        self.secret_key = secret_key or os.environ.get(
            'SESSION_SECRET',
            secrets.token_hex(32)
        )
        self._redis = None
        self._fallback_sessions: dict[str, dict] = {}
        self._connect_redis()

    def _connect_redis(self) -> None:
        """Подключается к Redis. Fallback на dict если недоступен."""
        try:
            import redis
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
            self._redis = redis.from_url(
                redis_url, socket_timeout=2, decode_responses=True
            )
            self._redis.ping()
            logger.info("Session storage: Redis")
        except Exception as e:
            logger.warning(
                f"Redis unavailable, using in-memory sessions: {e}"
            )
            self._redis = None

    def _session_key(self, token: str) -> str:
        return f"session:{token}"

    def create_token(self, user: User, expires_hours: int = 24) -> str:
        """Создаёт подписанный токен и сохраняет сессию в Redis."""
        random_part = secrets.token_hex(32)
        expires_at = datetime.now() + timedelta(hours=expires_hours)
        expires_timestamp = int(expires_at.timestamp())

        payload = f"{user.id}:{expires_timestamp}:{random_part}"
        signature = self._sign(payload)
        token = f"{payload}.{signature}"

        session_data = {
            'user_id': user.id,
            'expires_at': expires_at.isoformat(),
            'data': {
                'email': user.email,
                'company_id': user.company.id,
                'role': user.role,
            }
        }

        self._store_session(token, session_data, expires_hours)
        return token

    def verify_token(self, token: str) -> Optional[dict]:
        """Проверяет подпись и возвращает данные сессии."""
        try:
            parts = token.split('.')
            if len(parts) != 2:
                return None

            payload, signature = parts
            if not self._verify_signature(payload, signature):
                return None

            payload_parts = payload.split(':')
            if len(payload_parts) != 3:
                return None

            user_id, expires_timestamp, _ = payload_parts
            expires_at = datetime.fromtimestamp(int(expires_timestamp))

            if datetime.now() > expires_at:
                self._delete_session(token)
                return None

            session = self._get_session(token)
            if session:
                return session

            user = User.get_or_none(User.id == int(user_id))
            if not user or not user.is_active:
                return None

            remaining_hours = max(
                1,
                int((expires_at - datetime.now()).total_seconds() / 3600)
            )
            session_data = {
                'user_id': user.id,
                'expires_at': expires_at.isoformat(),
                'data': {
                    'email': user.email,
                    'company_id': user.company.id,
                    'role': user.role,
                }
            }
            self._store_session(token, session_data, remaining_hours)
            return session_data

        except (ValueError, TypeError):
            return None

    def invalidate_token(self, token: str) -> None:
        """Уничтожает сессию (logout)."""
        self._delete_session(token)

    def cleanup_expired(self) -> int:
        """Redis TTL автоматически удаляет истёкшие. Для dict — ручная очистка."""
        if self._redis:
            return 0
        now = datetime.now()
        expired = [
            t for t, d in self._fallback_sessions.items()
            if datetime.fromisoformat(d['expires_at']) < now
        ]
        for t in expired:
            del self._fallback_sessions[t]
        return len(expired)

    def _store_session(
        self, token: str, data: dict, expires_hours: int
    ) -> None:
        """Сохраняет сессию в Redis или fallback dict."""
        if self._redis:
            try:
                key = self._session_key(token)
                self._redis.setex(
                    key, expires_hours * 3600, json.dumps(data, default=str)
                )
                return
            except Exception as e:
                logger.warning(f"Redis write failed: {e}")
        self._fallback_sessions[token] = data

    def _get_session(self, token: str) -> Optional[dict]:
        """Читает сессию из Redis или fallback dict."""
        if self._redis:
            try:
                key = self._session_key(token)
                raw = self._redis.get(key)
                if raw:
                    return json.loads(raw)
                return None
            except Exception as e:
                logger.warning(f"Redis read failed: {e}")
        return self._fallback_sessions.get(token)

    def _delete_session(self, token: str) -> None:
        """Удаляет сессию из Redis или fallback dict."""
        if self._redis:
            try:
                key = self._session_key(token)
                self._redis.delete(key)
            except Exception as e:
                logger.warning(f"Redis delete failed: {e}")
        self._fallback_sessions.pop(token, None)

    def _sign(self, payload: str) -> str:
        return hmac.new(
            self.secret_key.encode('utf-8'),
            payload.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

    def _verify_signature(self, payload: str, signature: str) -> bool:
        expected = self._sign(payload)
        return hmac.compare_digest(expected, signature)


session_manager = SessionManager()


def get_current_user_from_token(token: str) -> Optional[User]:
    """Получает пользователя из токена сессии."""
    session_data = session_manager.verify_token(token)
    if not session_data:
        return None

    try:
        user = User.get(User.id == session_data['user_id'])
        return user
    except Exception:
        return None
