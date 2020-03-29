"""The tests for the utility_meter component."""
from datetime import timedelta
import logging
from unittest.mock import patch

from openpeerpower.components.sensor import DOMAIN as SENSOR_DOMAIN
from openpeerpower.components.utility_meter.const import (
    ATTR_TARIFF,
    DOMAIN,
    SERVICE_RESET,
    SERVICE_SELECT_NEXT_TARIFF,
    SERVICE_SELECT_TARIFF,
)
from openpeerpower.const import ATTR_ENTITY_ID, EVENT_OPENPEERPOWER_START
from openpeerpower.setup import async_setup_component
import openpeerpower.util.dt as dt_util

_LOGGER = logging.getLogger(__name__)


async def test_services(opp):
    """Test energy sensor reset service."""
    config = {
        "utility_meter": {
            "energy_bill": {
                "source": "sensor.energy",
                "cycle": "hourly",
                "tariffs": ["peak", "offpeak"],
            }
        }
    }

    assert await async_setup_component(opp, DOMAIN, config)
    assert await async_setup_component(opp, SENSOR_DOMAIN, config)
    await opp.async_block_till_done()

    opp.bus.async_fire(EVENT_OPENPEERPOWER_START)
    entity_id = config[DOMAIN]["energy_bill"]["source"]
    opp.states.async_set(entity_id, 1, {"unit_of_measurement": "kWh"})
    await opp.async_block_till_done()

    now = dt_util.utcnow() + timedelta(seconds=10)
    with patch("openpeerpower.util.dt.utcnow", return_value=now):
        opp.states.async_set(
            entity_id, 3, {"unit_of_measurement": "kWh"}, force_update=True
        )
        await opp.async_block_till_done()

    state = opp.states.get("sensor.energy_bill_peak")
    assert state.state == "2"

    state = opp.states.get("sensor.energy_bill_offpeak")
    assert state.state == "0"

    # Next tariff
    data = {ATTR_ENTITY_ID: "utility_meter.energy_bill"}
    await opp.services.async_call(DOMAIN, SERVICE_SELECT_NEXT_TARIFF, data)
    await opp.async_block_till_done()

    now += timedelta(seconds=10)
    with patch("openpeerpower.util.dt.utcnow", return_value=now):
        opp.states.async_set(
            entity_id, 4, {"unit_of_measurement": "kWh"}, force_update=True
        )
        await opp.async_block_till_done()

    state = opp.states.get("sensor.energy_bill_peak")
    assert state.state == "2"

    state = opp.states.get("sensor.energy_bill_offpeak")
    assert state.state == "1"

    # Change tariff
    data = {ATTR_ENTITY_ID: "utility_meter.energy_bill", ATTR_TARIFF: "peak"}
    await opp.services.async_call(DOMAIN, SERVICE_SELECT_TARIFF, data)
    await opp.async_block_till_done()

    now += timedelta(seconds=10)
    with patch("openpeerpower.util.dt.utcnow", return_value=now):
        opp.states.async_set(
            entity_id, 5, {"unit_of_measurement": "kWh"}, force_update=True
        )
        await opp.async_block_till_done()

    state = opp.states.get("sensor.energy_bill_peak")
    assert state.state == "3"

    state = opp.states.get("sensor.energy_bill_offpeak")
    assert state.state == "1"

    # Reset meters
    data = {ATTR_ENTITY_ID: "utility_meter.energy_bill"}
    await opp.services.async_call(DOMAIN, SERVICE_RESET, data)
    await opp.async_block_till_done()

    state = opp.states.get("sensor.energy_bill_peak")
    assert state.state == "0"

    state = opp.states.get("sensor.energy_bill_offpeak")
    assert state.state == "0"
