"""
Тесты API для работы с полями: авторизация → получение данных таблицы полей.

Регрессионный тест для бага: после логина DataTables не загружает поля.
"""
import json

import pytest
from tornado.httpclient import HTTPRequest

from db import Field


@pytest.fixture
def company_with_fields(test_db):
    """Создаёт компанию, пользователя и 3 тестовых поля."""
    from src.models.auth import Company, User, UserRole

    company = Company.create(name='Test Agro', slug='test-agro')
    user = User.create_user(
        email='farmer@test.com',
        password='farm123',
        company=company,
        role=UserRole.OWNER
    )

    # Создаём поля
    Field.create(name='Поле A', area=10.5, company_id=company.id, geometry_wkt='POLYGON((0 0, 1 0, 1 1, 0 1, 0 0))')
    Field.create(name='Поле B', area=20.3, company_id=company.id, geometry_wkt='POLYGON((2 0, 3 0, 3 1, 2 1, 2 0))')
    Field.create(name='Поле C', area=5.0, company_id=company.id, geometry_wkt='POLYGON((4 0, 5 0, 5 1, 4 1, 4 0))')

    return {'user': user, 'company': company}


class TestFieldsApiAuth:
    """Тесты авторизации для API полей."""

    @pytest.mark.asyncio
    async def test_fields_data_requires_auth(self, http_server_client):
        """GET /api/fields_data без авторизации → 401."""
        client, base = http_server_client
        with pytest.raises(Exception) as exc_info:
            await client.fetch(f'{base}/api/fields_data')
        assert exc_info.value.code == 401

    @pytest.mark.asyncio
    async def test_login_returns_user_data(self, http_server_client, company_with_fields):
        """POST /api/auth/login → 200 с user объектом."""
        client, base = http_server_client
        body = json.dumps({'email': 'farmer@test.com', 'password': 'farm123'})
        req = HTTPRequest(
            f'{base}/api/auth/login',
            method='POST',
            headers={'Content-Type': 'application/json'},
            body=body
        )
        resp = await client.fetch(req)
        assert resp.code == 200
        data = json.loads(resp.body)
        assert 'user' in data
        assert data['user']['email'] == 'farmer@test.com'

    @pytest.mark.asyncio
    async def test_fields_data_with_auth_cookie(self, http_server_client, company_with_fields):
        """
        Полный сценарий: логин → cookie → GET /api/fields_data → данные с полями.

        Это ключевой тест: он воспроизводит то что делает DataTables в браузере.
        """
        client, base = http_server_client

        # 1. Логинимся, получаем cookie
        body = json.dumps({'email': 'farmer@test.com', 'password': 'farm123'})
        req = HTTPRequest(
            f'{base}/api/auth/login',
            method='POST',
            headers={'Content-Type': 'application/json'},
            body=body
        )
        resp = await client.fetch(req)
        assert resp.code == 200

        # Извлекаем cookie
        cookie_header = resp.headers.get('Set-Cookie', '')
        assert cookie_header, 'Login response must set cookies'

        # 2. Запрашиваем поля с cookie
        req2 = HTTPRequest(
            f'{base}/api/fields_data',
            method='GET',
            headers={'Cookie': cookie_header}
        )
        resp2 = await client.fetch(req2)
        assert resp2.code == 200

        data = json.loads(resp2.body)
        assert 'data' in data
        assert len(data['data']) == 3
        names = [f['name'] for f in data['data']]
        assert 'Поле A' in names
        assert 'Поле B' in names
        assert 'Поле C' in names

    @pytest.mark.asyncio
    async def test_profile_after_login(self, http_server_client, company_with_fields):
        """GET /api/auth/profile после логина возвращает user + company."""
        client, base = http_server_client

        body = json.dumps({'email': 'farmer@test.com', 'password': 'farm123'})
        req = HTTPRequest(
            f'{base}/api/auth/login',
            method='POST',
            headers={'Content-Type': 'application/json'},
            body=body
        )
        resp = await client.fetch(req)
        cookie = resp.headers.get('Set-Cookie', '')

        req2 = HTTPRequest(
            f'{base}/api/auth/profile',
            method='GET',
            headers={'Cookie': cookie}
        )
        resp2 = await client.fetch(req2)
        assert resp2.code == 200

        data = json.loads(resp2.body)
        assert 'user' in data
        assert data['user']['email'] == 'farmer@test.com'
        assert 'company' in data['user']
        assert data['user']['company']['name'] == 'Test Agro'

    @pytest.mark.asyncio
    async def test_owners_api_with_auth(self, http_server_client, company_with_fields):
        """GET /api/owners с авторизацией → список владельцев."""
        client, base = http_server_client

        body = json.dumps({'email': 'farmer@test.com', 'password': 'farm123'})
        req = HTTPRequest(
            f'{base}/api/auth/login',
            method='POST',
            headers={'Content-Type': 'application/json'},
            body=body
        )
        resp = await client.fetch(req)
        cookie = resp.headers.get('Set-Cookie', '')

        req2 = HTTPRequest(
            f'{base}/api/owners',
            method='GET',
            headers={'Cookie': cookie}
        )
        resp2 = await client.fetch(req2)
        assert resp2.code == 200

        data = json.loads(resp2.body)
        assert 'data' in data
        assert isinstance(data['data'], list)
