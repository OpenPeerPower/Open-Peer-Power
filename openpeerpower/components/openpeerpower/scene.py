"""Allow users to set and activate scenes."""
from collections import namedtuple
import logging

import voluptuous as vol

from openpeerpower import config as conf_util
from openpeerpower.components.scene import DOMAIN as SCENE_DOMAIN, STATES, Scene
from openpeerpower.const import (
    ATTR_ENTITY_ID,
    ATTR_STATE,
    CONF_ENTITIES,
    CONF_ID,
    CONF_NAME,
    CONF_PLATFORM,
    SERVICE_RELOAD,
    STATE_OFF,
    STATE_ON,
)
from openpeerpower.core import DOMAIN as OP_DOMAIN, State
from openpeerpower.exceptions import OpenPeerPowerError
from openpeerpower.helpers import (
    config_per_platform,
    config_validation as cv,
    entity_platform,
)
from openpeerpower.helpers.state import async_reproduce_state
from openpeerpower.loader import async_get_integration


def _convert_states(states):
    """Convert state definitions to State objects."""
    result = {}

    for entity_id in states:
        entity_id = cv.entity_id(entity_id)

        if isinstance(states[entity_id], dict):
            entity_attrs = states[entity_id].copy()
            state = entity_attrs.pop(ATTR_STATE, None)
            attributes = entity_attrs
        else:
            state = states[entity_id]
            attributes = {}

        # YAML translates 'on' to a boolean
        # http://yaml.org/type/bool.html
        if isinstance(state, bool):
            state = STATE_ON if state else STATE_OFF
        elif not isinstance(state, str):
            raise vol.Invalid(f"State for {entity_id} should be a string")

        result[entity_id] = State(entity_id, state, attributes)

    return result


def _ensure_no_intersection(value):
    """Validate that entities and snapshot_entities do not overlap."""
    if (
        CONF_SNAPSHOT not in value
        or CONF_ENTITIES not in value
        or not any(
            entity_id in value[CONF_SNAPSHOT] for entity_id in value[CONF_ENTITIES]
        )
    ):
        return value

    raise vol.Invalid("entities and snapshot_entities must not overlap")


CONF_SCENE_ID = "scene_id"
CONF_SNAPSHOT = "snapshot_entities"

STATES_SCHEMA = vol.All(dict, _convert_states)

PLATFORM_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_PLATFORM): OP_DOMAIN,
        vol.Required(STATES): vol.All(
            cv.ensure_list,
            [
                {
                    vol.Required(CONF_NAME): cv.string,
                    vol.Required(CONF_ENTITIES): STATES_SCHEMA,
                }
            ],
        ),
    },
    extra=vol.ALLOW_EXTRA,
)

CREATE_SCENE_SCHEMA = vol.All(
    cv.has_at_least_one_key(CONF_ENTITIES, CONF_SNAPSHOT),
    _ensure_no_intersection,
    vol.Schema(
        {
            vol.Required(CONF_SCENE_ID): cv.slug,
            vol.Optional(CONF_ENTITIES, default={}): STATES_SCHEMA,
            vol.Optional(CONF_SNAPSHOT, default=[]): cv.entity_ids,
        }
    ),
)

SERVICE_APPLY = "apply"
SERVICE_CREATE = "create"
SCENECONFIG = namedtuple("SceneConfig", [CONF_NAME, STATES])
_LOGGER = logging.getLogger(__name__)


async def async_setup_platform(opp, config, async_add_entities, discovery_info=None):
    """Set up Open Peer Power scene entries."""
    _process_scenes_config(opp, async_add_entities, config)

    # This platform can be loaded multiple times. Only first time register the service.
    if opp.services.has_service(SCENE_DOMAIN, SERVICE_RELOAD):
        return

    # Store platform for later.
    platform = entity_platform.current_platform.get()

    async def reload_config(call):
        """Reload the scene config."""
        try:
            conf = await conf_util.async_opp_config_yaml(opp)
        except OpenPeerPowerError as err:
            _LOGGER.error(err)
            return

        integration = await async_get_integration(opp, SCENE_DOMAIN)

        conf = await conf_util.async_process_component_config(opp, conf, integration)

        if not conf or not platform:
            return

        await platform.async_reset()

        # Extract only the config for the Open Peer Power platform, ignore the rest.
        for p_type, p_config in config_per_platform(conf, SCENE_DOMAIN):
            if p_type != OP_DOMAIN:
                continue

            _process_scenes_config(opp, async_add_entities, p_config)

    opp.helpers.service.async_register_admin_service(
        SCENE_DOMAIN, SERVICE_RELOAD, reload_config
    )

    async def apply_service(call):
        """Apply a scene."""
        await async_reproduce_state(
            opp, call.data[CONF_ENTITIES].values(), blocking=True, context=call.context
        )

    opp.services.async_register(
        SCENE_DOMAIN,
        SERVICE_APPLY,
        apply_service,
        vol.Schema({vol.Required(CONF_ENTITIES): STATES_SCHEMA}),
    )

    async def create_service(call):
        """Create a scene."""
        snapshot = call.data[CONF_SNAPSHOT]
        entities = call.data[CONF_ENTITIES]

        for entity_id in snapshot:
            state = opp.states.get(entity_id)
            if state is None:
                _LOGGER.warning(
                    "Entity %s does not exist and therefore cannot be snapshotted",
                    entity_id,
                )
                continue
            entities[entity_id] = State(entity_id, state.state, state.attributes)

        if not entities:
            _LOGGER.warning("Empty scenes are not allowed")
            return

        scene_config = SCENECONFIG(call.data[CONF_SCENE_ID], entities)
        entity_id = f"{SCENE_DOMAIN}.{scene_config.name}"
        old = platform.entities.get(entity_id)
        if old is not None:
            if not old.from_service:
                _LOGGER.warning("The scene %s already exists", entity_id)
                return
            await platform.async_remove_entity(entity_id)
        async_add_entities([OpenPeerPowerScene(opp, scene_config, from_service=True)])

    opp.services.async_register(
        SCENE_DOMAIN, SERVICE_CREATE, create_service, CREATE_SCENE_SCHEMA
    )


def _process_scenes_config(opp, async_add_entities, config):
    """Process multiple scenes and add them."""
    scene_config = config[STATES]

    # Check empty list
    if not scene_config:
        return

    async_add_entities(
        OpenPeerPowerScene(
            opp,
            SCENECONFIG(scene[CONF_NAME], scene[CONF_ENTITIES]),
            scene.get(CONF_ID),
        )
        for scene in scene_config
    )


class OpenPeerPowerScene(Scene):
    """A scene is a group of entities and the states we want them to be."""

    def __init__(self, opp, scene_config, scene_id=None, from_service=False):
        """Initialize the scene."""
        self._id = scene_id
        self.opp = opp
        self.scene_config = scene_config
        self.from_service = from_service

    @property
    def name(self):
        """Return the name of the scene."""
        return self.scene_config.name

    @property
    def device_state_attributes(self):
        """Return the scene state attributes."""
        attributes = {ATTR_ENTITY_ID: list(self.scene_config.states)}
        if self._id is not None:
            attributes[CONF_ID] = self._id
        return attributes

    async def async_activate(self):
        """Activate scene. Try to get entities into requested state."""
        await async_reproduce_state(
            self.opp,
            self.scene_config.states.values(),
            blocking=True,
            context=self._context,
        )
