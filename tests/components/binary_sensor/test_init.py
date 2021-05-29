"""The tests for the Binary sensor component."""
import unittest
from unittest import mock

from openpeerpower.components import binary_sensor
from openpeerpower.const import STATE_OFF, STATE_ON


class TestBinarySensor(unittest.TestCase):
    """Test the binary_sensor base class."""

    def test_state(self):
        """Test binary sensor state."""
        sensor = binary_sensor.BinarySensorDevice()
        assert STATE_OFF == sensor.state
        with mock.patch(
            "openpeerpower.components.binary_sensor.BinarySensorDevice.is_on",
            new=False,
        ):
            assert STATE_OFF == binary_sensor.BinarySensorDevice().state
        with mock.patch(
            "openpeerpower.components.binary_sensor.BinarySensorDevice.is_on",
            new=True,
        ):
            assert STATE_ON == binary_sensor.BinarySensorDevice().state
