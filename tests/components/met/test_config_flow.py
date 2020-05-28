"""Tests for Met.no config flow."""
from asynctest import patch
import pytest

from openpeerpower.components.met.const import DOMAIN, HOME_LOCATION_NAME
from openpeerpower.const import CONF_ELEVATION, CONF_LATITUDE, CONF_LONGITUDE

from tests.common import MockConfigEntry


@pytest.fixture(name="met_setup", autouse=True)
def met_setup_fixture():
    """Patch met setup entry."""
    with patch("openpeerpower.components.met.async_setup_entry", return_value=True):
        yield


async def test_show_config_form(opp):
    """Test show configuration form."""
    result = await opp.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )

    assert result["type"] == "form"
    assert result["step_id"] == "user"


async def test_flow_with_home_location(opp):
    """Test config flow.

    Test the flow when a default location is configured.
    Then it should return a form with default values.
    """
    opp.config.latitude = 1
    opp.config.longitude = 2
    opp.config.elevation = 3

    result = await opp.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )

    assert result["type"] == "form"
    assert result["step_id"] == "user"

    default_data = result["data_schema"]({})
    assert default_data["name"] == HOME_LOCATION_NAME
    assert default_data["latitude"] == 1
    assert default_data["longitude"] == 2
    assert default_data["elevation"] == 3


async def test_create_entry(opp):
    """Test create entry from user input."""
    test_data = {
        "name": "home",
        CONF_LONGITUDE: 0,
        CONF_LATITUDE: 0,
        CONF_ELEVATION: 0,
    }

    result = await opp.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}, data=test_data
    )

    assert result["type"] == "create_entry"
    assert result["title"] == "home"
    assert result["data"] == test_data


async def test_flow_entry_already_exists(opp):
    """Test user input for config_entry that already exists.

    Test when the form should show when user puts existing location
    in the config gui. Then the form should show with error.
    """
    first_entry = MockConfigEntry(domain="met")
    first_entry.data["name"] = "home"
    first_entry.data[CONF_LONGITUDE] = 0
    first_entry.data[CONF_LATITUDE] = 0
    first_entry.data[CONF_ELEVATION] = 0
    first_entry.add_to_opp(opp)

    test_data = {
        "name": "home",
        CONF_LONGITUDE: 0,
        CONF_LATITUDE: 0,
        CONF_ELEVATION: 0,
    }

    result = await opp.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}, data=test_data
    )

    assert result["type"] == "form"
    assert result["errors"]["name"] == "name_exists"


async def test_onboarding_step(opp):
    """Test initializing via onboarding step."""
    result = await opp.config_entries.flow.async_init(
        DOMAIN, context={"source": "onboarding"}, data={}
    )

    assert result["type"] == "create_entry"
    assert result["title"] == HOME_LOCATION_NAME
    assert result["data"] == {"track_home": True}
