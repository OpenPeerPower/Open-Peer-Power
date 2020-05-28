"""Temperature helpers for Open Peer Power."""
from numbers import Number
from typing import Optional

from openpeerpower.const import PRECISION_HALVES, PRECISION_TENTHS
from openpeerpower.core import OpenPeerPower
from openpeerpower.util.temperature import convert as convert_temperature


def display_temp(
    opp: OpenPeerPower, temperature: Optional[float], unit: str, precision: float
) -> Optional[float]:
    """Convert temperature into preferred units/precision for display."""
    temperature_unit = unit
    op_unit = opp.config.units.temperature_unit

    if temperature is None:
        return temperature

    # If the temperature is not a number this can cause issues
    # with Polymer components, so bail early there.
    if not isinstance(temperature, Number):
        raise TypeError(f"Temperature is not a number: {temperature}")

    # type ignore: https://github.com/python/mypy/issues/7207
    if temperature_unit != op_unit:  # type: ignore
        temperature = convert_temperature(temperature, temperature_unit, op_unit)

    # Round in the units appropriate
    if precision == PRECISION_HALVES:
        temperature = round(temperature * 2) / 2.0
    elif precision == PRECISION_TENTHS:
        temperature = round(temperature, 1)
    # Integer as a fall back (PRECISION_WHOLE)
    else:
        temperature = round(temperature)

    return temperature
