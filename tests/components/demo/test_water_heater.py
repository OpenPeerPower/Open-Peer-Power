"""The tests for the demo water_heater component."""
import unittest

import pytest
import voluptuous as vol

from openpeerpower.components import water_heater
from openpeerpower.setup import setup_component
from openpeerpower.util.unit_system import IMPERIAL_SYSTEM

from tests.common import get_test_open_peer_power
from tests.components.water_heater import common

ENTITY_WATER_HEATER = "water_heater.demo_water_heater"
ENTITY_WATER_HEATER_CELSIUS = "water_heater.demo_water_heater_celsius"


class TestDemowater_heater(unittest.TestCase):
    """Test the demo water_heater."""

    def setUp(self):  # pylint: disable=invalid-name
        """Set up things to be run when tests are started."""
        self.opp = get_test_open_peer_power()
        self.opp.config.units = IMPERIAL_SYSTEM
        assert setup_component(
            self.opp, water_heater.DOMAIN, {"water_heater": {"platform": "demo"}}
        )

    def tearDown(self):  # pylint: disable=invalid-name
        """Stop down everything that was started."""
        self.opp.stop()

    def test_setup_params(self):
        """Test the initial parameters."""
        state = self.opp.states.get(ENTITY_WATER_HEATER)
        assert 119 == state.attributes.get("temperature")
        assert "off" == state.attributes.get("away_mode")
        assert "eco" == state.attributes.get("operation_mode")

    def test_default_setup_params(self):
        """Test the setup with default parameters."""
        state = self.opp.states.get(ENTITY_WATER_HEATER)
        assert 110 == state.attributes.get("min_temp")
        assert 140 == state.attributes.get("max_temp")

    def test_set_only_target_temp_bad_attr(self):
        """Test setting the target temperature without required attribute."""
        state = self.opp.states.get(ENTITY_WATER_HEATER)
        assert 119 == state.attributes.get("temperature")
        with pytest.raises(vol.Invalid):
            common.set_temperature(self.opp, None, ENTITY_WATER_HEATER)
        self.opp.block_till_done()
        assert 119 == state.attributes.get("temperature")

    def test_set_only_target_temp(self):
        """Test the setting of the target temperature."""
        state = self.opp.states.get(ENTITY_WATER_HEATER)
        assert 119 == state.attributes.get("temperature")
        common.set_temperature(self.opp, 110, ENTITY_WATER_HEATER)
        self.opp.block_till_done()
        state = self.opp.states.get(ENTITY_WATER_HEATER)
        assert 110 == state.attributes.get("temperature")

    def test_set_operation_bad_attr_and_state(self):
        """Test setting operation mode without required attribute.

        Also check the state.
        """
        state = self.opp.states.get(ENTITY_WATER_HEATER)
        assert "eco" == state.attributes.get("operation_mode")
        assert "eco" == state.state
        with pytest.raises(vol.Invalid):
            common.set_operation_mode(self.opp, None, ENTITY_WATER_HEATER)
        self.opp.block_till_done()
        state = self.opp.states.get(ENTITY_WATER_HEATER)
        assert "eco" == state.attributes.get("operation_mode")
        assert "eco" == state.state

    def test_set_operation(self):
        """Test setting of new operation mode."""
        state = self.opp.states.get(ENTITY_WATER_HEATER)
        assert "eco" == state.attributes.get("operation_mode")
        assert "eco" == state.state
        common.set_operation_mode(self.opp, "electric", ENTITY_WATER_HEATER)
        self.opp.block_till_done()
        state = self.opp.states.get(ENTITY_WATER_HEATER)
        assert "electric" == state.attributes.get("operation_mode")
        assert "electric" == state.state

    def test_set_away_mode_bad_attr(self):
        """Test setting the away mode without required attribute."""
        state = self.opp.states.get(ENTITY_WATER_HEATER)
        assert "off" == state.attributes.get("away_mode")
        with pytest.raises(vol.Invalid):
            common.set_away_mode(self.opp, None, ENTITY_WATER_HEATER)
        self.opp.block_till_done()
        assert "off" == state.attributes.get("away_mode")

    def test_set_away_mode_on(self):
        """Test setting the away mode on/true."""
        common.set_away_mode(self.opp, True, ENTITY_WATER_HEATER)
        self.opp.block_till_done()
        state = self.opp.states.get(ENTITY_WATER_HEATER)
        assert "on" == state.attributes.get("away_mode")

    def test_set_away_mode_off(self):
        """Test setting the away mode off/false."""
        common.set_away_mode(self.opp, False, ENTITY_WATER_HEATER_CELSIUS)
        self.opp.block_till_done()
        state = self.opp.states.get(ENTITY_WATER_HEATER_CELSIUS)
        assert "off" == state.attributes.get("away_mode")

    def test_set_only_target_temp_with_convert(self):
        """Test the setting of the target temperature."""
        state = self.opp.states.get(ENTITY_WATER_HEATER_CELSIUS)
        assert 113 == state.attributes.get("temperature")
        common.set_temperature(self.opp, 114, ENTITY_WATER_HEATER_CELSIUS)
        self.opp.block_till_done()
        state = self.opp.states.get(ENTITY_WATER_HEATER_CELSIUS)
        assert 114 == state.attributes.get("temperature")
