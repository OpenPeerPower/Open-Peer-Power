"""Provides functionality to notify people."""
import asyncio
from functools import partial
import logging
from typing import Optional

import voluptuous as vol

from openpeerpower.const import CONF_NAME, CONF_PLATFORM
from openpeerpower.exceptions import OpenPeerPowerError
from openpeerpower.helpers import config_per_platform, discovery
import openpeerpower.helpers.config_validation as cv
from openpeerpower.helpers.typing import OpenPeerPowerType
from openpeerpower.setup import async_prepare_setup_platform
from openpeerpower.util import slugify

# mypy: allow-untyped-defs, no-check-untyped-defs

_LOGGER = logging.getLogger(__name__)

# Platform specific data
ATTR_DATA = "data"

# Text to notify user of
ATTR_MESSAGE = "message"

# Target of the notification (user, device, etc)
ATTR_TARGET = "target"

# Title of notification
ATTR_TITLE = "title"
ATTR_TITLE_DEFAULT = "Open Peer Power"

DOMAIN = "notify"

SERVICE_NOTIFY = "notify"

PLATFORM_SCHEMA = vol.Schema(
    {vol.Required(CONF_PLATFORM): cv.string, vol.Optional(CONF_NAME): cv.string},
    extra=vol.ALLOW_EXTRA,
)

NOTIFY_SERVICE_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_MESSAGE): cv.template,
        vol.Optional(ATTR_TITLE): cv.template,
        vol.Optional(ATTR_TARGET): vol.All(cv.ensure_list, [cv.string]),
        vol.Optional(ATTR_DATA): dict,
    }
)


async def async_setup(opp, config):
    """Set up the notify services."""
    targets = {}

    async def async_setup_platform(p_type, p_config=None, discovery_info=None):
        """Set up a notify platform."""
        if p_config is None:
            p_config = {}

        platform = await async_prepare_setup_platform(opp, config, DOMAIN, p_type)

        if platform is None:
            _LOGGER.error("Unknown notification service specified")
            return

        _LOGGER.info("Setting up %s.%s", DOMAIN, p_type)
        notify_service = None
        try:
            if hasattr(platform, "async_get_service"):
                notify_service = await platform.async_get_service(
                    opp, p_config, discovery_info
                )
            elif hasattr(platform, "get_service"):
                notify_service = await opp.async_add_job(
                    platform.get_service, opp, p_config, discovery_info
                )
            else:
                raise OpenPeerPowerError("Invalid notify platform.")

            if notify_service is None:
                # Platforms can decide not to create a service based
                # on discovery data.
                if discovery_info is None:
                    _LOGGER.error(
                        "Failed to initialize notification service %s", p_type
                    )
                return

        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception("Error setting up platform %s", p_type)
            return

        notify_service.opp = opp

        if discovery_info is None:
            discovery_info = {}

        async def async_notify_message(service):
            """Handle sending notification message service calls."""
            kwargs = {}
            message = service.data[ATTR_MESSAGE]
            title = service.data.get(ATTR_TITLE)

            if title:
                title.opp = opp
                kwargs[ATTR_TITLE] = title.async_render()

            if targets.get(service.service) is not None:
                kwargs[ATTR_TARGET] = [targets[service.service]]
            elif service.data.get(ATTR_TARGET) is not None:
                kwargs[ATTR_TARGET] = service.data.get(ATTR_TARGET)

            message.opp = opp
            kwargs[ATTR_MESSAGE] = message.async_render()
            kwargs[ATTR_DATA] = service.data.get(ATTR_DATA)

            await notify_service.async_send_message(**kwargs)

        if hasattr(notify_service, "targets"):
            platform_name = (
                p_config.get(CONF_NAME) or discovery_info.get(CONF_NAME) or p_type
            )
            for name, target in notify_service.targets.items():
                target_name = slugify(f"{platform_name}_{name}")
                targets[target_name] = target
                opp.services.async_register(
                    DOMAIN,
                    target_name,
                    async_notify_message,
                    schema=NOTIFY_SERVICE_SCHEMA,
                )

        platform_name = (
            p_config.get(CONF_NAME) or discovery_info.get(CONF_NAME) or SERVICE_NOTIFY
        )
        platform_name_slug = slugify(platform_name)

        opp.services.async_register(
            DOMAIN,
            platform_name_slug,
            async_notify_message,
            schema=NOTIFY_SERVICE_SCHEMA,
        )

        opp.config.components.add(f"{DOMAIN}.{p_type}")

        return True

    setup_tasks = [
        async_setup_platform(p_type, p_config)
        for p_type, p_config in config_per_platform(config, DOMAIN)
    ]

    if setup_tasks:
        await asyncio.wait(setup_tasks)

    async def async_platform_discovered(platform, info):
        """Handle for discovered platform."""
        await async_setup_platform(platform, discovery_info=info)

    discovery.async_listen_platform(opp, DOMAIN, async_platform_discovered)

    return True


class BaseNotificationService:
    """An abstract class for notification services."""

    opp: Optional[OpenPeerPowerType] = None

    def send_message(self, message, **kwargs):
        """Send a message.

        kwargs can contain ATTR_TITLE to specify a title.
        """
        raise NotImplementedError()

    async def async_send_message(self, message, **kwargs):
        """Send a message.

        kwargs can contain ATTR_TITLE to specify a title.
        """
        await self.opp.async_add_job(partial(self.send_message, message, **kwargs))
