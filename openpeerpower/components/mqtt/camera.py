"""Camera that loads a picture from an MQTT topic."""
import logging

import voluptuous as vol

from openpeerpower.components import camera, mqtt
from openpeerpower.components.camera import PLATFORM_SCHEMA, Camera
from openpeerpower.const import CONF_DEVICE, CONF_NAME
from openpeerpower.core import callback
from openpeerpower.helpers import config_validation as cv
from openpeerpower.helpers.dispatcher import async_dispatcher_connect
from openpeerpower.helpers.typing import ConfigType, OpenPeerPowerType

from . import (
    ATTR_DISCOVERY_HASH,
    CONF_UNIQUE_ID,
    MqttDiscoveryUpdate,
    MqttEntityDeviceInfo,
    subscription,
)
from .discovery import MQTT_DISCOVERY_NEW, clear_discovery_hash

_LOGGER = logging.getLogger(__name__)

CONF_TOPIC = "topic"
DEFAULT_NAME = "MQTT Camera"

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
        vol.Required(CONF_TOPIC): mqtt.valid_subscribe_topic,
        vol.Optional(CONF_UNIQUE_ID): cv.string,
        vol.Optional(CONF_DEVICE): mqtt.MQTT_ENTITY_DEVICE_INFO_SCHEMA,
    }
)


async def async_setup_platform(
    opp: OpenPeerPowerType, config: ConfigType, async_add_entities, discovery_info=None
):
    """Set up MQTT camera through configuration.yaml."""
    await _async_setup_entity(config, async_add_entities)


async def async_setup_entry(opp, config_entry, async_add_entities):
    """Set up MQTT camera dynamically through MQTT discovery."""

    async def async_discover(discovery_payload):
        """Discover and add a MQTT camera."""
        try:
            discovery_hash = discovery_payload.pop(ATTR_DISCOVERY_HASH)
            config = PLATFORM_SCHEMA(discovery_payload)
            await _async_setup_entity(
                config, async_add_entities, config_entry, discovery_hash
            )
        except Exception:
            if discovery_hash:
                clear_discovery_hash(opp, discovery_hash)
            raise

    async_dispatcher_connect(
        opp, MQTT_DISCOVERY_NEW.format(camera.DOMAIN, "mqtt"), async_discover
    )


async def _async_setup_entity(
    config, async_add_entities, config_entry=None, discovery_hash=None
):
    """Set up the MQTT Camera."""
    async_add_entities([MqttCamera(config, config_entry, discovery_hash)])


class MqttCamera(MqttDiscoveryUpdate, MqttEntityDeviceInfo, Camera):
    """representation of a MQTT camera."""

    def __init__(self, config, config_entry, discovery_hash):
        """Initialize the MQTT Camera."""
        self._config = config
        self._unique_id = config.get(CONF_UNIQUE_ID)
        self._sub_state = None

        self._qos = 0
        self._last_image = None

        device_config = config.get(CONF_DEVICE)

        Camera.__init__(self)
        MqttDiscoveryUpdate.__init__(self, discovery_hash, self.discovery_update)
        MqttEntityDeviceInfo.__init__(self, device_config, config_entry)

    async def async_added_to_opp(self):
        """Subscribe MQTT events."""
        await super().async_added_to_opp()
        await self._subscribe_topics()

    async def discovery_update(self, discovery_payload):
        """Handle updated discovery message."""
        config = PLATFORM_SCHEMA(discovery_payload)
        self._config = config
        await self.device_info_discovery_update(config)
        await self._subscribe_topics()
        self.async_write_op_state()

    async def _subscribe_topics(self):
        """(Re)Subscribe to topics."""

        @callback
        def message_received(msg):
            """Handle new MQTT messages."""
            self._last_image = msg.payload

        self._sub_state = await subscription.async_subscribe_topics(
            self.opp,
            self._sub_state,
            {
                "state_topic": {
                    "topic": self._config[CONF_TOPIC],
                    "msg_callback": message_received,
                    "qos": self._qos,
                    "encoding": None,
                }
            },
        )

    async def async_will_remove_from_opp(self):
        """Unsubscribe when removed."""
        self._sub_state = await subscription.async_unsubscribe_topics(
            self.opp, self._sub_state
        )

    async def async_camera_image(self):
        """Return image response."""
        return self._last_image

    @property
    def name(self):
        """Return the name of this camera."""
        return self._config[CONF_NAME]

    @property
    def unique_id(self):
        """Return a unique ID."""
        return self._unique_id
