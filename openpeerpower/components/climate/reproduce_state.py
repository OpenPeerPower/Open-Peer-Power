"""Module that groups code required to handle state restore for component."""
import asyncio
from typing import Iterable, Optional

from openpeerpower.const import (
    ATTR_TEMPERATURE, SERVICE_TURN_OFF,
    SERVICE_TURN_ON, STATE_OFF, STATE_ON)
from openpeerpower.core import Context, State
from openpeerpower.helpers.typing import OpenPeerPowerType
from openpeerpower.loader import bind_opp

from .const import (
    ATTR_AUX_HEAT,
    ATTR_AWAY_MODE,
    ATTR_TARGET_TEMP_HIGH,
    ATTR_TARGET_TEMP_LOW,
    ATTR_HOLD_MODE,
    ATTR_OPERATION_MODE,
    ATTR_SWING_MODE,
    ATTR_HUMIDITY,
    SERVICE_SET_AWAY_MODE,
    SERVICE_SET_AUX_HEAT,
    SERVICE_SET_TEMPERATURE,
    SERVICE_SET_HOLD_MODE,
    SERVICE_SET_OPERATION_MODE,
    SERVICE_SET_SWING_MODE,
    SERVICE_SET_HUMIDITY,
    DOMAIN,
)


async def _async_reproduce_states(opp: OpenPeerPowerType,
                                  state: State,
                                  context: Optional[Context] = None) -> None:
    """Reproduce component states."""
    async def call_service(service: str, keys: Iterable):
        """Call service with set of attributes given."""
        data = {}
        data['entity_id'] = state.entity_id
        for key in keys:
            if key in state.attributes:
                data[key] = state.attributes[key]

        await opp.services.async_call(
            DOMAIN, service, data,
            blocking=True, context=context)

    if state.state == STATE_ON:
        await call_service(SERVICE_TURN_ON, [])
    elif state.state == STATE_OFF:
        await call_service(SERVICE_TURN_OFF, [])

    if ATTR_AUX_HEAT in state.attributes:
        await call_service(SERVICE_SET_AUX_HEAT, [ATTR_AUX_HEAT])

    if ATTR_AWAY_MODE in state.attributes:
        await call_service(SERVICE_SET_AWAY_MODE, [ATTR_AWAY_MODE])

    if (ATTR_TEMPERATURE in state.attributes) or \
            (ATTR_TARGET_TEMP_HIGH in state.attributes) or \
            (ATTR_TARGET_TEMP_LOW in state.attributes):
        await call_service(SERVICE_SET_TEMPERATURE,
                           [ATTR_TEMPERATURE,
                            ATTR_TARGET_TEMP_HIGH,
                            ATTR_TARGET_TEMP_LOW])

    if ATTR_HOLD_MODE in state.attributes:
        await call_service(SERVICE_SET_HOLD_MODE,
                           [ATTR_HOLD_MODE])

    if ATTR_OPERATION_MODE in state.attributes:
        await call_service(SERVICE_SET_OPERATION_MODE,
                           [ATTR_OPERATION_MODE])

    if ATTR_SWING_MODE in state.attributes:
        await call_service(SERVICE_SET_SWING_MODE,
                           [ATTR_SWING_MODE])

    if ATTR_HUMIDITY in state.attributes:
        await call_service(SERVICE_SET_HUMIDITY,
                           [ATTR_HUMIDITY])


@bind_opp
async def async_reproduce_states(opp: OpenPeerPowerType,
                                 states: Iterable[State],
                                 context: Optional[Context] = None) -> None:
    """Reproduce component states."""
    await asyncio.gather(*[
        _async_reproduce_states(opp, state, context)
        for state in states])
