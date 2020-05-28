"""Helpers for components that manage entities."""
import asyncio
from datetime import timedelta
from itertools import chain
import logging
from types import ModuleType
from typing import Dict, Optional, cast

from openpeerpower import config as conf_util
from openpeerpower.config_entries import ConfigEntry
from openpeerpower.const import CONF_ENTITY_NAMESPACE, CONF_SCAN_INTERVAL
from openpeerpower.core import OpenPeerPower, callback
from openpeerpower.exceptions import OpenPeerPowerError
from openpeerpower.helpers import (
    config_per_platform,
    config_validation as cv,
    discovery,
    entity,
    service,
)
from openpeerpower.loader import async_get_integration, bind_opp
from openpeerpower.setup import async_prepare_setup_platform

from .entity_platform import EntityPlatform

# mypy: allow-untyped-defs, no-check-untyped-defs

DEFAULT_SCAN_INTERVAL = timedelta(seconds=15)
DATA_INSTANCES = "entity_components"


@bind_opp
async def async_update_entity(opp: OpenPeerPower, entity_id: str) -> None:
    """Trigger an update for an entity."""
    domain = entity_id.split(".", 1)[0]
    entity_comp = opp.data.get(DATA_INSTANCES, {}).get(domain)

    if entity_comp is None:
        logging.getLogger(__name__).warning(
            "Forced update failed. Component for %s not loaded.", entity_id
        )
        return

    entity_obj = entity_comp.get_entity(entity_id)

    if entity_obj is None:
        logging.getLogger(__name__).warning(
            "Forced update failed. Entity %s not found.", entity_id
        )
        return

    await entity_obj.async_update_op_state(True)


class EntityComponent:
    """The EntityComponent manages platforms that manages entities.

    This class has the following responsibilities:
     - Process the configuration and set up a platform based component.
     - Manage the platforms and their entities.
     - Help extract the entities from a service call.
     - Listen for discovery events for platforms related to the domain.
    """

    def __init__(
        self,
        logger: logging.Logger,
        domain: str,
        opp: OpenPeerPower,
        scan_interval: timedelta = DEFAULT_SCAN_INTERVAL,
    ):
        """Initialize an entity component."""
        self.logger = logger
        self.opp = opp
        self.domain = domain
        self.scan_interval = scan_interval

        self.config = None

        self._platforms: Dict[str, EntityPlatform] = {
            domain: self._async_init_entity_platform(domain, None)
        }
        self.async_add_entities = self._platforms[domain].async_add_entities
        self.add_entities = self._platforms[domain].add_entities

        opp.data.setdefault(DATA_INSTANCES, {})[domain] = self

    @property
    def entities(self):
        """Return an iterable that returns all entities."""
        return chain.from_iterable(
            platform.entities.values() for platform in self._platforms.values()
        )

    def get_entity(self, entity_id: str) -> Optional[entity.Entity]:
        """Get an entity."""
        for platform in self._platforms.values():
            entity_obj = cast(Optional[entity.Entity], platform.entities.get(entity_id))
            if entity_obj is not None:
                return entity_obj
        return None

    def setup(self, config):
        """Set up a full entity component.

        This doesn't block the executor to protect from deadlocks.
        """
        self.opp.add_job(self.async_setup(config))

    async def async_setup(self, config):
        """Set up a full entity component.

        Loads the platforms from the config and will listen for supported
        discovered platforms.

        This method must be run in the event loop.
        """
        self.config = config

        # Look in config for Domain, Domain 2, Domain 3 etc and load them
        tasks = []
        for p_type, p_config in config_per_platform(config, self.domain):
            tasks.append(self.async_setup_platform(p_type, p_config))

        if tasks:
            await asyncio.wait(tasks)

        # Generic discovery listener for loading platform dynamically
        # Refer to: openpeerpower.components.discovery.load_platform()
        async def component_platform_discovered(platform, info):
            """Handle the loading of a platform."""
            await self.async_setup_platform(platform, {}, info)

        discovery.async_listen_platform(
            self.opp, self.domain, component_platform_discovered
        )

    async def async_setup_entry(self, config_entry):
        """Set up a config entry."""
        platform_type = config_entry.domain
        platform = await async_prepare_setup_platform(
            self.opp,
            # In future PR we should make opp_config part of the constructor
            # params.
            self.config or {},
            self.domain,
            platform_type,
        )

        if platform is None:
            return False

        key = config_entry.entry_id

        if key in self._platforms:
            raise ValueError("Config entry has already been setup!")

        self._platforms[key] = self._async_init_entity_platform(
            platform_type,
            platform,
            scan_interval=getattr(platform, "SCAN_INTERVAL", None),
        )

        return await self._platforms[key].async_setup_entry(config_entry)

    async def async_unload_entry(self, config_entry: ConfigEntry) -> bool:
        """Unload a config entry."""
        key = config_entry.entry_id

        platform = self._platforms.pop(key, None)

        if platform is None:
            raise ValueError("Config entry was never loaded!")

        await platform.async_reset()
        return True

    async def async_extract_from_service(self, service_call, expand_group=True):
        """Extract all known and available entities from a service call.

        Will return an empty list if entities specified but unknown.

        This method must be run in the event loop.
        """
        return await service.async_extract_entities(
            self.opp, self.entities, service_call, expand_group
        )

    @callback
    def async_register_entity_service(self, name, schema, func, required_features=None):
        """Register an entity service."""
        if isinstance(schema, dict):
            schema = cv.make_entity_service_schema(schema)

        async def handle_service(call):
            """Handle the service."""
            await self.opp.helpers.service.entity_service_call(
                self._platforms.values(), func, call, required_features
            )

        self.opp.services.async_register(self.domain, name, handle_service, schema)

    async def async_setup_platform(
        self, platform_type, platform_config, discovery_info=None
    ):
        """Set up a platform for this component."""
        if self.config is None:
            raise RuntimeError("async_setup needs to be called first")

        platform = await async_prepare_setup_platform(
            self.opp, self.config, self.domain, platform_type
        )

        if platform is None:
            return

        # Use config scan interval, fallback to platform if none set
        scan_interval = platform_config.get(
            CONF_SCAN_INTERVAL, getattr(platform, "SCAN_INTERVAL", None)
        )
        entity_namespace = platform_config.get(CONF_ENTITY_NAMESPACE)

        key = (platform_type, scan_interval, entity_namespace)

        if key not in self._platforms:
            self._platforms[key] = self._async_init_entity_platform(
                platform_type, platform, scan_interval, entity_namespace
            )

        await self._platforms[key].async_setup(platform_config, discovery_info)

    async def _async_reset(self) -> None:
        """Remove entities and reset the entity component to initial values.

        This method must be run in the event loop.
        """
        tasks = [platform.async_reset() for platform in self._platforms.values()]

        if tasks:
            await asyncio.wait(tasks)

        self._platforms = {self.domain: self._platforms[self.domain]}
        self.config = None

    async def async_remove_entity(self, entity_id: str) -> None:
        """Remove an entity managed by one of the platforms."""
        for platform in self._platforms.values():
            if entity_id in platform.entities:
                await platform.async_remove_entity(entity_id)

    async def async_prepare_reload(self, *, skip_reset: bool = False) -> Optional[dict]:
        """Prepare reloading this entity component.

        This method must be run in the event loop.
        """
        try:
            conf = await conf_util.async_opp_config_yaml(self.opp)
        except OpenPeerPowerError as err:
            self.logger.error(err)
            return None

        integration = await async_get_integration(self.opp, self.domain)

        processed_conf = await conf_util.async_process_component_config(
            self.opp, conf, integration
        )

        if processed_conf is None:
            return None

        if not skip_reset:
            await self._async_reset()

        return processed_conf

    @callback
    def _async_init_entity_platform(
        self,
        platform_type: str,
        platform: Optional[ModuleType],
        scan_interval: Optional[timedelta] = None,
        entity_namespace: Optional[str] = None,
    ) -> EntityPlatform:
        """Initialize an entity platform."""
        if scan_interval is None:
            scan_interval = self.scan_interval

        return EntityPlatform(  # type: ignore
            opp=self.opp,
            logger=self.logger,
            domain=self.domain,
            platform_name=platform_type,
            platform=platform,
            scan_interval=scan_interval,
            entity_namespace=entity_namespace,
        )
