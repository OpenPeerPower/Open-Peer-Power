"""The tests for the integration sensor platform."""
from datetime import timedelta
from unittest.mock import patch

from openpeerpower.setup import async_setup_component
import openpeerpower.util.dt as dt_util


async def test_state(opp):
    """Test integration sensor state."""
    config = {
        "sensor": {
            "platform": "integration",
            "name": "integration",
            "source": "sensor.power",
            "unit": "kWh",
            "round": 2,
        }
    }

    assert await async_setup_component(opp, "sensor", config)

    entity_id = config["sensor"]["source"]
    opp.states.async_set(entity_id, 1, {})
    await opp.async_block_till_done()

    now = dt_util.utcnow() + timedelta(seconds=3600)
    with patch("openpeerpower.util.dt.utcnow", return_value=now):
        opp.states.async_set(entity_id, 1, {}, force_update=True)
        await opp.async_block_till_done()

    state = opp.states.get("sensor.integration")
    assert state is not None

    # Testing a power sensor at 1 KiloWatts for 1hour = 1kWh
    assert round(float(state.state), config["sensor"]["round"]) == 1.0

    assert state.attributes.get("unit_of_measurement") == "kWh"


async def test_trapezoidal(opp):
    """Test integration sensor state."""
    config = {
        "sensor": {
            "platform": "integration",
            "name": "integration",
            "source": "sensor.power",
            "unit": "kWh",
            "round": 2,
        }
    }

    assert await async_setup_component(opp, "sensor", config)

    entity_id = config["sensor"]["source"]
    opp.states.async_set(entity_id, 0, {})
    await opp.async_block_till_done()

    # Testing a power sensor with non-monotonic intervals and values
    for time, value in [(20, 10), (30, 30), (40, 5), (50, 0)]:
        now = dt_util.utcnow() + timedelta(minutes=time)
        with patch("openpeerpower.util.dt.utcnow", return_value=now):
            opp.states.async_set(entity_id, value, {}, force_update=True)
            await opp.async_block_till_done()

    state = opp.states.get("sensor.integration")
    assert state is not None

    assert round(float(state.state), config["sensor"]["round"]) == 8.33

    assert state.attributes.get("unit_of_measurement") == "kWh"


async def test_left(opp):
    """Test integration sensor state with left reimann method."""
    config = {
        "sensor": {
            "platform": "integration",
            "name": "integration",
            "method": "left",
            "source": "sensor.power",
            "unit": "kWh",
            "round": 2,
        }
    }

    assert await async_setup_component(opp, "sensor", config)

    entity_id = config["sensor"]["source"]
    opp.states.async_set(entity_id, 0, {})
    await opp.async_block_till_done()

    # Testing a power sensor with non-monotonic intervals and values
    for time, value in [(20, 10), (30, 30), (40, 5), (50, 0)]:
        now = dt_util.utcnow() + timedelta(minutes=time)
        with patch("openpeerpower.util.dt.utcnow", return_value=now):
            opp.states.async_set(entity_id, value, {}, force_update=True)
            await opp.async_block_till_done()

    state = opp.states.get("sensor.integration")
    assert state is not None

    assert round(float(state.state), config["sensor"]["round"]) == 7.5

    assert state.attributes.get("unit_of_measurement") == "kWh"


async def test_right(opp):
    """Test integration sensor state with left reimann method."""
    config = {
        "sensor": {
            "platform": "integration",
            "name": "integration",
            "method": "right",
            "source": "sensor.power",
            "unit": "kWh",
            "round": 2,
        }
    }

    assert await async_setup_component(opp, "sensor", config)

    entity_id = config["sensor"]["source"]
    opp.states.async_set(entity_id, 0, {})
    await opp.async_block_till_done()

    # Testing a power sensor with non-monotonic intervals and values
    for time, value in [(20, 10), (30, 30), (40, 5), (50, 0)]:
        now = dt_util.utcnow() + timedelta(minutes=time)
        with patch("openpeerpower.util.dt.utcnow", return_value=now):
            opp.states.async_set(entity_id, value, {}, force_update=True)
            await opp.async_block_till_done()

    state = opp.states.get("sensor.integration")
    assert state is not None

    assert round(float(state.state), config["sensor"]["round"]) == 9.17

    assert state.attributes.get("unit_of_measurement") == "kWh"


async def test_prefix(opp):
    """Test integration sensor state using a power source."""
    config = {
        "sensor": {
            "platform": "integration",
            "name": "integration",
            "source": "sensor.power",
            "round": 2,
            "unit_prefix": "k",
        }
    }

    assert await async_setup_component(opp, "sensor", config)

    entity_id = config["sensor"]["source"]
    opp.states.async_set(entity_id, 1000, {"unit_of_measurement": "W"})
    await opp.async_block_till_done()

    now = dt_util.utcnow() + timedelta(seconds=3600)
    with patch("openpeerpower.util.dt.utcnow", return_value=now):
        opp.states.async_set(
            entity_id, 1000, {"unit_of_measurement": "W"}, force_update=True
        )
        await opp.async_block_till_done()

    state = opp.states.get("sensor.integration")
    assert state is not None

    # Testing a power sensor at 1000 Watts for 1hour = 1kWh
    assert round(float(state.state), config["sensor"]["round"]) == 1.0
    assert state.attributes.get("unit_of_measurement") == "kWh"


async def test_suffix(opp):
    """Test integration sensor state using a network counter source."""
    config = {
        "sensor": {
            "platform": "integration",
            "name": "integration",
            "source": "sensor.bytes_per_second",
            "round": 2,
            "unit_prefix": "k",
            "unit_time": "s",
        }
    }

    assert await async_setup_component(opp, "sensor", config)

    entity_id = config["sensor"]["source"]
    opp.states.async_set(entity_id, 1000, {})
    await opp.async_block_till_done()

    now = dt_util.utcnow() + timedelta(seconds=10)
    with patch("openpeerpower.util.dt.utcnow", return_value=now):
        opp.states.async_set(entity_id, 1000, {}, force_update=True)
        await opp.async_block_till_done()

    state = opp.states.get("sensor.integration")
    assert state is not None

    # Testing a network speed sensor at 1000 bytes/s over 10s  = 10kbytes
    assert round(float(state.state)) == 10
