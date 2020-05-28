"""Component providing default configuration for new users."""
try:
    import av
except ImportError:
    av = None

from openpeerpower.setup import async_setup_component

DOMAIN = "default_config"


async def async_setup(opp, config):
    """Initialize default configuration."""
    if av is None:
        return True

    return await async_setup_component(opp, "stream", config)
