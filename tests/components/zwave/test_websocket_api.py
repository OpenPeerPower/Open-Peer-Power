"""Test Z-Wave Websocket API."""
from openpeerpower.bootstrap import async_setup_component
from openpeerpower.components.zwave.const import (
    CONF_AUTOHEAL,
    CONF_POLLING_INTERVAL,
    CONF_USB_STICK_PATH,
)
from openpeerpower.components.zwave.websocket_api import ID, TYPE


async def test_zwave_ws_api(opp, mock_openzwave, opp_ws_client):
    """Test Z-Wave websocket API."""

    await async_setup_component(
        opp,
        "zwave",
        {
            "zwave": {
                CONF_AUTOHEAL: False,
                CONF_USB_STICK_PATH: "/dev/zwave",
                CONF_POLLING_INTERVAL: 6000,
            }
        },
    )

    await opp.async_block_till_done()

    client = await opp_ws_client(opp)

    await client.send_json({ID: 5, TYPE: "zwave/get_config"})

    msg = await client.receive_json()
    result = msg["result"]

    assert result[CONF_USB_STICK_PATH] == "/dev/zwave"
    assert not result[CONF_AUTOHEAL]
    assert result[CONF_POLLING_INTERVAL] == 6000
