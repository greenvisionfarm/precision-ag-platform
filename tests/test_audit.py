"""
Тесты аудит-журнала: логирование изменений полей.
"""
import json

import pytest
from tornado.httpclient import HTTPRequest

from db import Field, Owner
from src.models.field import AuditLog


@pytest.fixture
def field_with_owner(test_db, test_company, test_user):
    """Создаёт поле и владельца для тестов аудита."""
    owner = Owner.create(name='Test Owner', company=test_company)
    field = Field.create(
        name='Test Field',
        geometry_wkt='POLYGON((0 0, 1 0, 1 1, 0 1, 0 0))',
        company_id=test_company.id,
        owner_id=owner.id,
    )
    return {'field': field, 'owner': owner, 'user': test_user, 'company': test_company}


class TestAuditLogging:
    """Тесты записи аудит-логов при изменении полей."""

    @pytest.mark.asyncio
    async def test_assign_owner_creates_audit_log(self, http_server_client, field_with_owner):
        """Назначение владельца должно создавать запись в auditlog."""
        client, base = http_server_client

        body = json.dumps({'email': field_with_owner['user'].email, 'password': 'testpassword123'})
        req = HTTPRequest(f'{base}/api/auth/login', method='POST',
                          headers={'Content-Type': 'application/json'}, body=body)
        resp = await client.fetch(req)
        cookie = resp.headers.get('Set-Cookie', '')

        field_id = field_with_owner['field'].id
        new_owner = Owner.create(name='New Owner', company=field_with_owner['company'])

        body = json.dumps({'owner_id': str(new_owner.id)})
        req = HTTPRequest(f'{base}/api/field/assign_owner/{field_id}', method='PUT',
                          headers={'Cookie': cookie, 'Content-Type': 'application/json'}, body=body)
        resp = await client.fetch(req)
        assert resp.code == 200

        logs = AuditLog.select().where(
            (AuditLog.action == 'assign_owner') & (AuditLog.entity_id == field_id)
        )
        assert logs.count() == 1
        log = logs.first()
        assert log.entity_type == 'field'
        assert log.user_email == field_with_owner['user'].email

    @pytest.mark.asyncio
    async def test_rename_creates_audit_log(self, http_server_client, field_with_owner):
        """Переименование поля должно создавать запись."""
        client, base = http_server_client

        body = json.dumps({'email': field_with_owner['user'].email, 'password': 'testpassword123'})
        req = HTTPRequest(f'{base}/api/auth/login', method='POST',
                          headers={'Content-Type': 'application/json'}, body=body)
        resp = await client.fetch(req)
        cookie = resp.headers.get('Set-Cookie', '')

        field_id = field_with_owner['field'].id
        body = json.dumps({'new_name': 'Renamed Field'})
        req = HTTPRequest(f'{base}/api/field/rename/{field_id}', method='PUT',
                          headers={'Cookie': cookie, 'Content-Type': 'application/json'}, body=body)
        resp = await client.fetch(req)
        assert resp.code == 200

        logs = AuditLog.select().where(
            (AuditLog.action == 'rename') & (AuditLog.entity_id == field_id)
        )
        assert logs.count() == 1
        log = logs.first()
        details = json.loads(log.details)
        assert details['old_name'] == 'Test Field'
        assert details['new_name'] == 'Renamed Field'

    @pytest.mark.asyncio
    async def test_audit_logs_api_requires_auth(self, http_server_client):
        """GET /api/audit-logs без авторизации → 401."""
        client, base = http_server_client
        with pytest.raises(Exception) as exc_info:
            await client.fetch(f'{base}/api/audit-logs')
        assert exc_info.value.code == 401

    @pytest.mark.asyncio
    async def test_audit_logs_api_returns_data(self, http_server_client, field_with_owner):
        """GET /api/audit-logs с авторизацией → список логов."""
        client, base = http_server_client

        body = json.dumps({'email': field_with_owner['user'].email, 'password': 'testpassword123'})
        req = HTTPRequest(f'{base}/api/auth/login', method='POST',
                          headers={'Content-Type': 'application/json'}, body=body)
        resp = await client.fetch(req)
        cookie = resp.headers.get('Set-Cookie', '')

        # Сначала делаем изменение чтобы был лог
        field_id = field_with_owner['field'].id
        body = json.dumps({'new_name': 'Logged Field'})
        req = HTTPRequest(f'{base}/api/field/rename/{field_id}', method='PUT',
                          headers={'Cookie': cookie, 'Content-Type': 'application/json'}, body=body)
        await client.fetch(req)

        # Теперь запрашиваем логи
        req = HTTPRequest(f'{base}/api/audit-logs?limit=5', method='GET', headers={'Cookie': cookie})
        resp = await client.fetch(req)
        assert resp.code == 200

        data = json.loads(resp.body)
        assert 'logs' in data
        assert len(data['logs']) >= 1
        assert data['logs'][0]['action'] == 'rename'
