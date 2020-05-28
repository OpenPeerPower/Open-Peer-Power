"""Tests for the cloud component."""
from unittest.mock import patch

from openpeerpower.components import cloud
from openpeerpower.components.cloud import const
from openpeerpower.setup import async_setup_component

from tests.common import mock_coro


async def mock_cloud(opp, config=None):
    """Mock cloud."""
    assert await async_setup_component(opp, cloud.DOMAIN, {"cloud": config or {}})
    cloud_inst = opp.data["cloud"]
    with patch("opp_nabucasa.Cloud.run_executor", return_value=mock_coro()):
        await cloud_inst.start()


def mock_cloud_prefs(opp, prefs={}):
    """Fixture for cloud component."""
    prefs_to_set = {
        const.PREF_ENABLE_ALEXA: True,
        const.PREF_ENABLE_GOOGLE: True,
        const.PREF_GOOGLE_SECURE_DEVICES_PIN: None,
    }
    prefs_to_set.update(prefs)
    opp.data[cloud.DOMAIN].client._prefs._prefs = prefs_to_set
    return opp.data[cloud.DOMAIN].client._prefs
