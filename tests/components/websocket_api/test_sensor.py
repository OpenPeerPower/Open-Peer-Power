"""Test cases for the API stream sensor."""

from openpeerpower.bootstrap import async_setup_component

from .test_auth import test_auth_active_with_token

from tests.common import assert_setup_component


async def test_websocket_api(
    opp, no_auth_websocket_client, opp_access_token, legacy_auth
):
    """Test API streams."""
    with assert_setup_component(1):
        await async_setup_component(
            opp, "sensor", {"sensor": {"platform": "websocket_api"}}
        )

    state = opp.states.get("sensor.connected_clients")
    assert state.state == "0"

    await test_auth_active_with_token(opp, no_auth_websocket_client, opp_access_token)

    state = opp.states.get("sensor.connected_clients")
    assert state.state == "1"

    await no_auth_websocket_client.close()
    await opp.async_block_till_done()

    state = opp.states.get("sensor.connected_clients")
    assert state.state == "0"
