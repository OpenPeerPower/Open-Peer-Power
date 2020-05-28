"""Support for Almond."""
import asyncio
from datetime import timedelta
import logging
import time
from typing import Optional

from aiohttp import ClientError, ClientSession
import async_timeout
from pyalmond import AbstractAlmondWebAuth, AlmondLocalAuth, WebAlmondAPI
import voluptuous as vol

from openpeerpower import config_entries
from openpeerpower.auth.const import GROUP_ID_ADMIN
from openpeerpower.components import conversation
from openpeerpower.const import CONF_HOST, CONF_TYPE, EVENT_OPENPEERPOWER_START
from openpeerpower.core import Context, CoreState, OpenPeerPower
from openpeerpower.exceptions import ConfigEntryNotReady
from openpeerpower.helpers import (
    aiohttp_client,
    config_entry_oauth2_flow,
    config_validation as cv,
    event,
    intent,
    network,
    storage,
)

from . import config_flow
from .const import DOMAIN, TYPE_LOCAL, TYPE_OAUTH2

CONF_CLIENT_ID = "client_id"
CONF_CLIENT_SECRET = "client_secret"

STORAGE_VERSION = 1
STORAGE_KEY = DOMAIN

ALMOND_SETUP_DELAY = 30

DEFAULT_OAUTH2_HOST = "https://almond.stanford.edu"
DEFAULT_LOCAL_HOST = "http://localhost:3000"

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Any(
            vol.Schema(
                {
                    vol.Required(CONF_TYPE): TYPE_OAUTH2,
                    vol.Required(CONF_CLIENT_ID): cv.string,
                    vol.Required(CONF_CLIENT_SECRET): cv.string,
                    vol.Optional(CONF_HOST, default=DEFAULT_OAUTH2_HOST): cv.url,
                }
            ),
            vol.Schema(
                {vol.Required(CONF_TYPE): TYPE_LOCAL, vol.Required(CONF_HOST): cv.url}
            ),
        )
    },
    extra=vol.ALLOW_EXTRA,
)
_LOGGER = logging.getLogger(__name__)


async def async_setup(opp, config):
    """Set up the Almond component."""
    opp.data[DOMAIN] = {}

    if DOMAIN not in config:
        return True

    conf = config[DOMAIN]

    host = conf[CONF_HOST]

    if conf[CONF_TYPE] == TYPE_OAUTH2:
        config_flow.AlmondFlowHandler.async_register_implementation(
            opp,
            config_entry_oauth2_flow.LocalOAuth2Implementation(
                opp,
                DOMAIN,
                conf[CONF_CLIENT_ID],
                conf[CONF_CLIENT_SECRET],
                f"{host}/me/api/oauth2/authorize",
                f"{host}/me/api/oauth2/token",
            ),
        )
        return True

    if not opp.config_entries.async_entries(DOMAIN):
        opp.async_create_task(
            opp.config_entries.flow.async_init(
                DOMAIN,
                context={"source": config_entries.SOURCE_IMPORT},
                data={"type": TYPE_LOCAL, "host": conf[CONF_HOST]},
            )
        )
    return True


async def async_setup_entry(opp: OpenPeerPower, entry: config_entries.ConfigEntry):
    """Set up Almond config entry."""
    websession = aiohttp_client.async_get_clientsession(opp)

    if entry.data["type"] == TYPE_LOCAL:
        auth = AlmondLocalAuth(entry.data["host"], websession)
    else:
        # OAuth2
        implementation = await config_entry_oauth2_flow.async_get_config_entry_implementation(
            opp, entry
        )
        oauth_session = config_entry_oauth2_flow.OAuth2Session(
            opp, entry, implementation
        )
        auth = AlmondOAuth(entry.data["host"], websession, oauth_session)

    api = WebAlmondAPI(auth)
    agent = AlmondAgent(opp, api, entry)

    # Opp.io does its own configuration.
    if not entry.data.get("is_oppio"):
        # If we're not starting or local, set up Almond right away
        if opp.state != CoreState.not_running or entry.data["type"] == TYPE_LOCAL:
            await _configure_almond_for_ha(opp, entry, api)

        else:
            # OAuth2 implementations can potentially rely on the HA Cloud url.
            # This url is not be available until 30 seconds after boot.

            async def configure_almond(_now):
                try:
                    await _configure_almond_for_ha(opp, entry, api)
                except ConfigEntryNotReady:
                    _LOGGER.warning(
                        "Unable to configure Almond to connect to Open Peer Power"
                    )

            async def almond_opp_start(_event):
                event.async_call_later(opp, ALMOND_SETUP_DELAY, configure_almond)

            opp.bus.async_listen_once(EVENT_OPENPEERPOWER_START, almond_opp_start)

    conversation.async_set_agent(opp, agent)
    return True


async def _configure_almond_for_ha(
    opp: OpenPeerPower, entry: config_entries.ConfigEntry, api: WebAlmondAPI
):
    """Configure Almond to connect to HA."""

    if entry.data["type"] == TYPE_OAUTH2:
        # If we're connecting over OAuth2, we will only set up connection
        # with Open Peer Power if we're remotely accessible.
        opp_url = network.async_get_external_url(opp)
    else:
        opp_url = opp.config.api.base_url

    # If opp_url is None, we're not going to configure Almond to connect to HA.
    if opp_url is None:
        return

    _LOGGER.debug("Configuring Almond to connect to Open Peer Power at %s", opp_url)
    store = storage.Store(opp, STORAGE_VERSION, STORAGE_KEY)
    data = await store.async_load()

    if data is None:
        data = {}

    user = None
    if "almond_user" in data:
        user = await opp.auth.async_get_user(data["almond_user"])

    if user is None:
        user = await opp.auth.async_create_system_user("Almond", [GROUP_ID_ADMIN])
        data["almond_user"] = user.id
        await store.async_save(data)

    refresh_token = await opp.auth.async_create_refresh_token(
        user,
        # Almond will be fine as long as we restart once every 5 years
        access_token_expiration=timedelta(days=365 * 5),
    )

    # Create long lived access token
    access_token = opp.auth.async_create_access_token(refresh_token)

    # Store token in Almond
    try:
        with async_timeout.timeout(30):
            await api.async_create_device(
                {
                    "kind": "io.open-peer-power",
                    "oppUrl": opp_url,
                    "accessToken": access_token,
                    "refreshToken": "",
                    # 5 years from now in ms.
                    "accessTokenExpires": (time.time() + 60 * 60 * 24 * 365 * 5) * 1000,
                }
            )
    except (asyncio.TimeoutError, ClientError) as err:
        if isinstance(err, asyncio.TimeoutError):
            msg = "Request timeout"
        else:
            msg = err
        _LOGGER.warning("Unable to configure Almond: %s", msg)
        await opp.auth.async_remove_refresh_token(refresh_token)
        raise ConfigEntryNotReady

    # Clear all other refresh tokens
    for token in list(user.refresh_tokens.values()):
        if token.id != refresh_token.id:
            await opp.auth.async_remove_refresh_token(token)


async def async_unload_entry(opp, entry):
    """Unload Almond."""
    conversation.async_set_agent(opp, None)
    return True


class AlmondOAuth(AbstractAlmondWebAuth):
    """Almond Authentication using OAuth2."""

    def __init__(
        self,
        host: str,
        websession: ClientSession,
        oauth_session: config_entry_oauth2_flow.OAuth2Session,
    ):
        """Initialize Almond auth."""
        super().__init__(host, websession)
        self._oauth_session = oauth_session

    async def async_get_access_token(self):
        """Return a valid access token."""
        if not self._oauth_session.valid_token:
            await self._oauth_session.async_ensure_token_valid()

        return self._oauth_session.token["access_token"]


class AlmondAgent(conversation.AbstractConversationAgent):
    """Almond conversation agent."""

    def __init__(
        self, opp: OpenPeerPower, api: WebAlmondAPI, entry: config_entries.ConfigEntry
    ):
        """Initialize the agent."""
        self.opp = opp
        self.api = api
        self.entry = entry

    @property
    def attribution(self):
        """Return the attribution."""
        return {"name": "Powered by Almond", "url": "https://almond.stanford.edu/"}

    async def async_get_onboarding(self):
        """Get onboard url if not onboarded."""
        if self.entry.data.get("onboarded"):
            return None

        host = self.entry.data["host"]
        if self.entry.data.get("is_oppio"):
            host = "/core_almond"
        return {
            "text": "Would you like to opt-in to share your anonymized commands with Stanford to improve Almond's responses?",
            "url": f"{host}/conversation",
        }

    async def async_set_onboarding(self, shown):
        """Set onboarding status."""
        self.opp.config_entries.async_update_entry(
            self.entry, data={**self.entry.data, "onboarded": shown}
        )

        return True

    async def async_process(
        self, text: str, context: Context, conversation_id: Optional[str] = None
    ) -> intent.IntentResponse:
        """Process a sentence."""
        response = await self.api.async_converse_text(text, conversation_id)

        first_choice = True
        buffer = ""
        for message in response["messages"]:
            if message["type"] == "text":
                buffer += "\n" + message["text"]
            elif message["type"] == "picture":
                buffer += "\n Picture: " + message["url"]
            elif message["type"] == "rdl":
                buffer += (
                    "\n Link: "
                    + message["rdl"]["displayTitle"]
                    + " "
                    + message["rdl"]["webCallback"]
                )
            elif message["type"] == "choice":
                if first_choice:
                    first_choice = False
                else:
                    buffer += ","
                buffer += f" {message['title']}"

        intent_result = intent.IntentResponse()
        intent_result.async_set_speech(buffer.strip())
        return intent_result
