"""Onboarding views."""
import asyncio

import voluptuous as vol

from openpeerpower.components.http.data_validator import RequestDataValidator
from openpeerpower.components.http.view import OpenPeerPowerView
from openpeerpower.core import callback

from .const import (
    DEFAULT_AREAS,
    DOMAIN,
    STEP_CORE_CONFIG,
    STEP_INTEGRATION,
    STEP_USER,
    STEPS,
)


async def async_setup(opp, data, store):
    """Set up the onboarding view."""
    opp.http.register_view(OnboardingView(data, store))
    opp.http.register_view(UserOnboardingView(data, store))
    opp.http.register_view(CoreConfigOnboardingView(data, store))
    opp.http.register_view(IntegrationOnboardingView(data, store))


class OnboardingView(OpenPeerPowerView):
    """Return the onboarding status."""

    requires_auth = False
    url = "/api/onboarding"
    name = "api:onboarding"

    def __init__(self, data, store):
        """Initialize the onboarding view."""
        self._store = store
        self._data = data

    async def get(self, request):
        """Return the onboarding status."""
        return self.json(
            [{"step": key, "done": key in self._data["done"]} for key in STEPS]
        )


class _BaseOnboardingView(OpenPeerPowerView):
    """Base class for onboarding."""

    step = None

    def __init__(self, data, store):
        """Initialize the onboarding view."""
        self._store = store
        self._data = data
        self._lock = asyncio.Lock()

    @callback
    def _async_is_done(self):
        """Return if this step is done."""
        return self.step in self._data["done"]

    async def _async_mark_done(self, opp):
        """Mark step as done."""
        self._data["done"].append(self.step)
        await self._store.async_save(self._data)

        if set(self._data["done"]) == set(STEPS):
            opp.data[DOMAIN] = True


class UserOnboardingView(_BaseOnboardingView):
    """View to handle create user onboarding step."""

    url = "/api/onboarding/users"
    name = "api:onboarding:users"
    requires_auth = False
    step = STEP_USER

    @RequestDataValidator(
        vol.Schema(
            {
                vol.Required("name"): str,
                vol.Required("username"): str,
                vol.Required("password"): str,
                vol.Required("client_id"): str,
                vol.Required("language"): str,
            }
        )
    )
    async def post(self, request, data):
        """Handle user creation, area creation."""
        opp = request.app["opp"]

        async with self._lock:
            if self._async_is_done():
                return self.json_message("User step already done", 403)

            provider = _async_get_opp_provider(opp)
            await provider.async_initialize()

            user = await opp.auth.async_create_user(data["name"])
            await opp.async_add_executor_job(
                provider.data.add_auth, data["username"], data["password"]
            )
            credentials = await provider.async_get_or_create_credentials(
                {"username": data["username"]}
            )
            await provider.data.async_save()
            await opp.auth.async_link_user(user, credentials)
            if "person" in opp.config.components:
                await opp.components.person.async_create_person(
                    data["name"], user_id=user.id
                )

            # Create default areas using the users supplied language.
            translations = await opp.helpers.translation.async_get_translations(
                data["language"]
            )

            area_registry = await opp.helpers.area_registry.async_get_registry()

            for area in DEFAULT_AREAS:
                area_registry.async_create(
                    translations[f"component.onboarding.area.{area}"]
                )

            await self._async_mark_done(opp)

            # Return authorization code for fetching tokens and connect
            # during onboarding.
            auth_code = opp.components.auth.create_auth_code(data["client_id"], user)
            return self.json({"auth_code": auth_code})


class CoreConfigOnboardingView(_BaseOnboardingView):
    """View to finish core config onboarding step."""

    url = "/api/onboarding/core_config"
    name = "api:onboarding:core_config"
    step = STEP_CORE_CONFIG

    async def post(self, request):
        """Handle finishing core config step."""
        opp = request.app["opp"]

        async with self._lock:
            if self._async_is_done():
                return self.json_message("Core config step already done", 403)

            await self._async_mark_done(opp)

            await opp.config_entries.flow.async_init(
                "met", context={"source": "onboarding"}
            )

            return self.json({})


class IntegrationOnboardingView(_BaseOnboardingView):
    """View to finish integration onboarding step."""

    url = "/api/onboarding/integration"
    name = "api:onboarding:integration"
    step = STEP_INTEGRATION

    @RequestDataValidator(vol.Schema({vol.Required("client_id"): str}))
    async def post(self, request, data):
        """Handle token creation."""
        opp = request.app["opp"]
        user = request["opp_user"]

        async with self._lock:
            if self._async_is_done():
                return self.json_message("Integration step already done", 403)

            await self._async_mark_done(opp)

            # Return authorization code so we can redirect user and log them in
            auth_code = opp.components.auth.create_auth_code(data["client_id"], user)
            return self.json({"auth_code": auth_code})


@callback
def _async_get_opp_provider(opp):
    """Get the Open Peer Power auth provider."""
    for prv in opp.auth.auth_providers:
        if prv.type == "openpeerpower":
            return prv

    raise RuntimeError("No Open Peer Power provider found")
