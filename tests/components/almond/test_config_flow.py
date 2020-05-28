"""Test the Almond config flow."""
import asyncio
from unittest.mock import patch

from openpeerpower import config_entries, data_entry_flow, setup
from openpeerpower.components.almond import config_flow
from openpeerpower.components.almond.const import DOMAIN
from openpeerpower.helpers import config_entry_oauth2_flow

from tests.common import MockConfigEntry, mock_coro

CLIENT_ID_VALUE = "1234"
CLIENT_SECRET_VALUE = "5678"


async def test_import(opp):
    """Test that we can import a config entry."""
    with patch("pyalmond.WebAlmondAPI.async_list_apps", side_effect=mock_coro):
        assert await setup.async_setup_component(
            opp,
            "almond",
            {"almond": {"type": "local", "host": "http://localhost:3000"}},
        )
        await opp.async_block_till_done()

    assert len(opp.config_entries.async_entries(DOMAIN)) == 1
    entry = opp.config_entries.async_entries(DOMAIN)[0]
    assert entry.data["type"] == "local"
    assert entry.data["host"] == "http://localhost:3000"


async def test_import_cannot_connect(opp):
    """Test that we won't import a config entry if we cannot connect."""
    with patch(
        "pyalmond.WebAlmondAPI.async_list_apps", side_effect=asyncio.TimeoutError
    ):
        assert await setup.async_setup_component(
            opp,
            "almond",
            {"almond": {"type": "local", "host": "http://localhost:3000"}},
        )
        await opp.async_block_till_done()

    assert len(opp.config_entries.async_entries(DOMAIN)) == 0


async def test_oppio(opp):
    """Test that Opp.io can discover this integration."""
    result = await opp.config_entries.flow.async_init(
        DOMAIN,
        context={"source": "oppio"},
        data={"addon": "Almond add-on", "host": "almond-addon", "port": "1234"},
    )

    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result["step_id"] == "oppio_confirm"

    result2 = await opp.config_entries.flow.async_configure(result["flow_id"], {})

    assert result2["type"] == data_entry_flow.RESULT_TYPE_CREATE_ENTRY

    assert len(opp.config_entries.async_entries(DOMAIN)) == 1
    entry = opp.config_entries.async_entries(DOMAIN)[0]
    assert entry.data["type"] == "local"
    assert entry.data["host"] == "http://almond-addon:1234"


async def test_abort_if_existing_entry(opp):
    """Check flow abort when an entry already exist."""
    MockConfigEntry(domain=DOMAIN).add_to_opp(opp)

    flow = config_flow.AlmondFlowHandler()
    flow.opp = opp

    result = await flow.async_step_user()
    assert result["type"] == data_entry_flow.RESULT_TYPE_ABORT
    assert result["reason"] == "already_setup"

    result = await flow.async_step_import()
    assert result["type"] == data_entry_flow.RESULT_TYPE_ABORT
    assert result["reason"] == "already_setup"

    result = await flow.async_step_oppio()
    assert result["type"] == data_entry_flow.RESULT_TYPE_ABORT
    assert result["reason"] == "already_setup"


async def test_full_flow(opp, aiohttp_client, aioclient_mock):
    """Check full flow."""
    assert await setup.async_setup_component(
        opp,
        "almond",
        {
            "almond": {
                "type": "oauth2",
                "client_id": CLIENT_ID_VALUE,
                "client_secret": CLIENT_SECRET_VALUE,
            },
            "http": {"base_url": "https://example.com"},
        },
    )

    result = await opp.config_entries.flow.async_init(
        "almond", context={"source": config_entries.SOURCE_USER}
    )
    state = config_entry_oauth2_flow._encode_jwt(opp, {"flow_id": result["flow_id"]})

    assert result["type"] == data_entry_flow.RESULT_TYPE_EXTERNAL_STEP
    assert result["url"] == (
        "https://almond.stanford.edu/me/api/oauth2/authorize"
        f"?response_type=code&client_id={CLIENT_ID_VALUE}"
        "&redirect_uri=https://example.com/auth/external/callback"
        f"&state={state}&scope=profile+user-read+user-read-results+user-exec-command"
    )

    client = await aiohttp_client(opp.http.app)
    resp = await client.get(f"/auth/external/callback?code=abcd&state={state}")
    assert resp.status == 200
    assert resp.headers["content-type"] == "text/html; charset=utf-8"

    aioclient_mock.post(
        "https://almond.stanford.edu/me/api/oauth2/token",
        json={
            "refresh_token": "mock-refresh-token",
            "access_token": "mock-access-token",
            "type": "Bearer",
            "expires_in": 60,
        },
    )

    result = await opp.config_entries.flow.async_configure(result["flow_id"])

    assert len(opp.config_entries.async_entries(DOMAIN)) == 1
    entry = opp.config_entries.async_entries(DOMAIN)[0]
    assert entry.data["type"] == "oauth2"
    assert entry.data["host"] == "https://almond.stanford.edu/me"
