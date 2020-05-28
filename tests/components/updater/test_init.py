"""The tests for the Updater component."""
import asyncio
from unittest.mock import Mock

from asynctest import patch
import pytest

from openpeerpower.components import updater
from openpeerpower.helpers.update_coordinator import UpdateFailed
from openpeerpower.setup import async_setup_component

from tests.common import MockDependency, mock_component, mock_coro

NEW_VERSION = "10000.0"
MOCK_VERSION = "10.0"
MOCK_DEV_VERSION = "10.0.dev0"
MOCK_HUUID = "abcdefg"
MOCK_RESPONSE = {"version": "0.15", "release-notes": "https://open-peer-power.io"}
MOCK_CONFIG = {updater.DOMAIN: {"reporting": True}}
RELEASE_NOTES = "test release notes"


@pytest.fixture(autouse=True)
def mock_distro():
    """Mock distro dep."""
    with MockDependency("distro"):
        yield


@pytest.fixture(autouse=True)
def mock_version():
    """Mock current version."""
    with patch("openpeerpower.components.updater.current_version", MOCK_VERSION):
        yield


@pytest.fixture(name="mock_get_newest_version")
def mock_get_newest_version_fixture():
    """Fixture to mock get_newest_version."""
    with patch(
        "openpeerpower.components.updater.get_newest_version",
        return_value=(NEW_VERSION, RELEASE_NOTES),
    ) as mock:
        yield mock


@pytest.fixture(name="mock_get_uuid", autouse=True)
def mock_get_uuid_fixture():
    """Fixture to mock get_uuid."""
    with patch("openpeerpower.components.updater._load_uuid") as mock:
        yield mock


async def test_new_version_shows_entity_true(
    opp, mock_get_uuid, mock_get_newest_version
):
    """Test if sensor is true if new version is available."""
    mock_get_uuid.return_value = MOCK_HUUID

    assert await async_setup_component(opp, updater.DOMAIN, {updater.DOMAIN: {}})

    await opp.async_block_till_done()
    assert opp.states.is_state("binary_sensor.updater", "on")
    assert (
        opp.states.get("binary_sensor.updater").attributes["newest_version"]
        == NEW_VERSION
    )
    assert (
        opp.states.get("binary_sensor.updater").attributes["release_notes"]
        == RELEASE_NOTES
    )


async def test_same_version_shows_entity_false(
    opp, mock_get_uuid, mock_get_newest_version
):
    """Test if sensor is false if no new version is available."""
    mock_get_uuid.return_value = MOCK_HUUID
    mock_get_newest_version.return_value = mock_coro((MOCK_VERSION, ""))

    assert await async_setup_component(opp, updater.DOMAIN, {updater.DOMAIN: {}})

    await opp.async_block_till_done()

    assert opp.states.is_state("binary_sensor.updater", "off")
    assert (
        opp.states.get("binary_sensor.updater").attributes["newest_version"]
        == MOCK_VERSION
    )
    assert "release_notes" not in opp.states.get("binary_sensor.updater").attributes


async def test_disable_reporting(opp, mock_get_uuid, mock_get_newest_version):
    """Test we do not gather analytics when disable reporting is active."""
    mock_get_uuid.return_value = MOCK_HUUID
    mock_get_newest_version.return_value = mock_coro((MOCK_VERSION, ""))

    assert await async_setup_component(
        opp, updater.DOMAIN, {updater.DOMAIN: {"reporting": False}}
    )
    await opp.async_block_till_done()

    assert opp.states.is_state("binary_sensor.updater", "off")
    await updater.get_newest_version(opp, MOCK_HUUID, MOCK_CONFIG)
    call = mock_get_newest_version.mock_calls[0][1]
    assert call[0] is opp
    assert call[1] is None


async def test_get_newest_version_no_analytics_when_no_huuid(opp, aioclient_mock):
    """Test we do not gather analytics when no huuid is passed in."""
    aioclient_mock.post(updater.UPDATER_URL, json=MOCK_RESPONSE)

    with patch(
        "openpeerpower.helpers.system_info.async_get_system_info", side_effect=Exception
    ):
        res = await updater.get_newest_version(opp, None, False)
        assert res == (MOCK_RESPONSE["version"], MOCK_RESPONSE["release-notes"])


async def test_get_newest_version_analytics_when_huuid(opp, aioclient_mock):
    """Test we gather analytics when huuid is passed in."""
    aioclient_mock.post(updater.UPDATER_URL, json=MOCK_RESPONSE)

    with patch(
        "openpeerpower.helpers.system_info.async_get_system_info",
        Mock(return_value=mock_coro({"fake": "bla"})),
    ):
        res = await updater.get_newest_version(opp, MOCK_HUUID, False)
        assert res == (MOCK_RESPONSE["version"], MOCK_RESPONSE["release-notes"])


async def test_error_fetching_new_version_timeout(opp):
    """Test we handle timeout error while fetching new version."""
    with patch(
        "openpeerpower.helpers.system_info.async_get_system_info",
        Mock(return_value=mock_coro({"fake": "bla"})),
    ), patch("async_timeout.timeout", side_effect=asyncio.TimeoutError), pytest.raises(
        UpdateFailed
    ):
        await updater.get_newest_version(opp, MOCK_HUUID, False)


async def test_error_fetching_new_version_bad_json(opp, aioclient_mock):
    """Test we handle json error while fetching new version."""
    aioclient_mock.post(updater.UPDATER_URL, text="not json")

    with patch(
        "openpeerpower.helpers.system_info.async_get_system_info",
        Mock(return_value=mock_coro({"fake": "bla"})),
    ), pytest.raises(UpdateFailed):
        await updater.get_newest_version(opp, MOCK_HUUID, False)


async def test_error_fetching_new_version_invalid_response(opp, aioclient_mock):
    """Test we handle response error while fetching new version."""
    aioclient_mock.post(
        updater.UPDATER_URL,
        json={
            "version": "0.15"
            # 'release-notes' is missing
        },
    )

    with patch(
        "openpeerpower.helpers.system_info.async_get_system_info",
        Mock(return_value=mock_coro({"fake": "bla"})),
    ), pytest.raises(UpdateFailed):
        await updater.get_newest_version(opp, MOCK_HUUID, False)


async def test_new_version_shows_entity_after_hour_oppio(
    opp, mock_get_uuid, mock_get_newest_version
):
    """Test if binary sensor gets updated if new version is available / Opp.io."""
    mock_get_uuid.return_value = MOCK_HUUID
    mock_component(opp, "oppio")
    opp.data["oppio_opp_version"] = "999.0"

    assert await async_setup_component(opp, updater.DOMAIN, {updater.DOMAIN: {}})

    await opp.async_block_till_done()

    assert opp.states.is_state("binary_sensor.updater", "on")
    assert (
        opp.states.get("binary_sensor.updater").attributes["newest_version"] == "999.0"
    )
    assert (
        opp.states.get("binary_sensor.updater").attributes["release_notes"]
        == RELEASE_NOTES
    )
