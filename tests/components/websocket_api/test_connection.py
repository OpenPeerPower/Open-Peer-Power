"""Test WebSocket Connection class."""
from openpeerpower.components import websocket_api
from openpeerpower.components.websocket_api import const


async def test_send_big_result(opp, websocket_client):
    """Test sending big results over the WS."""

    @websocket_api.websocket_command({"type": "big_result"})
    @websocket_api.async_response
    async def send_big_result(opp, connection, msg):
        await connection.send_big_result(msg["id"], {"big": "result"})

    opp.components.websocket_api.async_register_command(send_big_result)

    await websocket_client.send_json({"id": 5, "type": "big_result"})

    msg = await websocket_client.receive_json()
    assert msg["id"] == 5
    assert msg["type"] == const.TYPE_RESULT
    assert msg["success"]
    assert msg["result"] == {"big": "result"}
