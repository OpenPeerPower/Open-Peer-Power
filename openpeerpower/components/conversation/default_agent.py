"""Standard conversastion implementation for Open Peer Power."""
import logging
import re
from typing import Optional

from openpeerpower import core, setup
from openpeerpower.components.cover.intent import INTENT_CLOSE_COVER, INTENT_OPEN_COVER
from openpeerpower.components.shopping_list.intent import (
    INTENT_ADD_ITEM,
    INTENT_LAST_ITEMS,
)
from openpeerpower.const import EVENT_COMPONENT_LOADED
from openpeerpower.core import callback
from openpeerpower.helpers import intent
from openpeerpower.setup import ATTR_COMPONENT

from .agent import AbstractConversationAgent
from .const import DOMAIN
from .util import create_matcher

_LOGGER = logging.getLogger(__name__)

REGEX_TURN_COMMAND = re.compile(r"turn (?P<name>(?: |\w)+) (?P<command>\w+)")
REGEX_TYPE = type(re.compile(""))

UTTERANCES = {
    "cover": {
        INTENT_OPEN_COVER: ["Open [the] [a] [an] {name}[s]"],
        INTENT_CLOSE_COVER: ["Close [the] [a] [an] {name}[s]"],
    },
    "shopping_list": {
        INTENT_ADD_ITEM: ["Add [the] [a] [an] {item} to my shopping list"],
        INTENT_LAST_ITEMS: ["What is on my shopping list"],
    },
}


@core.callback
def async_register(opp, intent_type, utterances):
    """Register utterances and any custom intents for the default agent.

    Registrations don't require conversations to be loaded. They will become
    active once the conversation component is loaded.
    """
    intents = opp.data.setdefault(DOMAIN, {})
    conf = intents.setdefault(intent_type, [])

    for utterance in utterances:
        if isinstance(utterance, REGEX_TYPE):
            conf.append(utterance)
        else:
            conf.append(create_matcher(utterance))


class DefaultAgent(AbstractConversationAgent):
    """Default agent for conversation agent."""

    def __init__(self, opp: core.OpenPeerPower):
        """Initialize the default agent."""
        self.opp = opp

    async def async_initialize(self, config):
        """Initialize the default agent."""
        if "intent" not in self.opp.config.components:
            await setup.async_setup_component(self.opp, "intent", {})

        config = config.get(DOMAIN, {})
        intents = self.opp.data.setdefault(DOMAIN, {})

        for intent_type, utterances in config.get("intents", {}).items():
            conf = intents.get(intent_type)

            if conf is None:
                conf = intents[intent_type] = []

            conf.extend(create_matcher(utterance) for utterance in utterances)

        # We strip trailing 's' from name because our state matcher will fail
        # if a letter is not there. By removing 's' we can match singular and
        # plural names.

        async_register(
            self.opp,
            intent.INTENT_TURN_ON,
            ["Turn [the] [a] {name}[s] on", "Turn on [the] [a] [an] {name}[s]"],
        )
        async_register(
            self.opp,
            intent.INTENT_TURN_OFF,
            ["Turn [the] [a] [an] {name}[s] off", "Turn off [the] [a] [an] {name}[s]"],
        )
        async_register(
            self.opp,
            intent.INTENT_TOGGLE,
            ["Toggle [the] [a] [an] {name}[s]", "[the] [a] [an] {name}[s] toggle"],
        )

        @callback
        def component_loaded(event):
            """Handle a new component loaded."""
            self.register_utterances(event.data[ATTR_COMPONENT])

        self.opp.bus.async_listen(EVENT_COMPONENT_LOADED, component_loaded)

        # Check already loaded components.
        for component in self.opp.config.components:
            self.register_utterances(component)

    @callback
    def register_utterances(self, component):
        """Register utterances for a component."""
        if component not in UTTERANCES:
            return
        for intent_type, sentences in UTTERANCES[component].items():
            async_register(self.opp, intent_type, sentences)

    async def async_process(
        self, text: str, context: core.Context, conversation_id: Optional[str] = None
    ) -> intent.IntentResponse:
        """Process a sentence."""
        intents = self.opp.data[DOMAIN]

        for intent_type, matchers in intents.items():
            for matcher in matchers:
                match = matcher.match(text)

                if not match:
                    continue

                return await intent.async_handle(
                    self.opp,
                    DOMAIN,
                    intent_type,
                    {key: {"value": value} for key, value in match.groupdict().items()},
                    text,
                    context,
                )
