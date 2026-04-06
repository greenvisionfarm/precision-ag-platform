"""
Модели аутентификации и мульти-тенантности.
"""
import hashlib
import os
from datetime import datetime
from typing import Optional

from peewee import (
    BooleanField,
    CharField,
    DateTimeField,
    ForeignKeyField,
    Model,
    SqliteDatabase,
    TextField,
)

# Используем ту же БД, что и в основном приложении
from db import database


class Company(Model):
    """
    Модель компании (тенанта).
    Каждая компания имеет изолированные данные (поля, сканы, зоны).
    """
    name = CharField(unique=True, help_text="Название компании")
    slug = CharField(unique=True, index=True, help_text="Уникальный идентификатор (URL-friendly)")
    created_at = DateTimeField(default=datetime.now, help_text="Дата создания компании")
    is_active = BooleanField(default=True, help_text="Активна ли компания")
    settings_json = TextField(null=True, help_text="Настройки компании в формате JSON")

    class Meta:
        table_name = 'company'
        db_table = 'company'

    def __str__(self) -> str:
        return self.name


class UserRole:
    """
    Роли пользователей в системе.
    """
    OWNER = 'owner'       # Владелец компании (полный доступ)
    ADMIN = 'admin'       # Администратор (управление пользователями и данными)
    AGRONOMIST = 'agronomist'  # Агроном (просмотр и анализ данных)
    OPERATOR = 'operator'  # Оператор (загрузка данных, экспорт карт)
    VIEWER = 'viewer'     # Наблюдатель (только просмотр)


class User(Model):
    """
    Модель пользователя системы.
    Пользователь принадлежит одной компании и имеет роль.
    """
    email = CharField(unique=True, index=True, help_text="Email для входа")
    password_hash = CharField(help_text="Хэш пароля (SHA-256 + salt)")
    password_salt = CharField(help_text="Соль для хэширования пароля")
    
    first_name = CharField(null=True, help_text="Имя")
    last_name = CharField(null=True, help_text="Фамилия")
    
    company = ForeignKeyField(
        Company, 
        backref='users', 
        on_delete='CASCADE',
        help_text="Компания, к которой принадлежит пользователь"
    )
    role = CharField(
        default=UserRole.OPERATOR,
        help_text="Роль пользователя в компании"
    )
    
    is_active = BooleanField(default=True, help_text="Активен ли пользователь")
    is_verified = BooleanField(default=False, help_text="Подтверждён ли email")
    created_at = DateTimeField(default=datetime.now, help_text="Дата регистрации")
    last_login = DateTimeField(null=True, help_text="Последний вход")
    
    # Настройки пользователя
    language = CharField(default='ru', help_text="Язык интерфейса (ru/en/sk)")
    settings_json = TextField(null=True, help_text="Персональные настройки в JSON")

    class Meta:
        table_name = 'user'
        db_table = 'user'

    def __str__(self) -> str:
        return f"{self.email} ({self.company.name})"

    @staticmethod
    def hash_password(password: str, salt: Optional[str] = None) -> tuple[str, str]:
        """
        Хэширует пароль с использованием соли.
        
        Args:
            password: Пароль в открытом виде
            salt: Соль (если None, будет сгенерирована новая)
            
        Returns:
            Кортеж (password_hash, salt)
        """
        if salt is None:
            salt = os.urandom(32).hex()
        
        # Используем SHA-256 с солью
        hashed = hashlib.sha256((password + salt).encode('utf-8')).hexdigest()
        return hashed, salt

    @classmethod
    def create_user(
        cls,
        email: str,
        password: str,
        company: Company,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        role: str = UserRole.OPERATOR,
        language: str = 'ru'
    ) -> 'User':
        """
        Создаёт нового пользователя с хэшированным паролем.
        
        Args:
            email: Email пользователя
            password: Пароль в открытом виде
            company: Компания, к которой принадлежит пользователь
            first_name: Имя (опционально)
            last_name: Фамилия (опционально)
            role: Роль пользователя
            language: Язык интерфейса
            
        Returns:
            Созданный объект User
        """
        password_hash, salt = cls.hash_password(password)
        return cls.create(
            email=email,
            password_hash=password_hash,
            password_salt=salt,
            first_name=first_name,
            last_name=last_name,
            company=company,
            role=role,
            language=language
        )

    def verify_password(self, password: str) -> bool:
        """
        Проверяет правильность пароля.
        
        Args:
            password: Пароль для проверки
            
        Returns:
            True если пароль верный
        """
        password_hash, _ = self.hash_password(password, self.password_salt)
        return password_hash == self.password_hash

    def has_permission(self, required_role: str) -> bool:
        """
        Проверяет, имеет ли пользователь достаточные права.
        
        Args:
            required_role: Требуемая роль для доступа
            
        Returns:
            True если пользователь имеет достаточные права
        """
        role_hierarchy = {
            UserRole.VIEWER: 1,
            UserRole.OPERATOR: 2,
            UserRole.AGRONOMIST: 3,
            UserRole.ADMIN: 4,
            UserRole.OWNER: 5,
        }
        return role_hierarchy.get(self.role, 0) >= role_hierarchy.get(required_role, 0)

    def is_owner(self) -> bool:
        """Проверяет, является ли пользователь владельцем компании."""
        return self.role == UserRole.OWNER

    def is_admin(self) -> bool:
        """Проверяет, является ли пользователь администратором."""
        return self.role == UserRole.ADMIN
