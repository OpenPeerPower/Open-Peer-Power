"""Test Automation config panel."""
import json

from asynctest import patch

from openpeerpower.bootstrap import async_setup_component
from openpeerpower.components import config


async def test_get_device_config(opp, opp_client):
    """Test getting device config."""
    with patch.object(config, "SECTIONS", ["automation"]):
        await async_setup_component(opp, "config", {})

    client = await opp_client()

    def mock_read(path):
        """Mock reading data."""
        return [{"id": "sun"}, {"id": "moon"}]

    with patch("openpeerpower.components.config._read", mock_read):
        resp = await client.get("/api/config/automation/config/moon")

    assert resp.status == 200
    result = await resp.json()

    assert result == {"id": "moon"}


async def test_update_device_config(opp, opp_client):
    """Test updating device config."""
    with patch.object(config, "SECTIONS", ["automation"]):
        await async_setup_component(opp, "config", {})

    client = await opp_client()

    orig_data = [{"id": "sun"}, {"id": "moon"}]

    def mock_read(path):
        """Mock reading data."""
        return orig_data

    written = []

    def mock_write(path, data):
        """Mock writing data."""
        written.append(data)

    with patch("openpeerpower.components.config._read", mock_read), patch(
        "openpeerpower.components.config._write", mock_write
    ), patch("openpeerpower.config.async_opp_config_yaml", return_value={}):
        resp = await client.post(
            "/api/config/automation/config/moon",
            data=json.dumps({"trigger": [], "action": [], "condition": []}),
        )

    assert resp.status == 200
    result = await resp.json()
    assert result == {"result": "ok"}

    assert list(orig_data[1]) == ["id", "trigger", "condition", "action"]
    assert orig_data[1] == {"id": "moon", "trigger": [], "condition": [], "action": []}
    assert written[0] == orig_data


async def test_bad_formatted_automations(opp, opp_client):
    """Test that we handle automations without ID."""
    with patch.object(config, "SECTIONS", ["automation"]):
        await async_setup_component(opp, "config", {})

    client = await opp_client()

    orig_data = [
        {
            # No ID
            "action": {"event": "hello"}
        },
        {"id": "moon"},
    ]

    def mock_read(path):
        """Mock reading data."""
        return orig_data

    written = []

    def mock_write(path, data):
        """Mock writing data."""
        written.append(data)

    with patch("openpeerpower.components.config._read", mock_read), patch(
        "openpeerpower.components.config._write", mock_write
    ), patch("openpeerpower.config.async_opp_config_yaml", return_value={}):
        resp = await client.post(
            "/api/config/automation/config/moon",
            data=json.dumps({"trigger": [], "action": [], "condition": []}),
        )
        await opp.async_block_till_done()

    assert resp.status == 200
    result = await resp.json()
    assert result == {"result": "ok"}

    # Verify ID added to orig_data
    assert "id" in orig_data[0]

    assert orig_data[1] == {"id": "moon", "trigger": [], "condition": [], "action": []}


async def test_delete_automation(opp, opp_client):
    """Test deleting an automation."""
    ent_reg = await opp.helpers.entity_registry.async_get_registry()

    assert await async_setup_component(
        opp,
        "automation",
        {
            "automation": [
                {
                    "id": "sun",
                    "trigger": {"platform": "event", "event_type": "test_event"},
                    "action": {"service": "test.automation"},
                },
                {
                    "id": "moon",
                    "trigger": {"platform": "event", "event_type": "test_event"},
                    "action": {"service": "test.automation"},
                },
            ]
        },
    )

    assert len(ent_reg.entities) == 2

    with patch.object(config, "SECTIONS", ["automation"]):
        assert await async_setup_component(opp, "config", {})

    client = await opp_client()

    orig_data = [{"id": "sun"}, {"id": "moon"}]

    def mock_read(path):
        """Mock reading data."""
        return orig_data

    written = []

    def mock_write(path, data):
        """Mock writing data."""
        written.append(data)

    with patch("openpeerpower.components.config._read", mock_read), patch(
        "openpeerpower.components.config._write", mock_write
    ), patch("openpeerpower.config.async_opp_config_yaml", return_value={}):
        resp = await client.delete("/api/config/automation/config/sun")
        await opp.async_block_till_done()

    assert resp.status == 200
    result = await resp.json()
    assert result == {"result": "ok"}

    assert len(written) == 1
    assert written[0][0]["id"] == "moon"

    assert len(ent_reg.entities) == 1
