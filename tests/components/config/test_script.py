"""Tests for config/script."""
from unittest.mock import patch

from openpeerpower.bootstrap import async_setup_component
from openpeerpower.components import config


async def test_delete_script(opp, opp_client):
    """Test deleting a script."""
    with patch.object(config, "SECTIONS", ["script"]):
        await async_setup_component(opp, "config", {})

    client = await opp_client()

    orig_data = {"one": {}, "two": {}}

    def mock_read(path):
        """Mock reading data."""
        return orig_data

    written = []

    def mock_write(path, data):
        """Mock writing data."""
        written.append(data)

    with patch("openpeerpower.components.config._read", mock_read), patch(
        "openpeerpower.components.config._write", mock_write
    ):
        resp = await client.delete("/api/config/script/config/two")

    assert resp.status == 200
    result = await resp.json()
    assert result == {"result": "ok"}

    assert len(written) == 1
    assert written[0] == {"one": {}}
