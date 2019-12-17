"""Integration providing core pieces of infrastructure."""
import asyncio
import itertools as it
import logging
from typing import Awaitable

import voluptuous as vol

import openpeerpower.core as ha
import openpeerpower.config as conf_util
from openpeerpower.exceptions import OpenPeerPowerError
from openpeerpower.helpers.service import async_extract_entity_ids
from openpeerpower.helpers import intent
from openpeerpower.const import (
    ATTR_ENTITY_ID, SERVICE_TURN_ON, SERVICE_TURN_OFF, SERVICE_TOGGLE,
    SERVICE_OPENPEERPOWER_STOP, SERVICE_OPENPEERPOWER_RESTART,
    RESTART_EXIT_CODE)
from openpeerpower.helpers import config_validation as cv

_LOGGER = logging.getLogger(__name__)
DOMAIN = ha.DOMAIN
SERVICE_RELOAD_CORE_CONFIG = 'reload_core_config'
SERVICE_CHECK_CONFIG = 'check_config'
SERVICE_UPDATE_ENTITY = 'update_entity'
SCHEMA_UPDATE_ENTITY = vol.Schema({
    ATTR_ENTITY_ID: cv.entity_ids
})


async def async_setup(opp: ha.OpenPeerPower, config: dict) -> Awaitable[bool]:
    """Set up general services related to Open Power Power."""
    async def async_handle_turn_service(service):
        """Handle calls to openpeerpower.turn_on/off."""
        entity_ids = await async_extract_entity_ids(opp, service)

        # Generic turn on/off method requires entity id
        if not entity_ids:
            _LOGGER.error(
                "openpeerpower/%s cannot be called without entity_id",
                service.service)
            return

        # Group entity_ids by domain. groupby requires sorted data.
        by_domain = it.groupby(sorted(entity_ids),
                               lambda item: ha.split_entity_id(item)[0])

        tasks = []

        for domain, ent_ids in by_domain:
            # We want to block for all calls and only return when all calls
            # have been processed. If a service does not exist it causes a 10
            # second delay while we're blocking waiting for a response.
            # But services can be registered on other HA instances that are
            # listening to the bus too. So as an in between solution, we'll
            # block only if the service is defined in the current HA instance.
            blocking = opp.services.has_service(domain, service.service)

            # Create a new dict for this call
            data = dict(service.data)

            # ent_ids is a generator, convert it to a list.
            data[ATTR_ENTITY_ID] = list(ent_ids)

            tasks.append(opp.services.async_call(
                domain, service.service, data, blocking))

        await asyncio.wait(tasks, loop=opp.loop)

    opp.services.async_register(
        ha.DOMAIN, SERVICE_TURN_OFF, async_handle_turn_service)
    opp.services.async_register(
        ha.DOMAIN, SERVICE_TURN_ON, async_handle_turn_service)
    opp.services.async_register(
        ha.DOMAIN, SERVICE_TOGGLE, async_handle_turn_service)
    opp.helpers.intent.async_register(intent.ServiceIntentHandler(
        intent.INTENT_TURN_ON, ha.DOMAIN, SERVICE_TURN_ON, "Turned {} on"))
    opp.helpers.intent.async_register(intent.ServiceIntentHandler(
        intent.INTENT_TURN_OFF, ha.DOMAIN, SERVICE_TURN_OFF,
        "Turned {} off"))
    opp.helpers.intent.async_register(intent.ServiceIntentHandler(
        intent.INTENT_TOGGLE, ha.DOMAIN, SERVICE_TOGGLE, "Toggled {}"))

    async def async_handle_core_service(call):
        """Service handler for handling core services."""
        if call.service == SERVICE_OPENPEERPOWER_STOP:
            opp.async_create_task(opp.async_stop())
            return

        try:
            errors = await conf_util.async_check_op_config_file(opp)
        except OpenPeerPowerError:
            return

        if errors:
            _LOGGER.error(errors)
            opp.components.persistent_notification.async_create(
                "Config error. See dev-info panel for details.",
                "Config validating", "{0}.check_config".format(ha.DOMAIN))
            return

        if call.service == SERVICE_OPENPEERPOWER_RESTART:
            opp.async_create_task(opp.async_stop(RESTART_EXIT_CODE))

    async def async_handle_update_service(call):
        """Service handler for updating an entity."""
        tasks = [opp.helpers.entity_component.async_update_entity(entity)
                 for entity in call.data[ATTR_ENTITY_ID]]

        if tasks:
            await asyncio.wait(tasks)

    opp.services.async_register(
        ha.DOMAIN, SERVICE_OPENPEERPOWER_STOP, async_handle_core_service)
    opp.services.async_register(
        ha.DOMAIN, SERVICE_OPENPEERPOWER_RESTART, async_handle_core_service)
    opp.services.async_register(
        ha.DOMAIN, SERVICE_CHECK_CONFIG, async_handle_core_service)
    opp.services.async_register(
        ha.DOMAIN, SERVICE_UPDATE_ENTITY, async_handle_update_service,
        schema=SCHEMA_UPDATE_ENTITY)

    async def async_handle_reload_config(call):
        """Service handler for reloading core config."""
        try:
            conf = await conf_util.async_opp_config_yaml(opp)
        except OpenPeerPowerError as err:
            _LOGGER.error(err)
            return

        # auth only processed during startup
        await conf_util.async_process_op_core_config(
            opp, conf.get(ha.DOMAIN) or {})

    opp.services.async_register(
        ha.DOMAIN, SERVICE_RELOAD_CORE_CONFIG, async_handle_reload_config)

    return True
