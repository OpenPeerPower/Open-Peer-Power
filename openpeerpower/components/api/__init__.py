"""Rest API for Open Peer Power."""
import asyncio
import json
import logging

from aiohttp import web
from aiohttp.web_exceptions import HTTPBadRequest
import async_timeout
import voluptuous as vol

from openpeerpower.auth.permissions.const import POLICY_READ
from openpeerpower.bootstrap import DATA_LOGGING
from openpeerpower.components.http import OpenPeerPowerView
from openpeerpower.const import (
    EVENT_OPENPEERPOWER_STOP,
    EVENT_TIME_CHANGED,
    HTTP_BAD_REQUEST,
    HTTP_CREATED,
    HTTP_NOT_FOUND,
    MATCH_ALL,
    URL_API,
    URL_API_COMPONENTS,
    URL_API_CONFIG,
    URL_API_DISCOVERY_INFO,
    URL_API_ERROR_LOG,
    URL_API_EVENTS,
    URL_API_SERVICES,
    URL_API_STATES,
    URL_API_STATES_ENTITY,
    URL_API_STREAM,
    URL_API_TEMPLATE,
    __version__,
)
import openpeerpower.core as op
from openpeerpower.exceptions import ServiceNotFound, TemplateError, Unauthorized
from openpeerpower.helpers import template
from openpeerpower.helpers.json import JSONEncoder
from openpeerpower.helpers.service import async_get_all_descriptions
from openpeerpower.helpers.state import AsyncTrackStates

_LOGGER = logging.getLogger(__name__)

ATTR_BASE_URL = "base_url"
ATTR_LOCATION_NAME = "location_name"
ATTR_REQUIRES_API_PASSWORD = "requires_api_password"
ATTR_VERSION = "version"

DOMAIN = "api"
STREAM_PING_PAYLOAD = "ping"
STREAM_PING_INTERVAL = 50  # seconds


def setup(opp, config):
    """Register the API with the HTTP interface."""
    opp.http.register_view(APIStatusView)
    opp.http.register_view(APIEventStream)
    opp.http.register_view(APIConfigView)
    opp.http.register_view(APIDiscoveryView)
    opp.http.register_view(APIStatesView)
    opp.http.register_view(APIEntityStateView)
    opp.http.register_view(APIEventListenersView)
    opp.http.register_view(APIEventView)
    opp.http.register_view(APIServicesView)
    opp.http.register_view(APIDomainServicesView)
    opp.http.register_view(APIComponentsView)
    opp.http.register_view(APITemplateView)

    if DATA_LOGGING in opp.data:
        opp.http.register_view(APIErrorLog)

    return True


class APIStatusView(OpenPeerPowerView):
    """View to handle Status requests."""

    url = URL_API
    name = "api:status"

    @op.callback
    def get(self, request):
        """Retrieve if API is running."""
        return self.json_message("API running.")


class APIEventStream(OpenPeerPowerView):
    """View to handle EventStream requests."""

    url = URL_API_STREAM
    name = "api:stream"

    async def get(self, request):
        """Provide a streaming interface for the event bus."""
        if not request["opp_user"].is_admin:
            raise Unauthorized()
        opp = request.app["opp"]
        stop_obj = object()
        to_write = asyncio.Queue()

        restrict = request.query.get("restrict")
        if restrict:
            restrict = restrict.split(",") + [EVENT_OPENPEERPOWER_STOP]

        async def forward_events(event):
            """Forward events to the open request."""
            if event.event_type == EVENT_TIME_CHANGED:
                return

            if restrict and event.event_type not in restrict:
                return

            _LOGGER.debug("STREAM %s FORWARDING %s", id(stop_obj), event)

            if event.event_type == EVENT_OPENPEERPOWER_STOP:
                data = stop_obj
            else:
                data = json.dumps(event, cls=JSONEncoder)

            await to_write.put(data)

        response = web.StreamResponse()
        response.content_type = "text/event-stream"
        await response.prepare(request)

        unsub_stream = opp.bus.async_listen(MATCH_ALL, forward_events)

        try:
            _LOGGER.debug("STREAM %s ATTACHED", id(stop_obj))

            # Fire off one message so browsers fire open event right away
            await to_write.put(STREAM_PING_PAYLOAD)

            while True:
                try:
                    with async_timeout.timeout(STREAM_PING_INTERVAL):
                        payload = await to_write.get()

                    if payload is stop_obj:
                        break

                    msg = f"data: {payload}\n\n"
                    _LOGGER.debug("STREAM %s WRITING %s", id(stop_obj), msg.strip())
                    await response.write(msg.encode("UTF-8"))
                except asyncio.TimeoutError:
                    await to_write.put(STREAM_PING_PAYLOAD)

        except asyncio.CancelledError:
            _LOGGER.debug("STREAM %s ABORT", id(stop_obj))

        finally:
            _LOGGER.debug("STREAM %s RESPONSE CLOSED", id(stop_obj))
            unsub_stream()

        return response


class APIConfigView(OpenPeerPowerView):
    """View to handle Configuration requests."""

    url = URL_API_CONFIG
    name = "api:config"

    @op.callback
    def get(self, request):
        """Get current configuration."""
        return self.json(request.app["opp"].config.as_dict())


class APIDiscoveryView(OpenPeerPowerView):
    """View to provide Discovery information."""

    requires_auth = False
    url = URL_API_DISCOVERY_INFO
    name = "api:discovery"

    @op.callback
    def get(self, request):
        """Get discovery information."""
        opp = request.app["opp"]
        return self.json(
            {
                ATTR_BASE_URL: opp.config.api.base_url,
                ATTR_LOCATION_NAME: opp.config.location_name,
                # always needs authentication
                ATTR_REQUIRES_API_PASSWORD: True,
                ATTR_VERSION: __version__,
            }
        )


class APIStatesView(OpenPeerPowerView):
    """View to handle States requests."""

    url = URL_API_STATES
    name = "api:states"

    @op.callback
    def get(self, request):
        """Get current states."""
        user = request["opp_user"]
        entity_perm = user.permissions.check_entity
        states = [
            state
            for state in request.app["opp"].states.async_all()
            if entity_perm(state.entity_id, "read")
        ]
        return self.json(states)


class APIEntityStateView(OpenPeerPowerView):
    """View to handle EntityState requests."""

    url = "/api/states/{entity_id}"
    name = "api:entity-state"

    @op.callback
    def get(self, request, entity_id):
        """Retrieve state of entity."""
        user = request["opp_user"]
        if not user.permissions.check_entity(entity_id, POLICY_READ):
            raise Unauthorized(entity_id=entity_id)

        state = request.app["opp"].states.get(entity_id)
        if state:
            return self.json(state)
        return self.json_message("Entity not found.", HTTP_NOT_FOUND)

    async def post(self, request, entity_id):
        """Update state of entity."""
        if not request["opp_user"].is_admin:
            raise Unauthorized(entity_id=entity_id)
        opp = request.app["opp"]
        try:
            data = await request.json()
        except ValueError:
            return self.json_message("Invalid JSON specified.", HTTP_BAD_REQUEST)

        new_state = data.get("state")

        if new_state is None:
            return self.json_message("No state specified.", HTTP_BAD_REQUEST)

        attributes = data.get("attributes")
        force_update = data.get("force_update", False)

        is_new_state = opp.states.get(entity_id) is None

        # Write state
        opp.states.async_set(
            entity_id, new_state, attributes, force_update, self.context(request)
        )

        # Read the state back for our response
        status_code = HTTP_CREATED if is_new_state else 200
        resp = self.json(opp.states.get(entity_id), status_code)

        resp.headers.add("Location", URL_API_STATES_ENTITY.format(entity_id))

        return resp

    @op.callback
    def delete(self, request, entity_id):
        """Remove entity."""
        if not request["opp_user"].is_admin:
            raise Unauthorized(entity_id=entity_id)
        if request.app["opp"].states.async_remove(entity_id):
            return self.json_message("Entity removed.")
        return self.json_message("Entity not found.", HTTP_NOT_FOUND)


class APIEventListenersView(OpenPeerPowerView):
    """View to handle EventListeners requests."""

    url = URL_API_EVENTS
    name = "api:event-listeners"

    @op.callback
    def get(self, request):
        """Get event listeners."""
        return self.json(async_events_json(request.app["opp"]))


class APIEventView(OpenPeerPowerView):
    """View to handle Event requests."""

    url = "/api/events/{event_type}"
    name = "api:event"

    async def post(self, request, event_type):
        """Fire events."""
        if not request["opp_user"].is_admin:
            raise Unauthorized()
        body = await request.text()
        try:
            event_data = json.loads(body) if body else None
        except ValueError:
            return self.json_message(
                "Event data should be valid JSON.", HTTP_BAD_REQUEST
            )

        if event_data is not None and not isinstance(event_data, dict):
            return self.json_message(
                "Event data should be a JSON object", HTTP_BAD_REQUEST
            )

        # Special case handling for event STATE_CHANGED
        # We will try to convert state dicts back to State objects
        if event_type == op.EVENT_STATE_CHANGED and event_data:
            for key in ("old_state", "new_state"):
                state = op.State.from_dict(event_data.get(key))

                if state:
                    event_data[key] = state

        request.app["opp"].bus.async_fire(
            event_type, event_data, op.EventOrigin.remote, self.context(request)
        )

        return self.json_message(f"Event {event_type} fired.")


class APIServicesView(OpenPeerPowerView):
    """View to handle Services requests."""

    url = URL_API_SERVICES
    name = "api:services"

    async def get(self, request):
        """Get registered services."""
        services = await async_services_json(request.app["opp"])
        return self.json(services)


class APIDomainServicesView(OpenPeerPowerView):
    """View to handle DomainServices requests."""

    url = "/api/services/{domain}/{service}"
    name = "api:domain-services"

    async def post(self, request, domain, service):
        """Call a service.

        Returns a list of changed states.
        """
        opp = request.app["opp"]
        body = await request.text()
        try:
            data = json.loads(body) if body else None
        except ValueError:
            return self.json_message("Data should be valid JSON.", HTTP_BAD_REQUEST)

        with AsyncTrackStates(opp) as changed_states:
            try:
                await opp.services.async_call(
                    domain, service, data, True, self.context(request)
                )
            except (vol.Invalid, ServiceNotFound):
                raise HTTPBadRequest()

        return self.json(changed_states)


class APIComponentsView(OpenPeerPowerView):
    """View to handle Components requests."""

    url = URL_API_COMPONENTS
    name = "api:components"

    @op.callback
    def get(self, request):
        """Get current loaded components."""
        return self.json(request.app["opp"].config.components)


class APITemplateView(OpenPeerPowerView):
    """View to handle Template requests."""

    url = URL_API_TEMPLATE
    name = "api:template"

    async def post(self, request):
        """Render a template."""
        if not request["opp_user"].is_admin:
            raise Unauthorized()
        try:
            data = await request.json()
            tpl = template.Template(data["template"], request.app["opp"])
            return tpl.async_render(data.get("variables"))
        except (ValueError, TemplateError) as ex:
            return self.json_message(
                f"Error rendering template: {ex}", HTTP_BAD_REQUEST
            )


class APIErrorLog(OpenPeerPowerView):
    """View to fetch the API error log."""

    url = URL_API_ERROR_LOG
    name = "api:error_log"

    async def get(self, request):
        """Retrieve API error log."""
        if not request["opp_user"].is_admin:
            raise Unauthorized()
        return web.FileResponse(request.app["opp"].data[DATA_LOGGING])


async def async_services_json(opp):
    """Generate services data to JSONify."""
    descriptions = await async_get_all_descriptions(opp)
    return [{"domain": key, "services": value} for key, value in descriptions.items()]


@op.callback
def async_events_json(opp):
    """Generate event data to JSONify."""
    return [
        {"event": key, "listener_count": value}
        for key, value in opp.bus.async_listeners().items()
    ]
