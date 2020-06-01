"""Fixtures for cloud tests."""
from unittest.mock import patch

import jwt
import pytest

from openpeerpower.components.cloud import const, prefs

from . import mock_cloud, mock_cloud_prefs


@pytest.fixture(autouse=True)
def mock_user_data():
    """Mock os module."""
    with patch("opp_cloud.Cloud.write_user_info") as writer:
        yield writer


@pytest.fixture
def mock_cloud_fixture(opp):
    """Fixture for cloud component."""
    opp.loop.run_until_complete(mock_cloud(opp))
    return mock_cloud_prefs(opp)


@pytest.fixture
async def cloud_prefs(opp):
    """Fixture for cloud preferences."""
    cloud_prefs = prefs.CloudPreferences(opp)
    await cloud_prefs.async_initialize()
    return cloud_prefs


@pytest.fixture
async def mock_cloud_setup(opp):
    """Set up the cloud."""
    await mock_cloud(opp)


@pytest.fixture
def mock_cloud_login(opp, mock_cloud_setup):
    """Mock cloud is logged in."""
    opp.data[const.DOMAIN].id_token = jwt.encode(
        {
            "email": "hello@open-peer-power.io",
            "custom:sub-exp": "2018-01-03",
            "cognito:username": "abcdefghjkl",
        },
        "test",
    )
