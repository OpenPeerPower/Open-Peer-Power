"""Tests for the auth component."""
from openpeerpower import auth
from openpeerpower.setup import async_setup_component

from tests.common import ensure_auth_manager_loaded

BASE_CONFIG = [
    {
        "name": "Example",
        "type": "insecure_example",
        "users": [
            {"username": "test-user", "password": "test-pass", "name": "Test Name"}
        ],
    }
]

EMPTY_CONFIG = []


async def async_setup_auth(
    opp,
    aiohttp_client,
    provider_configs=BASE_CONFIG,
    module_configs=EMPTY_CONFIG,
    setup_api=False,
):
    """Set up authentication and create an HTTP client."""
    opp.auth = await auth.auth_manager_from_config(
        opp, provider_configs, module_configs
    )
    ensure_auth_manager_loaded(opp.auth)
    await async_setup_component(opp, "auth", {})
    if setup_api:
        await async_setup_component(opp, "api", {})
    return await aiohttp_client(opp.http.app)
