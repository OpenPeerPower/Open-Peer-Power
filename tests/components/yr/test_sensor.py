"""The tests for the Yr sensor platform."""
from datetime import datetime
from unittest.mock import patch

from openpeerpower.bootstrap import async_setup_component
import openpeerpower.util.dt as dt_util

from tests.common import assert_setup_component, load_fixture

NOW = datetime(2016, 6, 9, 1, tzinfo=dt_util.UTC)


async def test_default_setup(opp, aioclient_mock):
    """Test the default setup."""
    aioclient_mock.get(
        "https://aa015h6buqvih86i1.api.met.no/weatherapi/locationforecast/1.9/",
        text=load_fixture("yr.no.xml"),
    )
    config = {"platform": "yr", "elevation": 0}
    opp.allow_pool = True
    with patch(
        "openpeerpower.components.yr.sensor.dt_util.utcnow", return_value=NOW
    ), assert_setup_component(1):
        await async_setup_component(opp, "sensor", {"sensor": config})

    state = opp.states.get("sensor.yr_symbol")

    assert state.state == "3"
    assert state.attributes.get("unit_of_measurement") is None


async def test_custom_setup(opp, aioclient_mock):
    """Test a custom setup."""
    aioclient_mock.get(
        "https://aa015h6buqvih86i1.api.met.no/weatherapi/locationforecast/1.9/",
        text=load_fixture("yr.no.xml"),
    )

    config = {
        "platform": "yr",
        "elevation": 0,
        "monitored_conditions": [
            "pressure",
            "windDirection",
            "humidity",
            "fog",
            "windSpeed",
        ],
    }
    opp.allow_pool = True
    with patch(
        "openpeerpower.components.yr.sensor.dt_util.utcnow", return_value=NOW
    ), assert_setup_component(1):
        await async_setup_component(opp, "sensor", {"sensor": config})

    state = opp.states.get("sensor.yr_pressure")
    assert state.attributes.get("unit_of_measurement") == "hPa"
    assert state.state == "1009.3"

    state = opp.states.get("sensor.yr_wind_direction")
    assert state.attributes.get("unit_of_measurement") == "°"
    assert state.state == "103.6"

    state = opp.states.get("sensor.yr_humidity")
    assert state.attributes.get("unit_of_measurement") == "%"
    assert state.state == "55.5"

    state = opp.states.get("sensor.yr_fog")
    assert state.attributes.get("unit_of_measurement") == "%"
    assert state.state == "0.0"

    state = opp.states.get("sensor.yr_wind_speed")
    assert state.attributes.get("unit_of_measurement") == "m/s"
    assert state.state == "3.5"


async def test_forecast_setup(opp, aioclient_mock):
    """Test a custom setup with 24h forecast."""
    aioclient_mock.get(
        "https://aa015h6buqvih86i1.api.met.no/weatherapi/locationforecast/1.9/",
        text=load_fixture("yr.no.xml"),
    )

    config = {
        "platform": "yr",
        "elevation": 0,
        "forecast": 24,
        "monitored_conditions": [
            "pressure",
            "windDirection",
            "humidity",
            "fog",
            "windSpeed",
        ],
    }
    opp.allow_pool = True
    with patch(
        "openpeerpower.components.yr.sensor.dt_util.utcnow", return_value=NOW
    ), assert_setup_component(1):
        await async_setup_component(opp, "sensor", {"sensor": config})

    state = opp.states.get("sensor.yr_pressure")
    assert state.attributes.get("unit_of_measurement") == "hPa"
    assert state.state == "1008.3"

    state = opp.states.get("sensor.yr_wind_direction")
    assert state.attributes.get("unit_of_measurement") == "°"
    assert state.state == "148.9"

    state = opp.states.get("sensor.yr_humidity")
    assert state.attributes.get("unit_of_measurement") == "%"
    assert state.state == "77.4"

    state = opp.states.get("sensor.yr_fog")
    assert state.attributes.get("unit_of_measurement") == "%"
    assert state.state == "0.0"

    state = opp.states.get("sensor.yr_wind_speed")
    assert state.attributes.get("unit_of_measurement") == "m/s"
    assert state.state == "3.6"
