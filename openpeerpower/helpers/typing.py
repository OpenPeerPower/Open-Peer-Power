"""Typing Helpers for Open Peer Power."""
from typing import Any, Dict, Optional, Tuple

import openpeerpower.core

# pylint: disable=invalid-name

GPSType = Tuple[float, float]
ConfigType = Dict[str, Any]
ContextType = openpeerpower.core.Context
EventType = openpeerpower.core.Event
OpenPeerPowerType = openpeerpower.core.OpenPeerPower
ServiceCallType = openpeerpower.core.ServiceCall
ServiceDataType = Dict[str, Any]
TemplateVarsType = Optional[Dict[str, Any]]

# Custom type for recorder Queries
QueryType = Any
