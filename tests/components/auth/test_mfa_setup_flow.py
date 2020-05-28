"""Tests for the mfa setup flow."""
from openpeerpower import data_entry_flow
from openpeerpower.auth import auth_manager_from_config
from openpeerpower.components.auth import mfa_setup_flow
from openpeerpower.setup import async_setup_component

from tests.common import CLIENT_ID, MockUser, ensure_auth_manager_loaded


async def test_ws_setup_depose_mfa(opp, opp_ws_client):
    """Test set up mfa module for current user."""
    opp.auth = await auth_manager_from_config(
        opp,
        provider_configs=[
            {
                "type": "insecure_example",
                "users": [
                    {
                        "username": "test-user",
                        "password": "test-pass",
                        "name": "Test Name",
                    }
                ],
            }
        ],
        module_configs=[
            {
                "type": "insecure_example",
                "id": "example_module",
                "data": [{"user_id": "mock-user", "pin": "123456"}],
            }
        ],
    )
    ensure_auth_manager_loaded(opp.auth)
    await async_setup_component(opp, "auth", {"http": {}})

    user = MockUser(id="mock-user").add_to_opp(opp)
    cred = await opp.auth.auth_providers[0].async_get_or_create_credentials(
        {"username": "test-user"}
    )
    await opp.auth.async_link_user(user, cred)
    refresh_token = await opp.auth.async_create_refresh_token(user, CLIENT_ID)
    access_token = opp.auth.async_create_access_token(refresh_token)

    client = await opp_ws_client(opp, access_token)

    await client.send_json({"id": 10, "type": mfa_setup_flow.WS_TYPE_SETUP_MFA})

    result = await client.receive_json()
    assert result["id"] == 10
    assert result["success"] is False
    assert result["error"]["code"] == "no_module"

    await client.send_json(
        {
            "id": 11,
            "type": mfa_setup_flow.WS_TYPE_SETUP_MFA,
            "mfa_module_id": "example_module",
        }
    )

    result = await client.receive_json()
    assert result["id"] == 11
    assert result["success"]

    flow = result["result"]
    assert flow["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert flow["handler"] == "example_module"
    assert flow["step_id"] == "init"
    assert flow["data_schema"][0] == {"type": "string", "name": "pin"}

    await client.send_json(
        {
            "id": 12,
            "type": mfa_setup_flow.WS_TYPE_SETUP_MFA,
            "flow_id": flow["flow_id"],
            "user_input": {"pin": "654321"},
        }
    )

    result = await client.receive_json()
    assert result["id"] == 12
    assert result["success"]

    flow = result["result"]
    assert flow["type"] == data_entry_flow.RESULT_TYPE_CREATE_ENTRY
    assert flow["handler"] == "example_module"
    assert flow["data"]["result"] is None

    await client.send_json(
        {
            "id": 13,
            "type": mfa_setup_flow.WS_TYPE_DEPOSE_MFA,
            "mfa_module_id": "invalid_id",
        }
    )

    result = await client.receive_json()
    assert result["id"] == 13
    assert result["success"] is False
    assert result["error"]["code"] == "disable_failed"

    await client.send_json(
        {
            "id": 14,
            "type": mfa_setup_flow.WS_TYPE_DEPOSE_MFA,
            "mfa_module_id": "example_module",
        }
    )

    result = await client.receive_json()
    assert result["id"] == 14
    assert result["success"]
    assert result["result"] == "done"
