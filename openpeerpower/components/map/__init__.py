"""Support for showing device locations."""
DOMAIN = "map"


async def async_setup(opp, config):
    """Register the built-in map panel."""
    opp.components.frontend.async_register_built_in_panel(
        "map", "map", "opp:tooltip-account"
    )
    return True
