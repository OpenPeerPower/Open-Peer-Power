"""The tests for the utility_meter sensor platform."""
from contextlib import contextmanager
from datetime import timedelta
import logging
from unittest.mock import patch

from openpeerpower.components.sensor import DOMAIN as SENSOR_DOMAIN
from openpeerpower.components.utility_meter.const import (
    ATTR_TARIFF,
    DOMAIN,
    SERVICE_SELECT_TARIFF,
)
from openpeerpower.const import ATTR_ENTITY_ID, EVENT_OPENPEERPOWER_START
from openpeerpower.setup import async_setup_component
import openpeerpower.util.dt as dt_util

from tests.common import async_fire_time_changed

_LOGGER = logging.getLogger(__name__)


@contextmanager
def alter_time(retval):
    """Manage multiple time mocks."""
    patch1 = patch("openpeerpower.util.dt.utcnow", return_value=retval)
    patch2 = patch("openpeerpower.util.dt.now", return_value=retval)

    with patch1, patch2:
        yield


async def test_state(opp):
    """Test utility sensor state."""
    config = {
        "utility_meter": {
            "energy_bill": {
                "source": "sensor.energy",
                "tariffs": ["onpeak", "midpeak", "offpeak"],
            }
        }
    }

    assert await async_setup_component(opp, DOMAIN, config)
    assert await async_setup_component(opp, SENSOR_DOMAIN, config)
    await opp.async_block_till_done()

    opp.bus.async_fire(EVENT_OPENPEERPOWER_START)
    entity_id = config[DOMAIN]["energy_bill"]["source"]
    opp.states.async_set(entity_id, 2, {"unit_of_measurement": "kWh"})
    await opp.async_block_till_done()

    now = dt_util.utcnow() + timedelta(seconds=10)
    with patch("openpeerpower.util.dt.utcnow", return_value=now):
        opp.states.async_set(
            entity_id, 3, {"unit_of_measurement": "kWh"}, force_update=True
        )
        await opp.async_block_till_done()

    state = opp.states.get("sensor.energy_bill_onpeak")
    assert state is not None
    assert state.state == "1"

    state = opp.states.get("sensor.energy_bill_midpeak")
    assert state is not None
    assert state.state == "0"

    state = opp.states.get("sensor.energy_bill_offpeak")
    assert state is not None
    assert state.state == "0"

    await opp.services.async_call(
        DOMAIN,
        SERVICE_SELECT_TARIFF,
        {ATTR_ENTITY_ID: "utility_meter.energy_bill", ATTR_TARIFF: "offpeak"},
        blocking=True,
    )

    await opp.async_block_till_done()

    now = dt_util.utcnow() + timedelta(seconds=20)
    with patch("openpeerpower.util.dt.utcnow", return_value=now):
        opp.states.async_set(
            entity_id, 6, {"unit_of_measurement": "kWh"}, force_update=True
        )
        await opp.async_block_till_done()

    state = opp.states.get("sensor.energy_bill_onpeak")
    assert state is not None
    assert state.state == "1"

    state = opp.states.get("sensor.energy_bill_midpeak")
    assert state is not None
    assert state.state == "0"

    state = opp.states.get("sensor.energy_bill_offpeak")
    assert state is not None
    assert state.state == "3"


async def test_net_consumption(opp):
    """Test utility sensor state."""
    config = {
        "utility_meter": {
            "energy_bill": {"source": "sensor.energy", "net_consumption": True}
        }
    }

    assert await async_setup_component(opp, DOMAIN, config)
    assert await async_setup_component(opp, SENSOR_DOMAIN, config)
    await opp.async_block_till_done()

    opp.bus.async_fire(EVENT_OPENPEERPOWER_START)
    entity_id = config[DOMAIN]["energy_bill"]["source"]
    opp.states.async_set(entity_id, 2, {"unit_of_measurement": "kWh"})
    await opp.async_block_till_done()

    now = dt_util.utcnow() + timedelta(seconds=10)
    with patch("openpeerpower.util.dt.utcnow", return_value=now):
        opp.states.async_set(
            entity_id, 1, {"unit_of_measurement": "kWh"}, force_update=True
        )
        await opp.async_block_till_done()

    state = opp.states.get("sensor.energy_bill")
    assert state is not None

    assert state.state == "-1"


async def test_non_net_consumption(opp):
    """Test utility sensor state."""
    config = {
        "utility_meter": {
            "energy_bill": {"source": "sensor.energy", "net_consumption": False}
        }
    }

    assert await async_setup_component(opp, DOMAIN, config)
    assert await async_setup_component(opp, SENSOR_DOMAIN, config)
    await opp.async_block_till_done()

    opp.bus.async_fire(EVENT_OPENPEERPOWER_START)
    entity_id = config[DOMAIN]["energy_bill"]["source"]
    opp.states.async_set(entity_id, 2, {"unit_of_measurement": "kWh"})
    await opp.async_block_till_done()

    now = dt_util.utcnow() + timedelta(seconds=10)
    with patch("openpeerpower.util.dt.utcnow", return_value=now):
        opp.states.async_set(
            entity_id, 1, {"unit_of_measurement": "kWh"}, force_update=True
        )
        await opp.async_block_till_done()

    state = opp.states.get("sensor.energy_bill")
    assert state is not None

    assert state.state == "0"


def gen_config(cycle, offset=None):
    """Generate configuration."""
    config = {
        "utility_meter": {"energy_bill": {"source": "sensor.energy", "cycle": cycle}}
    }

    if offset:
        config["utility_meter"]["energy_bill"]["offset"] = {
            "days": offset.days,
            "seconds": offset.seconds,
        }
    return config


async def _test_self_reset(opp, config, start_time, expect_reset=True):
    """Test energy sensor self reset."""
    assert await async_setup_component(opp, DOMAIN, config)
    assert await async_setup_component(opp, SENSOR_DOMAIN, config)
    await opp.async_block_till_done()

    opp.bus.async_fire(EVENT_OPENPEERPOWER_START)
    entity_id = config[DOMAIN]["energy_bill"]["source"]

    now = dt_util.parse_datetime(start_time)
    with alter_time(now):
        async_fire_time_changed(opp, now)
        opp.states.async_set(entity_id, 1, {"unit_of_measurement": "kWh"})
        await opp.async_block_till_done()

    now += timedelta(seconds=30)
    with alter_time(now):
        async_fire_time_changed(opp, now)
        opp.states.async_set(
            entity_id, 3, {"unit_of_measurement": "kWh"}, force_update=True
        )
        await opp.async_block_till_done()

    now += timedelta(seconds=30)
    with alter_time(now):
        async_fire_time_changed(opp, now)
        await opp.async_block_till_done()
        opp.states.async_set(
            entity_id, 6, {"unit_of_measurement": "kWh"}, force_update=True
        )
        await opp.async_block_till_done()

    state = opp.states.get("sensor.energy_bill")
    if expect_reset:
        assert state.attributes.get("last_period") == "2"
        assert state.state == "3"
    else:
        assert state.attributes.get("last_period") == 0
        assert state.state == "5"


async def test_self_reset_hourly(opp):
    """Test hourly reset of meter."""
    await _test_self_reset(
        opp, gen_config("hourly"), "2017-12-31T23:59:00.000000+00:00"
    )


async def test_self_reset_daily(opp):
    """Test daily reset of meter."""
    await _test_self_reset(
        opp, gen_config("daily"), "2017-12-31T23:59:00.000000+00:00"
    )


async def test_self_reset_weekly(opp):
    """Test weekly reset of meter."""
    await _test_self_reset(
        opp, gen_config("weekly"), "2017-12-31T23:59:00.000000+00:00"
    )


async def test_self_reset_monthly(opp):
    """Test monthly reset of meter."""
    await _test_self_reset(
        opp, gen_config("monthly"), "2017-12-31T23:59:00.000000+00:00"
    )


async def test_self_reset_quarterly(opp):
    """Test quarterly reset of meter."""
    await _test_self_reset(
        opp, gen_config("quarterly"), "2017-03-31T23:59:00.000000+00:00"
    )


async def test_self_reset_yearly(opp):
    """Test yearly reset of meter."""
    await _test_self_reset(
        opp, gen_config("yearly"), "2017-12-31T23:59:00.000000+00:00"
    )


async def test_self_no_reset_yearly(opp):
    """Test yearly reset of meter does not occur after 1st January."""
    await _test_self_reset(
        opp,
        gen_config("yearly"),
        "2018-01-01T23:59:00.000000+00:00",
        expect_reset=False,
    )


async def test_reset_yearly_offset(opp):
    """Test yearly reset of meter."""
    await _test_self_reset(
        opp,
        gen_config("yearly", timedelta(days=1, minutes=10)),
        "2018-01-02T00:09:00.000000+00:00",
    )


async def test_no_reset_yearly_offset(opp):
    """Test yearly reset of meter."""
    await _test_self_reset(
        opp,
        gen_config("yearly", timedelta(31)),
        "2018-01-30T23:59:00.000000+00:00",
        expect_reset=False,
    )
