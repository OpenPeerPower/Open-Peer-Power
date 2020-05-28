"""Allow users to set and activate scenes."""
import importlib
import logging

import voluptuous as vol

from openpeerpower.const import CONF_PLATFORM, SERVICE_TURN_ON
from openpeerpower.core import DOMAIN as HA_DOMAIN
from openpeerpower.helpers.entity import Entity
from openpeerpower.helpers.entity_component import EntityComponent

# mypy: allow-untyped-defs, no-check-untyped-defs

DOMAIN = "scene"
STATE = "scening"
STATES = "states"


def _opp_domain_validator(config):
    """Validate platform in config for openpeerpower domain."""
    if CONF_PLATFORM not in config:
        config = {CONF_PLATFORM: HA_DOMAIN, STATES: config}

    return config


def _platform_validator(config):
    """Validate it is a valid  platform."""
    try:
        platform = importlib.import_module(
            ".{}".format(config[CONF_PLATFORM]), __name__
        )
    except ImportError:
        try:
            platform = importlib.import_module(
                "openpeerpower.components.{}.scene".format(config[CONF_PLATFORM])
            )
        except ImportError:
            raise vol.Invalid("Invalid platform specified") from None

    if not hasattr(platform, "PLATFORM_SCHEMA"):
        return config

    return platform.PLATFORM_SCHEMA(config)


PLATFORM_SCHEMA = vol.Schema(
    vol.All(
        _opp_domain_validator,
        vol.Schema({vol.Required(CONF_PLATFORM): str}, extra=vol.ALLOW_EXTRA),
        _platform_validator,
    ),
    extra=vol.ALLOW_EXTRA,
)


async def async_setup(opp, config):
    """Set up the scenes."""
    logger = logging.getLogger(__name__)
    component = opp.data[DOMAIN] = EntityComponent(logger, DOMAIN, opp)

    await component.async_setup(config)
    # Ensure Open Peer Power platform always loaded.
    await component.async_setup_platform(HA_DOMAIN, {"platform": HA_DOMAIN, STATES: []})
    component.async_register_entity_service(SERVICE_TURN_ON, {}, "async_activate")

    return True


async def async_setup_entry(opp, entry):
    """Set up a config entry."""
    return await opp.data[DOMAIN].async_setup_entry(entry)


async def async_unload_entry(opp, entry):
    """Unload a config entry."""
    return await opp.data[DOMAIN].async_unload_entry(entry)


class Scene(Entity):
    """A scene is a group of entities and the states we want them to be."""

    @property
    def should_poll(self):
        """No polling needed."""
        return False

    @property
    def state(self):
        """Return the state of the scene."""
        return STATE

    def activate(self):
        """Activate scene. Try to get entities into requested state."""
        raise NotImplementedError()

    async def async_activate(self):
        """Activate scene. Try to get entities into requested state."""
        await self.opp.async_add_job(self.activate)
