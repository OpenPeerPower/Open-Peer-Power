"""Helpers for sun events."""
import datetime
from typing import TYPE_CHECKING, Optional, Union

from openpeerpower.const import SUN_EVENT_SUNRISE, SUN_EVENT_SUNSET
from openpeerpower.core import callback
from openpeerpower.loader import bind_opp
from openpeerpower.util import dt as dt_util

from .typing import OpenPeerPowerType

if TYPE_CHECKING:
    import astral  # pylint: disable=unused-import

DATA_LOCATION_CACHE = "astral_location_cache"


@callback
@bind_opp
def get_astral_location(opp: OpenPeerPowerType) -> "astral.Location":
    """Get an astral location for the current Open Peer Power configuration."""
    from astral import Location

    latitude = opp.config.latitude
    longitude = opp.config.longitude
    timezone = str(opp.config.time_zone)
    elevation = opp.config.elevation
    info = ("", "", latitude, longitude, timezone, elevation)

    # Cache astral locations so they aren't recreated with the same args
    if DATA_LOCATION_CACHE not in opp.data:
        opp.data[DATA_LOCATION_CACHE] = {}

    if info not in opp.data[DATA_LOCATION_CACHE]:
        opp.data[DATA_LOCATION_CACHE][info] = Location(info)

    return opp.data[DATA_LOCATION_CACHE][info]


@callback
@bind_opp
def get_astral_event_next(
    opp: OpenPeerPowerType,
    event: str,
    utc_point_in_time: Optional[datetime.datetime] = None,
    offset: Optional[datetime.timedelta] = None,
) -> datetime.datetime:
    """Calculate the next specified solar event."""
    location = get_astral_location(opp)
    return get_location_astral_event_next(location, event, utc_point_in_time, offset)


@callback
def get_location_astral_event_next(
    location: "astral.Location",
    event: str,
    utc_point_in_time: Optional[datetime.datetime] = None,
    offset: Optional[datetime.timedelta] = None,
) -> datetime.datetime:
    """Calculate the next specified solar event."""
    from astral import AstralError

    if offset is None:
        offset = datetime.timedelta()

    if utc_point_in_time is None:
        utc_point_in_time = dt_util.utcnow()

    mod = -1
    while True:
        try:
            next_dt: datetime.datetime = (
                getattr(location, event)(
                    dt_util.as_local(utc_point_in_time).date()
                    + datetime.timedelta(days=mod),
                    local=False,
                )
                + offset
            )
            if next_dt > utc_point_in_time:
                return next_dt
        except AstralError:
            pass
        mod += 1


@callback
@bind_opp
def get_astral_event_date(
    opp: OpenPeerPowerType,
    event: str,
    date: Union[datetime.date, datetime.datetime, None] = None,
) -> Optional[datetime.datetime]:
    """Calculate the astral event time for the specified date."""
    from astral import AstralError

    location = get_astral_location(opp)

    if date is None:
        date = dt_util.now().date()

    if isinstance(date, datetime.datetime):
        date = dt_util.as_local(date).date()

    try:
        return getattr(location, event)(date, local=False)  # type: ignore
    except AstralError:
        # Event never occurs for specified date.
        return None


@callback
@bind_opp
def is_up(
    opp: OpenPeerPowerType, utc_point_in_time: Optional[datetime.datetime] = None
) -> bool:
    """Calculate if the sun is currently up."""
    if utc_point_in_time is None:
        utc_point_in_time = dt_util.utcnow()

    next_sunrise = get_astral_event_next(opp, SUN_EVENT_SUNRISE, utc_point_in_time)
    next_sunset = get_astral_event_next(opp, SUN_EVENT_SUNSET, utc_point_in_time)

    return next_sunrise > next_sunset
