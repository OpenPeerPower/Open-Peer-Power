"""Tests for the Open Peer Power Websocket API."""
from unittest.mock import Mock, patch

from aiohttp import WSMsgType
import pytest
import voluptuous as vol

from openpeerpower.components.websocket_api import const, messages


@pytest.fixture
def mock_low_queue():
    """Mock a low queue."""
    with patch("openpeerpower.components.websocket_api.http.MAX_PENDING_MSG", 5):
        yield


async def test_invalid_message_format(websocket_client):
    """Test sending invalid JSON."""
    await websocket_client.send_json({"type": 5})

    msg = await websocket_client.receive_json()

    assert msg["type"] == const.TYPE_RESULT
    error = msg["error"]
    assert error["code"] == const.ERR_INVALID_FORMAT
    assert error["message"].startswith("Message incorrectly formatted")


async def test_invalid_json(websocket_client):
    """Test sending invalid JSON."""
    await websocket_client.send_str("this is not JSON")

    msg = await websocket_client.receive()

    assert msg.type == WSMsgType.close


async def test_quiting_opp(opp, websocket_client):
    """Test sending invalid JSON."""
    with patch.object(opp.loop, "stop"):
        await opp.async_stop()

    msg = await websocket_client.receive()

    assert msg.type == WSMsgType.CLOSE


async def test_pending_msg_overflow(opp, mock_low_queue, websocket_client):
    """Test get_panels command."""
    for idx in range(10):
        await websocket_client.send_json({"id": idx + 1, "type": "ping"})
    msg = await websocket_client.receive()
    assert msg.type == WSMsgType.close


async def test_unknown_command(websocket_client):
    """Test get_panels command."""
    await websocket_client.send_json({"id": 5, "type": "unknown_command"})

    msg = await websocket_client.receive_json()
    assert not msg["success"]
    assert msg["error"]["code"] == const.ERR_UNKNOWN_COMMAND


async def test_handler_failing(opp, websocket_client):
    """Test a command that raises."""
    opp.components.websocket_api.async_register_command(
        "bla",
        Mock(side_effect=TypeError),
        messages.BASE_COMMAND_MESSAGE_SCHEMA.extend({"type": "bla"}),
    )
    await websocket_client.send_json({"id": 5, "type": "bla"})

    msg = await websocket_client.receive_json()
    assert msg["id"] == 5
    assert msg["type"] == const.TYPE_RESULT
    assert not msg["success"]
    assert msg["error"]["code"] == const.ERR_UNKNOWN_ERROR


async def test_invalid_vol(opp, websocket_client):
    """Test a command that raises invalid vol error."""
    opp.components.websocket_api.async_register_command(
        "bla",
        Mock(side_effect=TypeError),
        messages.BASE_COMMAND_MESSAGE_SCHEMA.extend(
            {"type": "bla", vol.Required("test_config"): str}
        ),
    )

    await websocket_client.send_json({"id": 5, "type": "bla", "test_config": 5})

    msg = await websocket_client.receive_json()
    assert msg["id"] == 5
    assert msg["type"] == const.TYPE_RESULT
    assert not msg["success"]
    assert msg["error"]["code"] == const.ERR_INVALID_FORMAT
    assert "expected str for dictionary value" in msg["error"]["message"]
