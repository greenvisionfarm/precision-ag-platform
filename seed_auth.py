#!/usr/bin/env python3
"""
Скрипт для создания тестовых данных (пользователи, компании).
"""
import logging
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def seed_data():
    """Создаёт тестовые данные в БД."""
    # Удаляем старую БД если есть
    if os.path.exists('fields.db'):
        os.remove('fields.db')
    
    # Сначала создаём базовые таблицы через db.initialize_db
    # Временно устанавливаем test окружение чтобы разрешить инициализацию
    os.environ['FIELD_MAPPER_ENV'] = 'test'
    
    from db import database, initialize_db
    from peewee import SqliteDatabase
    
    initialize_db()
    
    # Теперь выполняем миграцию для добавления company и user
    from src.db_migrate import migrate_db
    migrate_db('fields.db')
    
    # Импортируем модели
    database = SqliteDatabase('fields.db')
    from src.models.auth import Company, User, UserRole
    
    Company._meta.database = database
    User._meta.database = database
    
    database.connect()
    
    try:
        # Создаём компании
        logger.info("Создание компаний...")
        company1 = Company.create(
            name='АгроТех',
            slug='agro-tech',
            settings_json='{"language": "ru"}'
        )
        company2 = Company.create(
            name='Green Fields s.r.o.',
            slug='green-fields',
            settings_json='{"language": "sk"}'
        )
        company3 = Company.create(
            name='Demo Farm',
            slug='demo-farm',
            settings_json='{"language": "en"}'
        )
        
        # Создаём пользователей
        logger.info("Создание пользователей...")
        
        # Пользователи для АгроТех
        User.create_user(
            email='admin@agrotech.ru',
            password='admin123',
            company=company1,
            first_name='Иван',
            last_name='Петров',
            role=UserRole.OWNER,
            language='ru'
        )
        User.create_user(
            email='agronom@agrotech.ru',
            password='user123',
            company=company1,
            first_name='Мария',
            last_name='Сидорова',
            role=UserRole.AGRONOMIST,
            language='ru'
        )
        
        # Пользователи для Green Fields
        User.create_user(
            email='admin@greenfields.sk',
            password='admin123',
            company=company2,
            first_name='Ján',
            last_name='Novák',
            role=UserRole.OWNER,
            language='sk'
        )
        User.create_user(
            email='operator@greenfields.sk',
            password='user123',
            company=company2,
            first_name='Peter',
            last_name='Kováč',
            role=UserRole.OPERATOR,
            language='sk'
        )
        
        # Пользователи для Demo Farm
        User.create_user(
            email='admin@demofarm.com',
            password='admin123',
            company=company3,
            first_name='John',
            last_name='Smith',
            role=UserRole.OWNER,
            language='en'
        )
        
        logger.info("✓ Seed данные успешно созданы!")
        logger.info("=" * 50)
        logger.info("Тестовые учётные данные:")
        logger.info("=" * 50)
        logger.info("АгроТех (RU):")
        logger.info("  admin@agrotech.ru / admin123 (Owner)")
        logger.info("  agronom@agrotech.ru / user123 (Agronomist)")
        logger.info("")
        logger.info("Green Fields (SK):")
        logger.info("  admin@greenfields.sk / admin123 (Owner)")
        logger.info("  operator@greenfields.sk / user123 (Operator)")
        logger.info("")
        logger.info("Demo Farm (EN):")
        logger.info("  admin@demofarm.com / admin123 (Owner)")
        logger.info("=" * 50)
        
    except Exception as e:
        logger.error(f"Ошибка при создании seed данных: {e}")
        raise
    finally:
        database.close()
    
    # Сбрасываем окружение
    os.environ.pop('FIELD_MAPPER_ENV', None)


if __name__ == '__main__':
    seed_data()
