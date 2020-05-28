"""The tests for the geolocation component."""
import pytest

from openpeerpower.components import geo_location
from openpeerpower.components.geo_location import GeolocationEvent
from openpeerpower.setup import async_setup_component


async def test_setup_component(opp):
    """Simple test setup of component."""
    result = await async_setup_component(opp, geo_location.DOMAIN, {})
    assert result


async def test_event(opp):
    """Simple test of the geolocation event class."""
    entity = GeolocationEvent()

    assert entity.state is None
    assert entity.distance is None
    assert entity.latitude is None
    assert entity.longitude is None
    with pytest.raises(NotImplementedError):
        assert entity.source is None
