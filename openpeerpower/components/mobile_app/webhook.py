"""Webhook handlers for mobile_app."""
import logging

from aiohttp.web import HTTPBadRequest, Request, Response
import voluptuous as vol

from openpeerpower.components.frontend import MANIFEST_JSON
from openpeerpower.components.zone.const import DOMAIN as ZONE_DOMAIN
from openpeerpower.const import (
    ATTR_DOMAIN,
    ATTR_SERVICE,
    ATTR_SERVICE_DATA,
    CONF_WEBHOOK_ID,
    HTTP_BAD_REQUEST,
    HTTP_CREATED,
)
from openpeerpower.core import EventOrigin
from openpeerpower.exceptions import OpenPeerPowerError, ServiceNotFound, TemplateError
from openpeerpower.helpers import device_registry as dr
from openpeerpower.helpers.dispatcher import async_dispatcher_send
from openpeerpower.helpers.template import attach
from openpeerpower.helpers.typing import OpenPeerPowerType

from .const import (
    ATTR_DEVICE_ID,
    ATTR_DEVICE_NAME,
    ATTR_EVENT_DATA,
    ATTR_EVENT_TYPE,
    ATTR_MANUFACTURER,
    ATTR_MODEL,
    ATTR_OS_VERSION,
    ATTR_SENSOR_TYPE,
    ATTR_SENSOR_UNIQUE_ID,
    ATTR_SUPPORTS_ENCRYPTION,
    ATTR_TEMPLATE,
    ATTR_TEMPLATE_VARIABLES,
    ATTR_WEBHOOK_DATA,
    ATTR_WEBHOOK_ENCRYPTED,
    ATTR_WEBHOOK_ENCRYPTED_DATA,
    ATTR_WEBHOOK_TYPE,
    CONF_CLOUDHOOK_URL,
    CONF_REMOTE_UI_URL,
    CONF_SECRET,
    DATA_CONFIG_ENTRIES,
    DATA_DELETED_IDS,
    DATA_STORE,
    DOMAIN,
    ERR_ENCRYPTION_REQUIRED,
    ERR_SENSOR_DUPLICATE_UNIQUE_ID,
    ERR_SENSOR_NOT_REGISTERED,
    SIGNAL_LOCATION_UPDATE,
    SIGNAL_SENSOR_UPDATE,
    WEBHOOK_PAYLOAD_SCHEMA,
    WEBHOOK_SCHEMAS,
    WEBHOOK_TYPE_CALL_SERVICE,
    WEBHOOK_TYPE_FIRE_EVENT,
    WEBHOOK_TYPE_GET_CONFIG,
    WEBHOOK_TYPE_GET_ZONES,
    WEBHOOK_TYPE_REGISTER_SENSOR,
    WEBHOOK_TYPE_RENDER_TEMPLATE,
    WEBHOOK_TYPE_UPDATE_LOCATION,
    WEBHOOK_TYPE_UPDATE_REGISTRATION,
    WEBHOOK_TYPE_UPDATE_SENSOR_STATES,
    WEBHOOK_TYPES,
)
from .helpers import (
    _decrypt_payload,
    empty_okay_response,
    error_response,
    registration_context,
    safe_registration,
    savable_state,
    webhook_response,
)

_LOGGER = logging.getLogger(__name__)


async def handle_webhook(
    opp: OpenPeerPowerType, webhook_id: str, request: Request
) -> Response:
    """Handle webhook callback."""
    if webhook_id in opp.data[DOMAIN][DATA_DELETED_IDS]:
        return Response(status=410)

    headers = {}

    config_entry = opp.data[DOMAIN][DATA_CONFIG_ENTRIES][webhook_id]

    registration = config_entry.data

    try:
        req_data = await request.json()
    except ValueError:
        _LOGGER.warning("Received invalid JSON from mobile_app")
        return empty_okay_response(status=HTTP_BAD_REQUEST)

    if (
        ATTR_WEBHOOK_ENCRYPTED not in req_data
        and registration[ATTR_SUPPORTS_ENCRYPTION]
    ):
        _LOGGER.warning(
            "Refusing to accept unencrypted webhook from %s",
            registration[ATTR_DEVICE_NAME],
        )
        return error_response(ERR_ENCRYPTION_REQUIRED, "Encryption required")

    try:
        req_data = WEBHOOK_PAYLOAD_SCHEMA(req_data)
    except vol.Invalid as ex:
        err = vol.humanize.humanize_error(req_data, ex)
        _LOGGER.error("Received invalid webhook payload: %s", err)
        return empty_okay_response()

    webhook_type = req_data[ATTR_WEBHOOK_TYPE]

    webhook_payload = req_data.get(ATTR_WEBHOOK_DATA, {})

    if req_data[ATTR_WEBHOOK_ENCRYPTED]:
        enc_data = req_data[ATTR_WEBHOOK_ENCRYPTED_DATA]
        webhook_payload = _decrypt_payload(registration[CONF_SECRET], enc_data)

    if webhook_type not in WEBHOOK_TYPES:
        _LOGGER.error("Received invalid webhook type: %s", webhook_type)
        return empty_okay_response()

    data = webhook_payload

    _LOGGER.debug("Received webhook payload for type %s: %s", webhook_type, data)

    if webhook_type in WEBHOOK_SCHEMAS:
        try:
            data = WEBHOOK_SCHEMAS[webhook_type](webhook_payload)
        except vol.Invalid as ex:
            err = vol.humanize.humanize_error(webhook_payload, ex)
            _LOGGER.error("Received invalid webhook payload: %s", err)
            return empty_okay_response(headers=headers)

    context = registration_context(registration)

    if webhook_type == WEBHOOK_TYPE_CALL_SERVICE:
        try:
            await opp.services.async_call(
                data[ATTR_DOMAIN],
                data[ATTR_SERVICE],
                data[ATTR_SERVICE_DATA],
                blocking=True,
                context=context,
            )
        except (vol.Invalid, ServiceNotFound, Exception) as ex:
            _LOGGER.error(
                "Error when calling service during mobile_app "
                "webhook (device name: %s): %s",
                registration[ATTR_DEVICE_NAME],
                ex,
            )
            raise HTTPBadRequest()

        return empty_okay_response(headers=headers)

    if webhook_type == WEBHOOK_TYPE_FIRE_EVENT:
        event_type = data[ATTR_EVENT_TYPE]
        opp.bus.async_fire(
            event_type, data[ATTR_EVENT_DATA], EventOrigin.remote, context=context
        )
        return empty_okay_response(headers=headers)

    if webhook_type == WEBHOOK_TYPE_RENDER_TEMPLATE:
        resp = {}
        for key, item in data.items():
            try:
                tpl = item[ATTR_TEMPLATE]
                attach(opp, tpl)
                resp[key] = tpl.async_render(item.get(ATTR_TEMPLATE_VARIABLES))
            except TemplateError as ex:
                resp[key] = {"error": str(ex)}

        return webhook_response(resp, registration=registration, headers=headers)

    if webhook_type == WEBHOOK_TYPE_UPDATE_LOCATION:
        opp.helpers.dispatcher.async_dispatcher_send(
            SIGNAL_LOCATION_UPDATE.format(config_entry.entry_id), data
        )
        return empty_okay_response(headers=headers)

    if webhook_type == WEBHOOK_TYPE_UPDATE_REGISTRATION:
        new_registration = {**registration, **data}

        device_registry = await dr.async_get_registry(opp)

        device_registry.async_get_or_create(
            config_entry_id=config_entry.entry_id,
            identifiers={(DOMAIN, registration[ATTR_DEVICE_ID])},
            manufacturer=new_registration[ATTR_MANUFACTURER],
            model=new_registration[ATTR_MODEL],
            name=new_registration[ATTR_DEVICE_NAME],
            sw_version=new_registration[ATTR_OS_VERSION],
        )

        opp.config_entries.async_update_entry(config_entry, data=new_registration)

        return webhook_response(
            safe_registration(new_registration),
            registration=registration,
            headers=headers,
        )

    if webhook_type == WEBHOOK_TYPE_REGISTER_SENSOR:
        entity_type = data[ATTR_SENSOR_TYPE]

        unique_id = data[ATTR_SENSOR_UNIQUE_ID]

        unique_store_key = f"{webhook_id}_{unique_id}"

        if unique_store_key in opp.data[DOMAIN][entity_type]:
            _LOGGER.error("Refusing to re-register existing sensor %s!", unique_id)
            return error_response(
                ERR_SENSOR_DUPLICATE_UNIQUE_ID,
                f"{entity_type} {unique_id} already exists!",
                status=409,
            )

        data[CONF_WEBHOOK_ID] = webhook_id

        opp.data[DOMAIN][entity_type][unique_store_key] = data

        try:
            await opp.data[DOMAIN][DATA_STORE].async_save(savable_state(opp))
        except OpenPeerPowerError as ex:
            _LOGGER.error("Error registering sensor: %s", ex)
            return empty_okay_response()

        register_signal = "{}_{}_register".format(DOMAIN, data[ATTR_SENSOR_TYPE])
        async_dispatcher_send(opp, register_signal, data)

        return webhook_response(
            {"success": True},
            registration=registration,
            status=HTTP_CREATED,
            headers=headers,
        )

    if webhook_type == WEBHOOK_TYPE_UPDATE_SENSOR_STATES:
        resp = {}
        for sensor in data:
            entity_type = sensor[ATTR_SENSOR_TYPE]

            unique_id = sensor[ATTR_SENSOR_UNIQUE_ID]

            unique_store_key = f"{webhook_id}_{unique_id}"

            if unique_store_key not in opp.data[DOMAIN][entity_type]:
                _LOGGER.error(
                    "Refusing to update non-registered sensor: %s", unique_store_key
                )
                err_msg = f"{entity_type} {unique_id} is not registered"
                resp[unique_id] = {
                    "success": False,
                    "error": {"code": ERR_SENSOR_NOT_REGISTERED, "message": err_msg},
                }
                continue

            entry = opp.data[DOMAIN][entity_type][unique_store_key]

            new_state = {**entry, **sensor}

            opp.data[DOMAIN][entity_type][unique_store_key] = new_state

            safe = savable_state(opp)

            try:
                await opp.data[DOMAIN][DATA_STORE].async_save(safe)
            except OpenPeerPowerError as ex:
                _LOGGER.error("Error updating mobile_app registration: %s", ex)
                return empty_okay_response()

            async_dispatcher_send(opp, SIGNAL_SENSOR_UPDATE, new_state)

            resp[unique_id] = {"success": True}

        return webhook_response(resp, registration=registration, headers=headers)

    if webhook_type == WEBHOOK_TYPE_GET_ZONES:
        zones = (
            opp.states.get(entity_id)
            for entity_id in sorted(opp.states.async_entity_ids(ZONE_DOMAIN))
        )
        return webhook_response(list(zones), registration=registration, headers=headers)

    if webhook_type == WEBHOOK_TYPE_GET_CONFIG:

        opp_config = opp.config.as_dict()

        resp = {
            "latitude": opp_config["latitude"],
            "longitude": opp_config["longitude"],
            "elevation": opp_config["elevation"],
            "unit_system": opp_config["unit_system"],
            "location_name": opp_config["location_name"],
            "time_zone": opp_config["time_zone"],
            "components": opp_config["components"],
            "version": opp_config["version"],
            "theme_color": MANIFEST_JSON["theme_color"],
        }

        if CONF_CLOUDHOOK_URL in registration:
            resp[CONF_CLOUDHOOK_URL] = registration[CONF_CLOUDHOOK_URL]

        try:
            resp[CONF_REMOTE_UI_URL] = opp.components.cloud.async_remote_ui_url()
        except opp.components.cloud.CloudNotAvailable:
            pass

        return webhook_response(resp, registration=registration, headers=headers)
