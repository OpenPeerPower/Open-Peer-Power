"""
Core components of Open Peer Power 
Power Monitoring and Control framework for observing the state
of entities and reacting to changes.
"""
import datetime
import enum
import logging
import os
import pathlib
import re
import sys
import threading
from time import monotonic
import uuid

from types import MappingProxyType

import attr

from openpeerpower.const import (
    EVENT_SERVICE_EXECUTED, EVENT_SERVICE_REGISTERED, EVENT_STATE_CHANGED,
    EVENT_TIME_CHANGED, EVENT_TIMER_OUT_OF_SYNC, MATCH_ALL, __version__)
from openpeerpower import loader

class OpenPeerPower:
    """Root object of Open Peer Power ."""

    def __init__(self) -> None:
        """Initialize new OPP object."""
        # self.components = loader.Components(self)
        # This is a dictionary that any component can store any data on.
        self.data = {}  # type: dict
        self.exit_code = 0  # type: int
 