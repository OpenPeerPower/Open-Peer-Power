"""
Support for showing the date and the time.

For more details about this platform, please refer to the documentation at
https://open-peer-power.io/components/sensor.time_date/
"""
from datetime import timedelta
import logging

from openpeerpower.components.sensor import PLATFORM_SCHEMA
from openpeerpower.const import CONF_DISPLAY_OPTIONS
import openpeerpower.util.dt as dt_util

_LOGGER = logging.getLogger(__name__)

TIME_STR_FORMAT = '%H:%M'

OPTION_TYPES = {
    'time': 'Time',
    'date': 'Date',
    'date_time': 'Date & Time',
    'time_date': 'Time & Date',
    'beat': 'Internet Time',
    'time_utc': 'Time (UTC)',
}

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Optional(CONF_DISPLAY_OPTIONS, default=['time']):
        vol.All(cv.ensure_list, [vol.In(OPTION_TYPES)]),
})


class TimeDateSensor(Entity):
    """Implementation of a Time and Date sensor."""

    def __init__(self, opp, option_type):
        """Initialize the sensor."""
        self._name = OPTION_TYPES[option_type]
        self.type = option_type
        self._state = None
        self.opp = opp

        self._update_internal_state(dt_util.utcnow())

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def icon(self):
        """Icon to use in the frontend, if any."""
        if 'date' in self.type and 'time' in self.type:
            return 'mdi:calendar-clock'
        if 'date' in self.type:
            return 'mdi:calendar'
        return 'mdi:clock'

 