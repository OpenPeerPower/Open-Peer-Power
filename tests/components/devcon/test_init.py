"""Test the Devcon initialization."""
from unittest.mock import patch

from openpeerpower.components import frontend, devcon
from openpeerpower.setup import async_setup_component

from tests.common import async_capture_events, get_system_health_info


async def test_devcon_from_storage(opp, opp_ws_client, opp_storage):
    """Test we load devcon config from storage."""
    assert await async_setup_component(opp, "devcon", {})
    assert opp.data[frontend.DATA_PANELS]["devcon"].config == {"mode": "storage"}

    client = await opp_ws_client(opp)

    # Fetch data
    await client.send_json({"id": 5, "type": "devcon/config"})
    response = await client.receive_json()
    assert not response["success"]
    assert response["error"]["code"] == "config_not_found"

    # Store new config
    events = async_capture_events(opp, devcon.EVENT_LOVELACE_UPDATED)

    await client.send_json(
        {"id": 6, "type": "devcon/config/save", "config": {"yo": "hello"}}
    )
    response = await client.receive_json()
    assert response["success"]
    assert opp_storage[devcon.STORAGE_KEY]["data"] == {"config": {"yo": "hello"}}
    assert len(events) == 1

    # Load new config
    await client.send_json({"id": 7, "type": "devcon/config"})
    response = await client.receive_json()
    assert response["success"]

    assert response["result"] == {"yo": "hello"}

    # Test with safe mode
    opp.config.safe_mode = True
    await client.send_json({"id": 8, "type": "devcon/config"})
    response = await client.receive_json()
    assert not response["success"]
    assert response["error"]["code"] == "config_not_found"


async def test_devcon_from_storage_save_before_load(
    opp, opp_ws_client, opp_storage
):
    """Test we can load devcon config from storage."""
    assert await async_setup_component(opp, "devcon", {})
    client = await opp_ws_client(opp)

    # Store new config
    await client.send_json(
        {"id": 6, "type": "devcon/config/save", "config": {"yo": "hello"}}
    )
    response = await client.receive_json()
    assert response["success"]
    assert opp_storage[devcon.STORAGE_KEY]["data"] == {"config": {"yo": "hello"}}


async def test_devcon_from_storage_delete(opp, opp_ws_client, opp_storage):
    """Test we delete devcon config from storage."""
    assert await async_setup_component(opp, "devcon", {})
    client = await opp_ws_client(opp)

    # Store new config
    await client.send_json(
        {"id": 6, "type": "devcon/config/save", "config": {"yo": "hello"}}
    )
    response = await client.receive_json()
    assert response["success"]
    assert opp_storage[devcon.STORAGE_KEY]["data"] == {"config": {"yo": "hello"}}

    # Delete config
    await client.send_json({"id": 7, "type": "devcon/config/delete"})
    response = await client.receive_json()
    assert response["success"]
    assert opp_storage[devcon.STORAGE_KEY]["data"] == {"config": None}

    # Fetch data
    await client.send_json({"id": 8, "type": "devcon/config"})
    response = await client.receive_json()
    assert not response["success"]
    assert response["error"]["code"] == "config_not_found"


async def test_devcon_from_yaml(opp, opp_ws_client):
    """Test we load devcon config from yaml."""
    assert await async_setup_component(opp, "devcon", {"devcon": {"mode": "YAML"}})
    assert opp.data[frontend.DATA_PANELS]["devcon"].config == {"mode": "yaml"}

    client = await opp_ws_client(opp)

    # Fetch data
    await client.send_json({"id": 5, "type": "devcon/config"})
    response = await client.receive_json()
    assert not response["success"]

    assert response["error"]["code"] == "config_not_found"

    # Store new config not allowed
    await client.send_json(
        {"id": 6, "type": "devcon/config/save", "config": {"yo": "hello"}}
    )
    response = await client.receive_json()
    assert not response["success"]

    # Patch data
    events = async_capture_events(opp, devcon.EVENT_LOVELACE_UPDATED)

    with patch(
        "openpeerpower.components.devcon.load_yaml", return_value={"hello": "yo"}
    ):
        await client.send_json({"id": 7, "type": "devcon/config"})
        response = await client.receive_json()

    assert response["success"]
    assert response["result"] == {"hello": "yo"}

    assert len(events) == 0

    # Fake new data to see we fire event
    with patch(
        "openpeerpower.components.devcon.load_yaml", return_value={"hello": "yo2"}
    ):
        await client.send_json({"id": 8, "type": "devcon/config", "force": True})
        response = await client.receive_json()

    assert response["success"]
    assert response["result"] == {"hello": "yo2"}

    assert len(events) == 1


async def test_system_health_info_autogen(opp):
    """Test system health info endpoint."""
    assert await async_setup_component(opp, "devcon", {})
    info = await get_system_health_info(opp, "devcon")
    assert info == {"mode": "auto-gen"}


async def test_system_health_info_storage(opp, opp_storage):
    """Test system health info endpoint."""
    opp_storage[devcon.STORAGE_KEY] = {
        "key": "devcon",
        "version": 1,
        "data": {"config": {"resources": [], "views": []}},
    }
    assert await async_setup_component(opp, "devcon", {})
    info = await get_system_health_info(opp, "devcon")
    assert info == {"mode": "storage", "resources": 0, "views": 0}


async def test_system_health_info_yaml(opp):
    """Test system health info endpoint."""
    assert await async_setup_component(opp, "devcon", {"devcon": {"mode": "YAML"}})
    with patch(
        "openpeerpower.components.devcon.load_yaml",
        return_value={"views": [{"cards": []}]},
    ):
        info = await get_system_health_info(opp, "devcon")
    assert info == {"mode": "yaml", "resources": 0, "views": 1}


async def test_system_health_info_yaml_not_found(opp):
    """Test system health info endpoint."""
    assert await async_setup_component(opp, "devcon", {"devcon": {"mode": "YAML"}})
    info = await get_system_health_info(opp, "devcon")
    assert info == {
        "mode": "yaml",
        "error": "{} not found".format(opp.config.path("ui-devcon.yaml")),
    }
