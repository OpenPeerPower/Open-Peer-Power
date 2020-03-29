"""Service calling related helpers."""
import asyncio
from functools import partial, wraps
import logging
from typing import Callable

import voluptuous as vol

from openpeerpower.auth.permissions.const import CAT_ENTITIES, POLICY_CONTROL
from openpeerpower.const import (
    ATTR_AREA_ID,
    ATTR_ENTITY_ID,
    ENTITY_MATCH_ALL,
    ENTITY_MATCH_NONE,
)
import openpeerpower.core as op
from openpeerpower.exceptions import (
    OpenPeerPowerError,
    TemplateError,
    Unauthorized,
    UnknownUser,
)
from openpeerpower.helpers import template, typing
import openpeerpower.helpers.config_validation as cv
from openpeerpower.helpers.typing import OpenPeerPowerType
from openpeerpower.loader import async_get_integration, bind_opp
from openpeerpower.util.yaml import load_yaml
from openpeerpower.util.yaml.loader import JSON_TYPE

# mypy: allow-untyped-defs, no-check-untyped-defs

CONF_SERVICE = "service"
CONF_SERVICE_TEMPLATE = "service_template"
CONF_SERVICE_ENTITY_ID = "entity_id"
CONF_SERVICE_DATA = "data"
CONF_SERVICE_DATA_TEMPLATE = "data_template"

_LOGGER = logging.getLogger(__name__)

SERVICE_DESCRIPTION_CACHE = "service_description_cache"


@bind_opp
def call_from_config(
    opp, config, blocking=False, variables=None, validate_config=True
):
    """Call a service based on a config hash."""
    asyncio.run_coroutine_threadsafe(
        async_call_from_config(opp, config, blocking, variables, validate_config),
        opp.loop,
    ).result()


@bind_opp
async def async_call_from_config(
    opp, config, blocking=False, variables=None, validate_config=True, context=None
):
    """Call a service based on a config hash."""
    if validate_config:
        try:
            config = cv.SERVICE_SCHEMA(config)
        except vol.Invalid as ex:
            _LOGGER.error("Invalid config for calling service: %s", ex)
            return

    if CONF_SERVICE in config:
        domain_service = config[CONF_SERVICE]
    else:
        try:
            config[CONF_SERVICE_TEMPLATE].opp = opp
            domain_service = config[CONF_SERVICE_TEMPLATE].async_render(variables)
            domain_service = cv.service(domain_service)
        except TemplateError as ex:
            if blocking:
                raise
            _LOGGER.error("Error rendering service name template: %s", ex)
            return
        except vol.Invalid:
            if blocking:
                raise
            _LOGGER.error("Template rendered invalid service: %s", domain_service)
            return

    domain, service_name = domain_service.split(".", 1)
    service_data = dict(config.get(CONF_SERVICE_DATA, {}))

    if CONF_SERVICE_DATA_TEMPLATE in config:
        try:
            template.attach(opp, config[CONF_SERVICE_DATA_TEMPLATE])
            service_data.update(
                template.render_complex(config[CONF_SERVICE_DATA_TEMPLATE], variables)
            )
        except TemplateError as ex:
            _LOGGER.error("Error rendering data template: %s", ex)
            return

    if CONF_SERVICE_ENTITY_ID in config:
        service_data[ATTR_ENTITY_ID] = config[CONF_SERVICE_ENTITY_ID]

    await opp.services.async_call(
        domain, service_name, service_data, blocking=blocking, context=context
    )


@bind_opp
def extract_entity_ids(opp, service_call, expand_group=True):
    """Extract a list of entity ids from a service call.

    Will convert group entity ids to the entity ids it represents.
    """
    return asyncio.run_coroutine_threadsafe(
        async_extract_entity_ids(opp, service_call, expand_group), opp.loop
    ).result()


@bind_opp
async def async_extract_entities(opp, entities, service_call, expand_group=True):
    """Extract a list of entity objects from a service call.

    Will convert group entity ids to the entity ids it represents.
    """
    data_ent_id = service_call.data.get(ATTR_ENTITY_ID)

    if data_ent_id == ENTITY_MATCH_ALL:
        return [entity for entity in entities if entity.available]

    entity_ids = await async_extract_entity_ids(opp, service_call, expand_group)

    found = []

    for entity in entities:
        if entity.entity_id not in entity_ids:
            continue

        entity_ids.remove(entity.entity_id)

        if not entity.available:
            continue

        found.append(entity)

    if entity_ids:
        _LOGGER.warning(
            "Unable to find referenced entities %s", ", ".join(sorted(entity_ids))
        )

    return found


@bind_opp
async def async_extract_entity_ids(opp, service_call, expand_group=True):
    """Extract a list of entity ids from a service call.

    Will convert group entity ids to the entity ids it represents.
    """
    entity_ids = service_call.data.get(ATTR_ENTITY_ID)
    area_ids = service_call.data.get(ATTR_AREA_ID)

    extracted = set()

    if entity_ids in (None, ENTITY_MATCH_NONE) and area_ids in (
        None,
        ENTITY_MATCH_NONE,
    ):
        return extracted

    if entity_ids and entity_ids != ENTITY_MATCH_NONE:
        # Entity ID attr can be a list or a string
        if isinstance(entity_ids, str):
            entity_ids = [entity_ids]

        if expand_group:
            entity_ids = opp.components.group.expand_entity_ids(entity_ids)

        extracted.update(entity_ids)

    if area_ids and area_ids != ENTITY_MATCH_NONE:
        if isinstance(area_ids, str):
            area_ids = [area_ids]

        dev_reg, ent_reg = await asyncio.gather(
            opp.helpers.device_registry.async_get_registry(),
            opp.helpers.entity_registry.async_get_registry(),
        )
        devices = [
            device
            for area_id in area_ids
            for device in opp.helpers.device_registry.async_entries_for_area(
                dev_reg, area_id
            )
        ]
        extracted.update(
            entry.entity_id
            for device in devices
            for entry in opp.helpers.entity_registry.async_entries_for_device(
                ent_reg, device.id
            )
        )

    return extracted


async def _load_services_file(opp: OpenPeerPowerType, domain: str) -> JSON_TYPE:
    """Load services file for an integration."""
    integration = await async_get_integration(opp, domain)
    try:
        return await opp.async_add_executor_job(
            load_yaml, str(integration.file_path / "services.yaml")
        )
    except FileNotFoundError:
        _LOGGER.warning("Unable to find services.yaml for the %s integration", domain)
        return {}
    except OpenPeerPowerError:
        _LOGGER.warning("Unable to parse services.yaml for the %s integration", domain)
        return {}


@bind_opp
async def async_get_all_descriptions(opp):
    """Return descriptions (i.e. user documentation) for all service calls."""
    descriptions_cache = opp.data.setdefault(SERVICE_DESCRIPTION_CACHE, {})
    format_cache_key = "{}.{}".format
    services = opp.services.async_services()

    # See if there are new services not seen before.
    # Any service that we saw before already has an entry in description_cache.
    missing = set()
    for domain in services:
        for service in services[domain]:
            if format_cache_key(domain, service) not in descriptions_cache:
                missing.add(domain)
                break

    # Files we loaded for missing descriptions
    loaded = {}

    if missing:
        contents = await asyncio.gather(
            *(_load_services_file(opp, domain) for domain in missing)
        )

        for domain, content in zip(missing, contents):
            loaded[domain] = content

    # Build response
    descriptions = {}
    for domain in services:
        descriptions[domain] = {}

        for service in services[domain]:
            cache_key = format_cache_key(domain, service)
            description = descriptions_cache.get(cache_key)

            # Cache missing descriptions
            if description is None:
                domain_yaml = loaded[domain]
                yaml_description = domain_yaml.get(service, {})

                # Don't warn for missing services, because it triggers false
                # positives for things like scripts, that register as a service

                description = descriptions_cache[cache_key] = {
                    "description": yaml_description.get("description", ""),
                    "fields": yaml_description.get("fields", {}),
                }

            descriptions[domain][service] = description

    return descriptions


@op.callback
@bind_opp
def async_set_service_schema(opp, domain, service, schema):
    """Register a description for a service."""
    opp.data.setdefault(SERVICE_DESCRIPTION_CACHE, {})

    description = {
        "description": schema.get("description") or "",
        "fields": schema.get("fields") or {},
    }

    opp.data[SERVICE_DESCRIPTION_CACHE][f"{domain}.{service}"] = description


@bind_opp
async def entity_service_call(opp, platforms, func, call, required_features=None):
    """Handle an entity service call.

    Calls all platforms simultaneously.
    """
    if call.context.user_id:
        user = await opp.auth.async_get_user(call.context.user_id)
        if user is None:
            raise UnknownUser(context=call.context)
        entity_perms = user.permissions.check_entity
    else:
        entity_perms = None

    target_all_entities = call.data.get(ATTR_ENTITY_ID) == ENTITY_MATCH_ALL

    if not target_all_entities:
        # A set of entities we're trying to target.
        entity_ids = await async_extract_entity_ids(opp, call, True)

    # If the service function is a string, we'll pass it the service call data
    if isinstance(func, str):
        data = {
            key: val
            for key, val in call.data.items()
            if key not in cv.ENTITY_SERVICE_FIELDS
        }
    # If the service function is not a string, we pass the service call
    else:
        data = call

    # Check the permissions

    # A list with entities to call the service on.
    entity_candidates = []

    if entity_perms is None:
        for platform in platforms:
            if target_all_entities:
                entity_candidates.extend(platform.entities.values())
            else:
                entity_candidates.extend(
                    [
                        entity
                        for entity in platform.entities.values()
                        if entity.entity_id in entity_ids
                    ]
                )

    elif target_all_entities:
        # If we target all entities, we will select all entities the user
        # is allowed to control.
        for platform in platforms:
            entity_candidates.extend(
                [
                    entity
                    for entity in platform.entities.values()
                    if entity_perms(entity.entity_id, POLICY_CONTROL)
                ]
            )

    else:
        for platform in platforms:
            platform_entities = []
            for entity in platform.entities.values():

                if entity.entity_id not in entity_ids:
                    continue

                if not entity_perms(entity.entity_id, POLICY_CONTROL):
                    raise Unauthorized(
                        context=call.context,
                        entity_id=entity.entity_id,
                        permission=POLICY_CONTROL,
                    )

                platform_entities.append(entity)

            entity_candidates.extend(platform_entities)

    if not target_all_entities:
        for entity in entity_candidates:
            entity_ids.remove(entity.entity_id)

        if entity_ids:
            _LOGGER.warning(
                "Unable to find referenced entities %s", ", ".join(sorted(entity_ids))
            )

    entities = []

    for entity in entity_candidates:
        if not entity.available:
            continue

        # Skip entities that don't have the required feature.
        if required_features is not None and not any(
            entity.supported_features & feature_set for feature_set in required_features
        ):
            continue

        entities.append(entity)

    if not entities:
        return

    done, pending = await asyncio.wait(
        [
            entity.async_request_call(
                _handle_entity_call(opp, entity, func, data, call.context)
            )
            for entity in entities
        ]
    )
    assert not pending
    for future in done:
        future.result()  # pop exception if have

    tasks = []

    for entity in entities:
        if not entity.should_poll:
            continue

        # Context expires if the turn on commands took a long time.
        # Set context again so it's there when we update
        entity.async_set_context(call.context)
        tasks.append(entity.async_update_op_state(True))

    if tasks:
        done, pending = await asyncio.wait(tasks)
        assert not pending
        for future in done:
            future.result()  # pop exception if have


async def _handle_entity_call(opp, entity, func, data, context):
    """Handle calling service method."""
    entity.async_set_context(context)

    if isinstance(func, str):
        result = opp.async_add_job(partial(getattr(entity, func), **data))
    else:
        result = opp.async_add_job(func, entity, data)

    # Guard because callback functions do not return a task when passed to async_add_job.
    if result is not None:
        await result

    if asyncio.iscoroutine(result):
        _LOGGER.error(
            "Service %s for %s incorrectly returns a coroutine object. Await result instead in service handler. Report bug to integration author.",
            func,
            entity.entity_id,
        )
        await result


@bind_opp
@op.callback
def async_register_admin_service(
    opp: typing.OpenPeerPowerType,
    domain: str,
    service: str,
    service_func: Callable,
    schema: vol.Schema = vol.Schema({}, extra=vol.PREVENT_EXTRA),
) -> None:
    """Register a service that requires admin access."""

    @wraps(service_func)
    async def admin_handler(call):
        if call.context.user_id:
            user = await opp.auth.async_get_user(call.context.user_id)
            if user is None:
                raise UnknownUser(context=call.context)
            if not user.is_admin:
                raise Unauthorized(context=call.context)

        result = opp.async_add_job(service_func, call)
        if result is not None:
            await result

    opp.services.async_register(domain, service, admin_handler, schema)


@bind_opp
@op.callback
def verify_domain_control(opp: OpenPeerPowerType, domain: str) -> Callable:
    """Ensure permission to access any entity under domain in service call."""

    def decorator(service_handler: Callable) -> Callable:
        """Decorate."""
        if not asyncio.iscoroutinefunction(service_handler):
            raise OpenPeerPowerError("Can only decorate async functions.")

        async def check_permissions(call):
            """Check user permission and raise before call if unauthorized."""
            if not call.context.user_id:
                return await service_handler(call)

            user = await opp.auth.async_get_user(call.context.user_id)

            if user is None:
                raise UnknownUser(
                    context=call.context,
                    permission=POLICY_CONTROL,
                    user_id=call.context.user_id,
                )

            reg = await opp.helpers.entity_registry.async_get_registry()

            for entity in reg.entities.values():
                if entity.platform != domain:
                    continue

                if user.permissions.check_entity(entity.entity_id, POLICY_CONTROL):
                    return await service_handler(call)

            raise Unauthorized(
                context=call.context,
                permission=POLICY_CONTROL,
                user_id=call.context.user_id,
                perm_category=CAT_ENTITIES,
            )

        return check_permissions

    return decorator
