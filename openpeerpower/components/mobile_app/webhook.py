"""Webhook handlers for mobile_app."""
from functools import wraps
import logging
import secrets

from aiohttp.web import HTTPBadRequest, Request, Response, json_response
from nacl.secret import SecretBox
import voluptuous as vol

from openpeerpower.components.binary_sensor import (
    DEVICE_CLASSES as BINARY_SENSOR_CLASSES,
)
from openpeerpower.components.device_tracker import (
    ATTR_BATTERY,
    ATTR_GPS,
    ATTR_GPS_ACCURACY,
    ATTR_LOCATION_NAME,
)
from openpeerpower.components.frontend import MANIFEST_JSON
from openpeerpower.components.sensor import DEVICE_CLASSES as SENSOR_CLASSES
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
from openpeerpower.helpers import config_validation as cv, device_registry as dr
from openpeerpower.helpers.dispatcher import async_dispatcher_send
from openpeerpower.helpers.template import attach
from openpeerpower.helpers.typing import OpenPeerPowerType
from openpeerpower.util.decorator import Registry

from .const import (
    ATTR_ALTITUDE,
    ATTR_APP_DATA,
    ATTR_APP_VERSION,
    ATTR_COURSE,
    ATTR_DEVICE_ID,
    ATTR_DEVICE_NAME,
    ATTR_EVENT_DATA,
    ATTR_EVENT_TYPE,
    ATTR_MANUFACTURER,
    ATTR_MODEL,
    ATTR_OS_VERSION,
    ATTR_SENSOR_ATTRIBUTES,
    ATTR_SENSOR_DEVICE_CLASS,
    ATTR_SENSOR_ICON,
    ATTR_SENSOR_NAME,
    ATTR_SENSOR_STATE,
    ATTR_SENSOR_TYPE,
    ATTR_SENSOR_TYPE_BINARY_SENSOR,
    ATTR_SENSOR_TYPE_SENSOR,
    ATTR_SENSOR_UNIQUE_ID,
    ATTR_SENSOR_UOM,
    ATTR_SPEED,
    ATTR_SUPPORTS_ENCRYPTION,
    ATTR_TEMPLATE,
    ATTR_TEMPLATE_VARIABLES,
    ATTR_VERTICAL_ACCURACY,
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
    ERR_ENCRYPTION_ALREADY_ENABLED,
    ERR_ENCRYPTION_NOT_AVAILABLE,
    ERR_ENCRYPTION_REQUIRED,
    ERR_SENSOR_DUPLICATE_UNIQUE_ID,
    ERR_SENSOR_NOT_REGISTERED,
    SIGNAL_LOCATION_UPDATE,
    SIGNAL_SENSOR_UPDATE,
)
from .helpers import (
    _decrypt_payload,
    empty_okay_response,
    error_response,
    registration_context,
    safe_registration,
    savable_state,
    supports_encryption,
    webhook_response,
)

_LOGGER = logging.getLogger(__name__)


WEBHOOK_COMMANDS = Registry()

COMBINED_CLASSES = set(BINARY_SENSOR_CLASSES + SENSOR_CLASSES)
SENSOR_TYPES = [ATTR_SENSOR_TYPE_BINARY_SENSOR, ATTR_SENSOR_TYPE_SENSOR]

WEBHOOK_PAYLOAD_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_WEBHOOK_TYPE): cv.string,
        vol.Required(ATTR_WEBHOOK_DATA, default={}): vol.Any(dict, list),
        vol.Optional(ATTR_WEBHOOK_ENCRYPTED, default=False): cv.boolean,
        vol.Optional(ATTR_WEBHOOK_ENCRYPTED_DATA): cv.string,
    }
)


def validate_schema(schema):
    """Decorate a webhook function with a schema."""
    if isinstance(schema, dict):
        schema = vol.Schema(schema)

    def wrapper(func):
        """Wrap function so we validate schema."""

        @wraps(func)
        async def validate_and_run(opp, config_entry, data):
            """Validate input and call handler."""
            try:
                data = schema(data)
            except vol.Invalid as ex:
                err = vol.humanize.humanize_error(data, ex)
                _LOGGER.error("Received invalid webhook payload: %s", err)
                return empty_okay_response()

            return await func(opp, config_entry, data)

        return validate_and_run

    return wrapper


async def handle_webhook(
    opp: OpenPeerPowerType, webhook_id: str, request: Request
) -> Response:
    """Handle webhook callback."""
    if webhook_id in opp.data[DOMAIN][DATA_DELETED_IDS]:
        return Response(status=410)

    config_entry = opp.data[DOMAIN][DATA_CONFIG_ENTRIES][webhook_id]

    try:
        req_data = await request.json()
    except ValueError:
        _LOGGER.warning("Received invalid JSON from mobile_app")
        return empty_okay_response(status=HTTP_BAD_REQUEST)

    if (
        ATTR_WEBHOOK_ENCRYPTED not in req_data
        and config_entry.data[ATTR_SUPPORTS_ENCRYPTION]
    ):
        _LOGGER.warning(
            "Refusing to accept unencrypted webhook from %s",
            config_entry.data[ATTR_DEVICE_NAME],
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
        webhook_payload = _decrypt_payload(config_entry.data[CONF_SECRET], enc_data)

    if webhook_type not in WEBHOOK_COMMANDS:
        _LOGGER.error("Received invalid webhook type: %s", webhook_type)
        return empty_okay_response()

    _LOGGER.debug(
        "Received webhook payload for type %s: %s", webhook_type, webhook_payload
    )

    return await WEBHOOK_COMMANDS[webhook_type](opp, config_entry, webhook_payload)


@WEBHOOK_COMMANDS.register("call_service")
@validate_schema(
    {
        vol.Required(ATTR_DOMAIN): cv.string,
        vol.Required(ATTR_SERVICE): cv.string,
        vol.Optional(ATTR_SERVICE_DATA, default={}): dict,
    }
)
async def webhook_call_service(opp, config_entry, data):
    """Handle a call service webhook."""
    try:
        await opp.services.async_call(
            data[ATTR_DOMAIN],
            data[ATTR_SERVICE],
            data[ATTR_SERVICE_DATA],
            blocking=True,
            context=registration_context(config_entry.data),
        )
    except (vol.Invalid, ServiceNotFound, Exception) as ex:
        _LOGGER.error(
            "Error when calling service during mobile_app "
            "webhook (device name: %s): %s",
            config_entry.data[ATTR_DEVICE_NAME],
            ex,
        )
        raise HTTPBadRequest()

    return empty_okay_response()


@WEBHOOK_COMMANDS.register("fire_event")
@validate_schema(
    {
        vol.Required(ATTR_EVENT_TYPE): cv.string,
        vol.Optional(ATTR_EVENT_DATA, default={}): dict,
    }
)
async def webhook_fire_event(opp, config_entry, data):
    """Handle a fire event webhook."""
    event_type = data[ATTR_EVENT_TYPE]
    opp.bus.async_fire(
        event_type,
        data[ATTR_EVENT_DATA],
        EventOrigin.remote,
        context=registration_context(config_entry.data),
    )
    return empty_okay_response()


@WEBHOOK_COMMANDS.register("render_template")
@validate_schema(
    {
        str: {
            vol.Required(ATTR_TEMPLATE): cv.template,
            vol.Optional(ATTR_TEMPLATE_VARIABLES, default={}): dict,
        }
    }
)
async def webhook_render_template(opp, config_entry, data):
    """Handle a render template webhook."""
    resp = {}
    for key, item in data.items():
        try:
            tpl = item[ATTR_TEMPLATE]
            attach(opp, tpl)
            resp[key] = tpl.async_render(item.get(ATTR_TEMPLATE_VARIABLES))
        except TemplateError as ex:
            resp[key] = {"error": str(ex)}

    return webhook_response(resp, registration=config_entry.data)


@WEBHOOK_COMMANDS.register("update_location")
@validate_schema(
    {
        vol.Optional(ATTR_LOCATION_NAME): cv.string,
        vol.Required(ATTR_GPS): cv.gps,
        vol.Required(ATTR_GPS_ACCURACY): cv.positive_int,
        vol.Optional(ATTR_BATTERY): cv.positive_int,
        vol.Optional(ATTR_SPEED): cv.positive_int,
        vol.Optional(ATTR_ALTITUDE): vol.Coerce(float),
        vol.Optional(ATTR_COURSE): cv.positive_int,
        vol.Optional(ATTR_VERTICAL_ACCURACY): cv.positive_int,
    }
)
async def webhook_update_location(opp, config_entry, data):
    """Handle an update location webhook."""
    opp.helpers.dispatcher.async_dispatcher_send(
        SIGNAL_LOCATION_UPDATE.format(config_entry.entry_id), data
    )
    return empty_okay_response()


@WEBHOOK_COMMANDS.register("update_registration")
@validate_schema(
    {
        vol.Optional(ATTR_APP_DATA, default={}): dict,
        vol.Required(ATTR_APP_VERSION): cv.string,
        vol.Required(ATTR_DEVICE_NAME): cv.string,
        vol.Required(ATTR_MANUFACTURER): cv.string,
        vol.Required(ATTR_MODEL): cv.string,
        vol.Optional(ATTR_OS_VERSION): cv.string,
    }
)
async def webhook_update_registration(opp, config_entry, data):
    """Handle an update registration webhook."""
    new_registration = {**config_entry.data, **data}

    device_registry = await dr.async_get_registry(opp)

    device_registry.async_get_or_create(
        config_entry_id=config_entry.entry_id,
        identifiers={(DOMAIN, config_entry.data[ATTR_DEVICE_ID])},
        manufacturer=new_registration[ATTR_MANUFACTURER],
        model=new_registration[ATTR_MODEL],
        name=new_registration[ATTR_DEVICE_NAME],
        sw_version=new_registration[ATTR_OS_VERSION],
    )

    opp.config_entries.async_update_entry(config_entry, data=new_registration)

    return webhook_response(
        safe_registration(new_registration), registration=new_registration,
    )


@WEBHOOK_COMMANDS.register("enable_encryption")
async def webhook_enable_encryption(opp, config_entry, data):
    """Handle a encryption enable webhook."""
    if config_entry.data[ATTR_SUPPORTS_ENCRYPTION]:
        _LOGGER.warning(
            "Refusing to enable encryption for %s because it is already enabled!",
            config_entry.data[ATTR_DEVICE_NAME],
        )
        return error_response(
            ERR_ENCRYPTION_ALREADY_ENABLED, "Encryption already enabled"
        )

    if not supports_encryption():
        _LOGGER.warning(
            "Unable to enable encryption for %s because libsodium is unavailable!",
            config_entry.data[ATTR_DEVICE_NAME],
        )
        return error_response(ERR_ENCRYPTION_NOT_AVAILABLE, "Encryption is unavailable")

    secret = secrets.token_hex(SecretBox.KEY_SIZE)

    data = {**config_entry.data, ATTR_SUPPORTS_ENCRYPTION: True, CONF_SECRET: secret}

    opp.config_entries.async_update_entry(config_entry, data=data)

    return json_response({"secret": secret})


@WEBHOOK_COMMANDS.register("register_sensor")
@validate_schema(
    {
        vol.Optional(ATTR_SENSOR_ATTRIBUTES, default={}): dict,
        vol.Optional(ATTR_SENSOR_DEVICE_CLASS): vol.All(
            vol.Lower, vol.In(COMBINED_CLASSES)
        ),
        vol.Required(ATTR_SENSOR_NAME): cv.string,
        vol.Required(ATTR_SENSOR_TYPE): vol.In(SENSOR_TYPES),
        vol.Required(ATTR_SENSOR_UNIQUE_ID): cv.string,
        vol.Optional(ATTR_SENSOR_UOM): cv.string,
        vol.Required(ATTR_SENSOR_STATE): vol.Any(bool, str, int, float),
        vol.Optional(ATTR_SENSOR_ICON, default="mdi:cellphone"): cv.icon,
    }
)
async def webhook_register_sensor(opp, config_entry, data):
    """Handle a register sensor webhook."""
    entity_type = data[ATTR_SENSOR_TYPE]

    unique_id = data[ATTR_SENSOR_UNIQUE_ID]

    unique_store_key = f"{config_entry.data[CONF_WEBHOOK_ID]}_{unique_id}"

    if unique_store_key in opp.data[DOMAIN][entity_type]:
        _LOGGER.error("Refusing to re-register existing sensor %s!", unique_id)
        return error_response(
            ERR_SENSOR_DUPLICATE_UNIQUE_ID,
            f"{entity_type} {unique_id} already exists!",
            status=409,
        )

    data[CONF_WEBHOOK_ID] = config_entry.data[CONF_WEBHOOK_ID]

    opp.data[DOMAIN][entity_type][unique_store_key] = data

    try:
        await opp.data[DOMAIN][DATA_STORE].async_save(savable_state(opp))
    except OpenPeerPowerError as ex:
        _LOGGER.error("Error registering sensor: %s", ex)
        return empty_okay_response()

    register_signal = "{}_{}_register".format(DOMAIN, data[ATTR_SENSOR_TYPE])
    async_dispatcher_send(opp, register_signal, data)

    return webhook_response(
        {"success": True}, registration=config_entry.data, status=HTTP_CREATED,
    )


@WEBHOOK_COMMANDS.register("update_sensor_states")
@validate_schema(
    vol.All(
        cv.ensure_list,
        [
            vol.Schema(
                {
                    vol.Optional(ATTR_SENSOR_ATTRIBUTES, default={}): dict,
                    vol.Optional(ATTR_SENSOR_ICON, default="mdi:cellphone"): cv.icon,
                    vol.Required(ATTR_SENSOR_STATE): vol.Any(bool, str, int, float),
                    vol.Required(ATTR_SENSOR_TYPE): vol.In(SENSOR_TYPES),
                    vol.Required(ATTR_SENSOR_UNIQUE_ID): cv.string,
                }
            )
        ],
    )
)
async def webhook_update_sensor_states(opp, config_entry, data):
    """Handle an update sensor states webhook."""
    resp = {}
    for sensor in data:
        entity_type = sensor[ATTR_SENSOR_TYPE]

        unique_id = sensor[ATTR_SENSOR_UNIQUE_ID]

        unique_store_key = f"{config_entry.data[CONF_WEBHOOK_ID]}_{unique_id}"

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

    return webhook_response(resp, registration=config_entry.data)


@WEBHOOK_COMMANDS.register("get_zones")
async def webhook_get_zones(opp, config_entry, data):
    """Handle a get zones webhook."""
    zones = [
        opp.states.get(entity_id)
        for entity_id in sorted(opp.states.async_entity_ids(ZONE_DOMAIN))
    ]
    return webhook_response(zones, registration=config_entry.data)


@WEBHOOK_COMMANDS.register("get_config")
async def webhook_get_config(opp, config_entry, data):
    """Handle a get config webhook."""
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

    if CONF_CLOUDHOOK_URL in config_entry.data:
        resp[CONF_CLOUDHOOK_URL] = config_entry.data[CONF_CLOUDHOOK_URL]

    try:
        resp[CONF_REMOTE_UI_URL] = opp.components.cloud.async_remote_ui_url()
    except opp.components.cloud.CloudNotAvailable:
        pass

    return webhook_response(resp, registration=config_entry.data)
