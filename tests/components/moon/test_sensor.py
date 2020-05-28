"""The test for the moon sensor platform."""
from datetime import datetime
import unittest
from unittest.mock import patch

from openpeerpower.setup import setup_component
import openpeerpower.util.dt as dt_util

from tests.common import get_test_open_peer_power

DAY1 = datetime(2017, 1, 1, 1, tzinfo=dt_util.UTC)
DAY2 = datetime(2017, 1, 18, 1, tzinfo=dt_util.UTC)


class TestMoonSensor(unittest.TestCase):
    """Test the Moon sensor."""

    def setup_method(self, method):
        """Set up things to be run when tests are started."""
        self.opp = get_test_open_peer_power()

    def teardown_method(self, method):
        """Stop everything that was started."""
        self.opp.stop()

    @patch("openpeerpower.components.moon.sensor.dt_util.utcnow", return_value=DAY1)
    def test_moon_day1(self, mock_request):
        """Test the Moon sensor."""
        config = {"sensor": {"platform": "moon", "name": "moon_day1"}}

        assert setup_component(self.opp, "sensor", config)

        state = self.opp.states.get("sensor.moon_day1")
        assert state.state == "waxing_crescent"

    @patch("openpeerpower.components.moon.sensor.dt_util.utcnow", return_value=DAY2)
    def test_moon_day2(self, mock_request):
        """Test the Moon sensor."""
        config = {"sensor": {"platform": "moon", "name": "moon_day2"}}

        assert setup_component(self.opp, "sensor", config)

        state = self.opp.states.get("sensor.moon_day2")
        assert state.state == "waning_gibbous"
