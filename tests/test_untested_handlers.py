"""
Тесты для field_commands, owner_handlers, journal_handlers.
"""
import json
import pytest
from unittest.mock import MagicMock

from db import Field
from src.models.field import Owner
from src.handlers.field_commands import (
    FIELD_COMMANDS, RenameCommand, AssignOwnerCommand,
    UpdateDetailsCommand, UpdateGeometryCommand,
    get_command, get_available_actions,
)


class TestFieldCommands:
    """Тесты паттерна Command для обновления полей."""

    def test_get_command_returns_correct_instance(self):
        assert isinstance(get_command("rename"), RenameCommand)
        assert isinstance(get_command("assign_owner"), AssignOwnerCommand)
        assert isinstance(get_command("update_details"), UpdateDetailsCommand)
        assert isinstance(get_command("update_geometry"), UpdateGeometryCommand)

    def test_get_command_returns_none_for_unknown(self):
        assert get_command("nonexistent") is None

    def test_get_available_actions(self):
        actions = get_available_actions()
        assert "rename" in actions
        assert "assign_owner" in actions
        assert "update_details" in actions
        assert "update_geometry" in actions
        assert len(actions) == 4

    def test_rename_command(self, test_db, test_company):
        field = Field.create(
            name="Old Name",
            geometry_wkt="POLYGON ((0 0, 1 0, 1 1, 0 1, 0 0))",
            company_id=test_company.id,
        )
        RenameCommand().execute(field, {"new_name": "New Name"})
        assert field.name == "New Name"

    def test_assign_owner_command(self, test_db, test_company):
        field = Field.create(
            name="Test",
            geometry_wkt="POLYGON ((0 0, 1 0, 1 1, 0 1, 0 0))",
            company_id=test_company.id,
        )
        owner = Owner.create(name="Test Owner", company_id=test_company.id)
        AssignOwnerCommand().execute(field, {"owner_id": owner.id})
        assert field.owner_id == owner.id

    def test_assign_owner_command_clears_owner(self, test_db, test_company):
        field = Field.create(
            name="Test",
            geometry_wkt="POLYGON ((0 0, 1 0, 1 1, 0 1, 0 0))",
            company_id=test_company.id,
        )
        AssignOwnerCommand().execute(field, {"owner_id": None})
        assert field.owner_id is None

    def test_update_details_command(self, test_db, test_company):
        field = Field.create(
            name="Test",
            geometry_wkt="POLYGON ((0 0, 1 0, 1 1, 0 1, 0 0))",
            properties_json='{"area": 100}',
            company_id=test_company.id,
        )
        UpdateDetailsCommand().execute(field, {
            "land_status": "аренда",
            "parcel_number": "12345",
        })
        props = json.loads(field.properties_json)
        assert props["land_status"] == "аренда"
        assert props["parcel_number"] == "12345"
        assert props["area"] == 100


class TestOwnerHandlers:
    """Тесты handlers владельцев."""

    @pytest.mark.asyncio
    async def test_owners_requires_auth(self, http_server_client):
        client, base = http_server_client
        with pytest.raises(Exception) as exc_info:
            await client.fetch(f"{base}/api/owners")
        assert exc_info.value.code == 401

    @pytest.mark.asyncio
    async def test_owners_data_returns_list(self, http_server_client, test_company, auth_headers):
        client, base = http_server_client
        Owner.create(name="Owner A", company=test_company)
        Owner.create(name="Owner B", company=test_company)

        resp = await client.fetch(f"{base}/api/owners", headers=auth_headers)
        assert resp.code == 200
        data = json.loads(resp.body)
        assert "data" in data

    @pytest.mark.asyncio
    async def test_add_owner(self, http_server_client, test_company, auth_headers):
        client, base = http_server_client
        body = json.dumps({"name": "New Owner"})
        resp = await client.fetch(
            f"{base}/api/owner/add",
            method="POST",
            body=body,
            headers={**auth_headers, "Content-Type": "application/json"},
        )
        assert resp.code == 200

        owners = list(Owner.select().where(Owner.company == test_company))
        assert len(owners) == 1
        assert owners[0].name == "New Owner"

    @pytest.mark.asyncio
    async def test_add_owner_validation(self, http_server_client, test_company, auth_headers):
        client, base = http_server_client
        body = json.dumps({"name": ""})
        with pytest.raises(Exception) as exc_info:
            await client.fetch(
                f"{base}/api/owner/add",
                method="POST",
                body=body,
                headers={**auth_headers, "Content-Type": "application/json"},
            )
        assert exc_info.value.code == 400

    @pytest.mark.asyncio
    async def test_delete_owner(self, http_server_client, test_company, auth_headers):
        client, base = http_server_client
        owner = Owner.create(name="ToDelete", company=test_company)

        resp = await client.fetch(
            f"{base}/api/owner/delete/{owner.id}",
            method="DELETE",
            headers=auth_headers,
        )
        assert resp.code == 200
        assert Owner.select().where(Owner.id == owner.id).count() == 0
