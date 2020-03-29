"""Test add-on panel."""
from unittest.mock import Mock, patch

import pytest

from openpeerpower.setup import async_setup_component

from tests.common import mock_coro


@pytest.fixture(autouse=True)
def mock_all(aioclient_mock):
    """Mock all setup requests."""
    aioclient_mock.post("http://127.0.0.1/openpeerpower/options", json={"result": "ok"})
    aioclient_mock.get("http://127.0.0.1/supervisor/ping", json={"result": "ok"})
    aioclient_mock.post("http://127.0.0.1/supervisor/options", json={"result": "ok"})
    aioclient_mock.get(
        "http://127.0.0.1/openpeerpower/info",
        json={"result": "ok", "data": {"last_version": "10.0"}},
    )


async def test_oppio_addon_panel_startup(opp, aioclient_mock, oppio_env):
    """Test startup and panel setup after event."""
    aioclient_mock.get(
        "http://127.0.0.1/ingress/panels",
        json={
            "result": "ok",
            "data": {
                "panels": {
                    "test1": {
                        "enable": True,
                        "title": "Test",
                        "icon": "mdi:test",
                        "admin": False,
                    },
                    "test2": {
                        "enable": False,
                        "title": "Test 2",
                        "icon": "mdi:test2",
                        "admin": True,
                    },
                }
            },
        },
    )

    assert aioclient_mock.call_count == 0

    with patch(
        "openpeerpower.components.oppio.addon_panel._register_panel",
        Mock(return_value=mock_coro()),
    ) as mock_panel:
        await async_setup_component(opp, "oppio", {})
        await opp.async_block_till_done()

        assert aioclient_mock.call_count == 3
        assert mock_panel.called
        mock_panel.assert_called_with(
            opp,
            "test1",
            {"enable": True, "title": "Test", "icon": "mdi:test", "admin": False},
        )


async def test_oppio_addon_panel_api(opp, aioclient_mock, oppio_env, opp_client):
    """Test panel api after event."""
    aioclient_mock.get(
        "http://127.0.0.1/ingress/panels",
        json={
            "result": "ok",
            "data": {
                "panels": {
                    "test1": {
                        "enable": True,
                        "title": "Test",
                        "icon": "mdi:test",
                        "admin": False,
                    },
                    "test2": {
                        "enable": False,
                        "title": "Test 2",
                        "icon": "mdi:test2",
                        "admin": True,
                    },
                }
            },
        },
    )

    assert aioclient_mock.call_count == 0

    with patch(
        "openpeerpower.components.oppio.addon_panel._register_panel",
        Mock(return_value=mock_coro()),
    ) as mock_panel:
        await async_setup_component(opp, "oppio", {})
        await opp.async_block_till_done()

        assert aioclient_mock.call_count == 3
        assert mock_panel.called
        mock_panel.assert_called_with(
            opp,
            "test1",
            {"enable": True, "title": "Test", "icon": "mdi:test", "admin": False},
        )

        opp_client = await opp_client()

        resp = await opp_client.post("/api/oppio_push/panel/test2")
        assert resp.status == 400

        resp = await opp_client.post("/api/oppio_push/panel/test1")
        assert resp.status == 200
        assert mock_panel.call_count == 2

        mock_panel.assert_called_with(
            opp,
            "test1",
            {"enable": True, "title": "Test", "icon": "mdi:test", "admin": False},
        )
