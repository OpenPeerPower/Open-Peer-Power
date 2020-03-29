"""Support for alexa Smart Home Skill API."""
import logging

import openpeerpower.core as op

from .const import API_DIRECTIVE, API_HEADER
from .errors import AlexaBridgeUnreachableError, AlexaError
from .handlers import HANDLERS
from .messages import AlexaDirective

_LOGGER = logging.getLogger(__name__)

EVENT_ALEXA_SMART_HOME = "alexa_smart_home"


async def async_handle_message(opp, config, request, context=None, enabled=True):
    """Handle incoming API messages.

    If enabled is False, the response to all messagess will be a
    BRIDGE_UNREACHABLE error. This can be used if the API has been disabled in
    configuration.
    """
    assert request[API_DIRECTIVE][API_HEADER]["payloadVersion"] == "3"

    if context is None:
        context = op.Context()

    directive = AlexaDirective(request)

    try:
        if not enabled:
            raise AlexaBridgeUnreachableError(
                "Alexa API not enabled in Open Peer Power configuration"
            )

        if directive.has_endpoint:
            directive.load_entity(opp, config)

        funct_ref = HANDLERS.get((directive.namespace, directive.name))
        if funct_ref:
            response = await funct_ref(opp, config, directive, context)
            if directive.has_endpoint:
                response.merge_context_properties(directive.endpoint)
        else:
            _LOGGER.warning(
                "Unsupported API request %s/%s", directive.namespace, directive.name
            )
            response = directive.error()
    except AlexaError as err:
        response = directive.error(
            error_type=err.error_type, error_message=err.error_message
        )

    request_info = {"namespace": directive.namespace, "name": directive.name}

    if directive.has_endpoint:
        request_info["entity_id"] = directive.entity_id

    opp.bus.async_fire(
        EVENT_ALEXA_SMART_HOME,
        {
            "request": request_info,
            "response": {"namespace": response.namespace, "name": response.name},
        },
        context=context,
    )

    return response.serialize()
