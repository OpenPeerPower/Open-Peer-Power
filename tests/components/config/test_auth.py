"""Test config entries API."""
import pytest

from openpeerpower.auth import models as auth_models
from openpeerpower.components.config import auth as auth_config

from tests.common import CLIENT_ID, MockGroup, MockUser


@pytest.fixture(autouse=True)
def setup_config(opp, aiohttp_client):
    """Fixture that sets up the auth provider openpeerpower module."""
    opp.loop.run_until_complete(auth_config.async_setup(opp))


async def test_list_requires_admin(opp, opp_ws_client, opp_read_only_access_token):
    """Test get users requires auth."""
    client = await opp_ws_client(opp, opp_read_only_access_token)

    await client.send_json({"id": 5, "type": auth_config.WS_TYPE_LIST})

    result = await client.receive_json()
    assert not result["success"], result
    assert result["error"]["code"] == "unauthorized"


async def test_list(opp, opp_ws_client, opp_admin_user):
    """Test get users."""
    group = MockGroup().add_to_opp(opp)

    owner = MockUser(
        id="abc", name="Test Owner", is_owner=True, groups=[group]
    ).add_to_opp(opp)

    owner.credentials.append(
        auth_models.Credentials(
            auth_provider_type="openpeerpower", auth_provider_id=None, data={}
        )
    )

    system = MockUser(id="efg", name="Test Opp.io", system_generated=True).add_to_opp(
        opp
    )

    inactive = MockUser(
        id="hij", name="Inactive User", is_active=False, groups=[group]
    ).add_to_opp(opp)

    refresh_token = await opp.auth.async_create_refresh_token(owner, CLIENT_ID)
    access_token = opp.auth.async_create_access_token(refresh_token)

    client = await opp_ws_client(opp, access_token)
    await client.send_json({"id": 5, "type": auth_config.WS_TYPE_LIST})

    result = await client.receive_json()
    assert result["success"], result
    data = result["result"]
    assert len(data) == 4
    assert data[0] == {
        "id": opp_admin_user.id,
        "name": "Mock User",
        "is_owner": False,
        "is_active": True,
        "system_generated": False,
        "group_ids": [group.id for group in opp_admin_user.groups],
        "credentials": [],
    }
    assert data[1] == {
        "id": owner.id,
        "name": "Test Owner",
        "is_owner": True,
        "is_active": True,
        "system_generated": False,
        "group_ids": [group.id for group in owner.groups],
        "credentials": [{"type": "openpeerpower"}],
    }
    assert data[2] == {
        "id": system.id,
        "name": "Test Opp.io",
        "is_owner": False,
        "is_active": True,
        "system_generated": True,
        "group_ids": [],
        "credentials": [],
    }
    assert data[3] == {
        "id": inactive.id,
        "name": "Inactive User",
        "is_owner": False,
        "is_active": False,
        "system_generated": False,
        "group_ids": [group.id for group in inactive.groups],
        "credentials": [],
    }


async def test_delete_requires_admin(opp, opp_ws_client, opp_read_only_access_token):
    """Test delete command requires an admin."""
    client = await opp_ws_client(opp, opp_read_only_access_token)

    await client.send_json(
        {"id": 5, "type": auth_config.WS_TYPE_DELETE, "user_id": "abcd"}
    )

    result = await client.receive_json()
    assert not result["success"], result
    assert result["error"]["code"] == "unauthorized"


async def test_delete_unable_self_account(opp, opp_ws_client, opp_access_token):
    """Test we cannot delete our own account."""
    client = await opp_ws_client(opp, opp_access_token)
    refresh_token = await opp.auth.async_validate_access_token(opp_access_token)

    await client.send_json(
        {"id": 5, "type": auth_config.WS_TYPE_DELETE, "user_id": refresh_token.user.id}
    )

    result = await client.receive_json()
    assert not result["success"], result
    assert result["error"]["code"] == "no_delete_self"


async def test_delete_unknown_user(opp, opp_ws_client, opp_access_token):
    """Test we cannot delete an unknown user."""
    client = await opp_ws_client(opp, opp_access_token)

    await client.send_json(
        {"id": 5, "type": auth_config.WS_TYPE_DELETE, "user_id": "abcd"}
    )

    result = await client.receive_json()
    assert not result["success"], result
    assert result["error"]["code"] == "not_found"


async def test_delete(opp, opp_ws_client, opp_access_token):
    """Test delete command works."""
    client = await opp_ws_client(opp, opp_access_token)
    test_user = MockUser(id="efg").add_to_opp(opp)

    assert len(await opp.auth.async_get_users()) == 2

    await client.send_json(
        {"id": 5, "type": auth_config.WS_TYPE_DELETE, "user_id": test_user.id}
    )

    result = await client.receive_json()
    assert result["success"], result
    assert len(await opp.auth.async_get_users()) == 1


async def test_create(opp, opp_ws_client, opp_access_token):
    """Test create command works."""
    client = await opp_ws_client(opp, opp_access_token)

    assert len(await opp.auth.async_get_users()) == 1

    await client.send_json(
        {"id": 5, "type": auth_config.WS_TYPE_CREATE, "name": "Paulus"}
    )

    result = await client.receive_json()
    assert result["success"], result
    assert len(await opp.auth.async_get_users()) == 2
    data_user = result["result"]["user"]
    user = await opp.auth.async_get_user(data_user["id"])
    assert user is not None
    assert user.name == data_user["name"]
    assert user.is_active
    assert not user.is_owner
    assert not user.system_generated


async def test_create_requires_admin(opp, opp_ws_client, opp_read_only_access_token):
    """Test create command requires an admin."""
    client = await opp_ws_client(opp, opp_read_only_access_token)

    await client.send_json({"id": 5, "type": auth_config.WS_TYPE_CREATE, "name": "YO"})

    result = await client.receive_json()
    assert not result["success"], result
    assert result["error"]["code"] == "unauthorized"


async def test_update(opp, opp_ws_client):
    """Test update command works."""
    client = await opp_ws_client(opp)

    user = await opp.auth.async_create_user("Test user")

    await client.send_json(
        {
            "id": 5,
            "type": "config/auth/update",
            "user_id": user.id,
            "name": "Updated name",
            "group_ids": ["system-read-only"],
        }
    )

    result = await client.receive_json()
    assert result["success"], result
    data_user = result["result"]["user"]

    assert user.name == "Updated name"
    assert data_user["name"] == "Updated name"
    assert len(user.groups) == 1
    assert user.groups[0].id == "system-read-only"
    assert data_user["group_ids"] == ["system-read-only"]


async def test_update_requires_admin(opp, opp_ws_client, opp_read_only_access_token):
    """Test update command requires an admin."""
    client = await opp_ws_client(opp, opp_read_only_access_token)

    user = await opp.auth.async_create_user("Test user")

    await client.send_json(
        {
            "id": 5,
            "type": "config/auth/update",
            "user_id": user.id,
            "name": "Updated name",
        }
    )

    result = await client.receive_json()
    assert not result["success"], result
    assert result["error"]["code"] == "unauthorized"
    assert user.name == "Test user"


async def test_update_system_generated(opp, opp_ws_client):
    """Test update command cannot update a system generated."""
    client = await opp_ws_client(opp)

    user = await opp.auth.async_create_system_user("Test user")

    await client.send_json(
        {
            "id": 5,
            "type": "config/auth/update",
            "user_id": user.id,
            "name": "Updated name",
        }
    )

    result = await client.receive_json()
    assert not result["success"], result
    assert result["error"]["code"] == "cannot_modify_system_generated"
    assert user.name == "Test user"
