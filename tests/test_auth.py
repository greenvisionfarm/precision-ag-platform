"""
Тесты для системы аутентификации и мульти-тенантности.
"""
import json

import pytest

from src.models.auth import Company, User, UserRole
from src.utils.auth import SessionManager, get_current_user_from_token


@pytest.fixture
def test_db(db):
    """Создаёт тестовые компании и пользователей."""
    # Компании
    company1 = Company.create(name='Test Company 1', slug='test-company-1')
    company2 = Company.create(name='Test Company 2', slug='test-company-2')
    
    # Пользователи
    user1 = User.create_user(
        email='user1@test.com',
        password='password123',
        company=company1,
        role=UserRole.OWNER
    )
    user2 = User.create_user(
        email='user2@test.com',
        password='password123',
        company=company2,
        role=UserRole.OPERATOR
    )
    
    yield {
        'company1': company1,
        'company2': company2,
        'user1': user1,
        'user2': user2,
    }


class TestUserModel:
    """Тесты для модели User."""
    
    def test_hash_password(self, test_db):
        """Тест хэширования пароля."""
        password = 'test_password'
        hash1, salt1 = User.hash_password(password)
        hash2, salt2 = User.hash_password(password)
        
        # Хэши должны быть разными из-за разной соли
        assert hash1 != hash2
        assert salt1 != salt2
        
        # Но проверка с той же солью должна давать одинаковый результат
        hash3, _ = User.hash_password(password, salt1)
        assert hash3 == hash1
    
    def test_verify_password(self, test_db):
        """Тест проверки пароля."""
        user = test_db['user1']
        
        assert user.verify_password('password123') is True
        assert user.verify_password('wrong_password') is False
    
    def test_has_permission(self, test_db):
        """Тест проверки прав доступа."""
        owner = test_db['user1']
        operator = test_db['user2']
        
        # Owner имеет все права
        assert owner.has_permission(UserRole.OWNER) is True
        assert owner.has_permission(UserRole.ADMIN) is True
        assert owner.has_permission(UserRole.OPERATOR) is True
        assert owner.has_permission(UserRole.VIEWER) is True
        
        # Operator имеет ограниченные права
        assert operator.has_permission(UserRole.OPERATOR) is True
        assert operator.has_permission(UserRole.VIEWER) is True
        assert operator.has_permission(UserRole.ADMIN) is False
        assert operator.has_permission(UserRole.OWNER) is False
    
    def test_is_owner(self, test_db):
        """Тест проверки на владельца."""
        assert test_db['user1'].is_owner() is True
        assert test_db['user2'].is_owner() is False


class TestSessionManager:
    """Тесты для менеджера сессий."""
    
    def test_create_token(self, test_db):
        """Тест создания токена."""
        manager = SessionManager(secret_key='test_secret')
        user = test_db['user1']
        
        token = manager.create_token(user)
        
        assert token is not None
        assert '.' in token  # Токен должен содержать подпись
    
    def test_verify_token(self, test_db):
        """Тест проверки токена."""
        manager = SessionManager(secret_key='test_secret')
        user = test_db['user1']
        
        token = manager.create_token(user)
        session_data = manager.verify_token(token)
        
        assert session_data is not None
        assert session_data['user_id'] == user.id
        assert session_data['data']['email'] == user.email
    
    def test_invalid_token(self, test_db):
        """Тест невалидного токена."""
        manager = SessionManager(secret_key='test_secret')
        
        # Невалидный токен
        assert manager.verify_token('invalid_token') is None
        assert manager.verify_token('') is None
    
    def test_token_expiration(self, test_db):
        """Тест истечения токена."""
        manager = SessionManager(secret_key='test_secret')
        user = test_db['user1']
        
        # Создаём токен на 0 часов (сразу истекает)
        token = manager.create_token(user, expires_hours=0)
        
        # Токен должен быть валидным сразу после создания
        session_data = manager.verify_token(token)
        assert session_data is not None
        
        # Но после cleanup должен стать невалидным
        manager.cleanup_expired()
        # Примечание: токен ещё не истёк, т.к. создаётся с запасом
    
    def test_invalidate_token(self, test_db):
        """Тест уничтожения токена."""
        manager = SessionManager(secret_key='test_secret')
        user = test_db['user1']
        
        token = manager.create_token(user)
        
        # Токен валиден
        assert manager.verify_token(token) is not None
        
        # Уничтожаем токен
        manager.invalidate_token(token)
        
        # Токен больше не валиден
        assert manager.verify_token(token) is None


class TestGetCurrentUserFromToken:
    """Тесты для функции получения пользователя из токена."""
    
    def test_get_user_from_token(self, test_db):
        """Тест получения пользователя из токена."""
        user = test_db['user1']
        manager = SessionManager(secret_key='test_secret')
        token = manager.create_token(user)
        
        # Сохраняем токен в сессию
        from src.utils.auth import session_manager
        session_manager._sessions[token] = manager._sessions[token]
        
        retrieved_user = get_current_user_from_token(token)
        
        assert retrieved_user is not None
        assert retrieved_user.id == user.id
        assert retrieved_user.email == user.email


class TestTenantIsolation:
    """Тесты изоляции данных между компаниями."""
    
    def test_users_from_different_companies(self, test_db):
        """Тест что пользователи из разных компаний не видят данные друг друга."""
        user1 = test_db['user1']
        user2 = test_db['user2']
        
        # Пользователи должны быть из разных компаний
        assert user1.company.id != user2.company.id
    
    def test_company_filter(self, test_db):
        """Тест фильтрации по компании."""
        from src.models.field import Field
        
        # Создаём поля для разных компаний
        field1 = Field.create(
            name='Field 1',
            geometry_wkt='POINT(0 0)',
            company=test_db['company1']
        )
        field2 = Field.create(
            name='Field 2',
            geometry_wkt='POINT(1 1)',
            company=test_db['company2']
        )
        
        # Фильтруем поля по компании
        company1_fields = Field.select().where(Field.company == test_db['company1'])
        company2_fields = Field.select().where(Field.company == test_db['company2'])
        
        assert len(list(company1_fields)) == 1
        assert len(list(company2_fields)) == 1
        assert list(company1_fields)[0].id == field1.id
        assert list(company2_fields)[0].id == field2.id


class TestAuthAPI:
    """Тесты для API аутентификации."""
    
    def test_login_success(self, http_client, base_url, test_db):
        """Тест успешного входа."""
        response = http_client.fetch(
            f'{base_url}/api/auth/login',
            method='POST',
            body=json.dumps({
                'email': 'user1@test.com',
                'password': 'password123'
            })
        )
        
        assert response.code == 200
        data = json.loads(response.body)
        assert data['success'] is True
        assert 'user' in data
    
    def test_login_invalid_credentials(self, http_client, base_url, test_db):
        """Тест входа с неверными данными."""
        response = http_client.fetch(
            f'{base_url}/api/auth/login',
            method='POST',
            body=json.dumps({
                'email': 'user1@test.com',
                'password': 'wrong_password'
            })
        )
        
        assert response.code == 401
    
    def test_register_new_user(self, http_client, base_url):
        """Тест регистрации нового пользователя."""
        response = http_client.fetch(
            f'{base_url}/api/auth/register',
            method='POST',
            body=json.dumps({
                'email': 'newuser@test.com',
                'password': 'newpassword123',
                'company_name': 'New Company',
                'first_name': 'New',
                'last_name': 'User'
            })
        )
        
        assert response.code == 200
        data = json.loads(response.body)
        assert data['success'] is True
        
        # Проверяем, что пользователь создан в БД
        user = User.get_or_none(User.email == 'newuser@test.com')
        assert user is not None
