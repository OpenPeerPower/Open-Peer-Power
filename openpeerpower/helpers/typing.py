"""Typing Helpers for Open Peer Power."""
from typing import Dict, Any, Tuple, Optional

import openpeerpower.core

# pylint: disable=invalid-name

GPSType = Tuple[float, float]
ConfigType = Dict[str, Any]
EventType = openpeerpower.core.Event
OpenPeerPowerType = openpeerpower.core.OpenPeerPower
ServiceDataType = Dict[str, Any]
TemplateVarsType = Optional[Dict[str, Any]]

# Custom type for recorder Queries
QueryType = Any
