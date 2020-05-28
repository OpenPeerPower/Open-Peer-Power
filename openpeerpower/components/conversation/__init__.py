"""Support for functionality to have conversations with Open Peer Power."""
import logging
import re

import voluptuous as vol

from openpeerpower import core
from openpeerpower.components import http, websocket_api
from openpeerpower.components.http.data_validator import RequestDataValidator
from openpeerpower.helpers import config_validation as cv, intent
from openpeerpower.loader import bind_opp

from .agent import AbstractConversationAgent
from .default_agent import DefaultAgent, async_register

_LOGGER = logging.getLogger(__name__)

ATTR_TEXT = "text"

DOMAIN = "conversation"

REGEX_TYPE = type(re.compile(""))
DATA_AGENT = "conversation_agent"
DATA_CONFIG = "conversation_config"

SERVICE_PROCESS = "process"

SERVICE_PROCESS_SCHEMA = vol.Schema({vol.Required(ATTR_TEXT): cv.string})

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Optional("intents"): vol.Schema(
                    {cv.string: vol.All(cv.ensure_list, [cv.string])}
                )
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)

async_register = bind_opp(async_register)  # pylint: disable=invalid-name


@core.callback
@bind_opp
def async_set_agent(opp: core.OpenPeerPower, agent: AbstractConversationAgent):
    """Set the agent to handle the conversations."""
    opp.data[DATA_AGENT] = agent


async def async_setup(opp, config):
    """Register the process service."""
    opp.data[DATA_CONFIG] = config

    async def handle_service(service):
        """Parse text into commands."""
        text = service.data[ATTR_TEXT]
        _LOGGER.debug("Processing: <%s>", text)
        agent = await _get_agent(opp)
        try:
            await agent.async_process(text, service.context)
        except intent.IntentHandleError as err:
            _LOGGER.error("Error processing %s: %s", text, err)

    opp.services.async_register(
        DOMAIN, SERVICE_PROCESS, handle_service, schema=SERVICE_PROCESS_SCHEMA
    )
    opp.http.register_view(ConversationProcessView())
    opp.components.websocket_api.async_register_command(websocket_process)
    opp.components.websocket_api.async_register_command(websocket_get_agent_info)
    opp.components.websocket_api.async_register_command(websocket_set_onboarding)

    return True


@websocket_api.async_response
@websocket_api.websocket_command(
    {"type": "conversation/process", "text": str, vol.Optional("conversation_id"): str}
)
async def websocket_process(opp, connection, msg):
    """Process text."""
    connection.send_result(
        msg["id"],
        await _async_converse(
            opp, msg["text"], msg.get("conversation_id"), connection.context(msg)
        ),
    )


@websocket_api.async_response
@websocket_api.websocket_command({"type": "conversation/agent/info"})
async def websocket_get_agent_info(opp, connection, msg):
    """Do we need onboarding."""
    agent = await _get_agent(opp)

    connection.send_result(
        msg["id"],
        {
            "onboarding": await agent.async_get_onboarding(),
            "attribution": agent.attribution,
        },
    )


@websocket_api.async_response
@websocket_api.websocket_command({"type": "conversation/onboarding/set", "shown": bool})
async def websocket_set_onboarding(opp, connection, msg):
    """Set onboarding status."""
    agent = await _get_agent(opp)

    success = await agent.async_set_onboarding(msg["shown"])

    if success:
        connection.send_result(msg["id"])
    else:
        connection.send_error(msg["id"])


class ConversationProcessView(http.OpenPeerPowerView):
    """View to process text."""

    url = "/api/conversation/process"
    name = "api:conversation:process"

    @RequestDataValidator(
        vol.Schema({vol.Required("text"): str, vol.Optional("conversation_id"): str})
    )
    async def post(self, request, data):
        """Send a request for processing."""
        opp = request.app["opp"]

        try:
            intent_result = await _async_converse(
                opp, data["text"], data.get("conversation_id"), self.context(request)
            )
        except intent.IntentError as err:
            _LOGGER.error("Error handling intent: %s", err)
            return self.json(
                {
                    "success": False,
                    "error": {
                        "code": str(err.__class__.__name__).lower(),
                        "message": str(err),
                    },
                },
                status_code=500,
            )

        return self.json(intent_result)


async def _get_agent(opp: core.OpenPeerPower) -> AbstractConversationAgent:
    """Get the active conversation agent."""
    agent = opp.data.get(DATA_AGENT)
    if agent is None:
        agent = opp.data[DATA_AGENT] = DefaultAgent(opp)
        await agent.async_initialize(opp.data.get(DATA_CONFIG))
    return agent


async def _async_converse(
    opp: core.OpenPeerPower, text: str, conversation_id: str, context: core.Context
) -> intent.IntentResponse:
    """Process text and get intent."""
    agent = await _get_agent(opp)
    try:
        intent_result = await agent.async_process(text, context, conversation_id)
    except intent.IntentHandleError as err:
        intent_result = intent.IntentResponse()
        intent_result.async_set_speech(str(err))

    if intent_result is None:
        intent_result = intent.IntentResponse()
        intent_result.async_set_speech("Sorry, I didn't understand that")

    return intent_result
