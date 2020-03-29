"""The tests for the demo platform."""
import unittest
from unittest.mock import patch

from openpeerpower.components import geo_location
from openpeerpower.components.demo.geo_location import (
    DEFAULT_UNIT_OF_MEASUREMENT,
    DEFAULT_UPDATE_INTERVAL,
    NUMBER_OF_DEMO_DEVICES,
)
from openpeerpower.setup import setup_component
import openpeerpower.util.dt as dt_util

from tests.common import (
    assert_setup_component,
    fire_time_changed,
    get_test_open_peer_power,
)

CONFIG = {geo_location.DOMAIN: [{"platform": "demo"}]}


class TestDemoPlatform(unittest.TestCase):
    """Test the demo platform."""

    def setUp(self):
        """Initialize values for this testcase class."""
        self.opp = get_test_open_peer_power()

    def tearDown(self):
        """Stop everything that was started."""
        self.opp.stop()

    def test_setup_platform(self):
        """Test setup of demo platform via configuration."""
        utcnow = dt_util.utcnow()
        # Patching 'utcnow' to gain more control over the timed update.
        with patch("openpeerpower.util.dt.utcnow", return_value=utcnow):
            with assert_setup_component(1, geo_location.DOMAIN):
                assert setup_component(self.opp, geo_location.DOMAIN, CONFIG)
            self.opp.block_till_done()

            # In this test, one zone and geolocation entities have been
            # generated.
            all_states = [
                self.opp.states.get(entity_id)
                for entity_id in self.opp.states.entity_ids(geo_location.DOMAIN)
            ]
            assert len(all_states) == NUMBER_OF_DEMO_DEVICES

            for state in all_states:
                # Check a single device's attributes.
                if state.domain != geo_location.DOMAIN:
                    # ignore home zone state
                    continue
                assert (
                    abs(state.attributes["latitude"] - self.opp.config.latitude) < 1.0
                )
                assert (
                    abs(state.attributes["longitude"] - self.opp.config.longitude)
                    < 1.0
                )
                assert (
                    state.attributes["unit_of_measurement"]
                    == DEFAULT_UNIT_OF_MEASUREMENT
                )

            # Update (replaces 1 device).
            fire_time_changed(self.opp, utcnow + DEFAULT_UPDATE_INTERVAL)
            self.opp.block_till_done()
            # Get all states again, ensure that the number of states is still
            # the same, but the lists are different.
            all_states_updated = [
                self.opp.states.get(entity_id)
                for entity_id in self.opp.states.entity_ids(geo_location.DOMAIN)
            ]
            assert len(all_states_updated) == NUMBER_OF_DEMO_DEVICES
            assert all_states != all_states_updated
