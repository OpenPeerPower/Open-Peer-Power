"""Tests for device tracker entities."""
import pytest

from openpeerpower.components.device_tracker.config_entry import (
    BaseTrackerEntity,
    ScannerEntity,
)
from openpeerpower.components.device_tracker.const import (
    ATTR_SOURCE_TYPE,
    DOMAIN,
    SOURCE_TYPE_ROUTER,
)
from openpeerpower.const import ATTR_BATTERY_LEVEL, STATE_HOME, STATE_NOT_HOME

from tests.common import MockConfigEntry


async def test_scanner_entity_device_tracker(opp):
    """Test ScannerEntity based device tracker."""
    config_entry = MockConfigEntry(domain="test")
    config_entry.add_to_opp(opp)

    await opp.config_entries.async_forward_entry_setup(config_entry, DOMAIN)
    await opp.async_block_till_done()

    entity_id = "device_tracker.unnamed_device"
    entity_state = opp.states.get(entity_id)
    assert entity_state.attributes == {
        ATTR_SOURCE_TYPE: SOURCE_TYPE_ROUTER,
        ATTR_BATTERY_LEVEL: 100,
    }
    assert entity_state.state == STATE_NOT_HOME

    entity = opp.data[DOMAIN].get_entity(entity_id)
    entity.set_connected()
    await opp.async_block_till_done()

    entity_state = opp.states.get(entity_id)
    assert entity_state.state == STATE_HOME


def test_scanner_entity():
    """Test coverage for base ScannerEntity entity class."""
    entity = ScannerEntity()
    with pytest.raises(NotImplementedError):
        assert entity.source_type is None
    with pytest.raises(NotImplementedError):
        assert entity.is_connected is None
    with pytest.raises(NotImplementedError):
        assert entity.state == STATE_NOT_HOME
    assert entity.battery_level is None


def test_base_tracker_entity():
    """Test coverage for base BaseTrackerEntity entity class."""
    entity = BaseTrackerEntity()
    with pytest.raises(NotImplementedError):
        assert entity.source_type is None
    assert entity.battery_level is None
    with pytest.raises(NotImplementedError):
        assert entity.state_attributes is None
