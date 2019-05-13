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
from typing import (
    Optional,
    Any,
    Callable,
    List,
    TypeVar,
    Dict,
    Coroutine,
    Set,
    TYPE_CHECKING,
    Awaitable,
    Iterator
    )

import attr

from openpeerpower.const import (
    EVENT_SERVICE_EXECUTED, EVENT_SERVICE_REGISTERED, EVENT_STATE_CHANGED,
    EVENT_TIME_CHANGED, EVENT_TIMER_OUT_OF_SYNC, MATCH_ALL, __version__)
from openpeerpower import loader
# Typing imports that create a circular dependency
# pylint: disable=using-constant-test
if TYPE_CHECKING:
    from openpeerpower.config_entries import ConfigEntries  # noqa
    
# pylint: disable=invalid-name
T = TypeVar('T')
CALLABLE_T = TypeVar('CALLABLE_T', bound=Callable)
CALLBACK_TYPE = Callable[[], None]
DOMAIN = 'openpeerpower'

def callback(func: CALLABLE_T) -> CALLABLE_T:
    """Annotation to mark method as safe to call from within the event loop."""
    setattr(func, '_hass_callback', True)
    return func
    
class OpenPeerPower:
    """Root object of Open Peer Power ."""

    def __init__(self) -> None:
        """Initialize new OPP object."""
        # self.components = loader.Components(self)
        # This is a dictionary that any component can store any data on.
        self.data = {}  # type: dict
        self.exit_code = 0  # type: int
 
@attr.s(slots=True, frozen=True)
class Context:
    """The context that triggered something."""

    user_id = attr.ib(
        type=str,
        default=None,
    )
    parent_id = attr.ib(
        type=Optional[str],
        default=None
    )
    id = attr.ib(
        type=str,
        default=attr.Factory(lambda: uuid.uuid4().hex),
    )

    def as_dict(self) -> dict:
        """Return a dictionary representation of the context."""
        return {
            'id': self.id,
            'parent_id': self.parent_id,
            'user_id': self.user_id,
        }