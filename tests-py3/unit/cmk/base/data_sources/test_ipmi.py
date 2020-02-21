from collections import namedtuple

import pytest  # type: ignore[import]

from cmk.base.data_sources.ipmi import IPMIManagementBoardDataSource

SensorReading = namedtuple(
    "SensorReading", "states health name imprecision units"
    " state_ids type value unavailable")


@pytest.mark.parametrize(
    "reading, parsed",
    [
        # standard case
        (SensorReading(['lower non-critical threshold'], 1, "Hugo", None, "", [42], "hugo-type",
                       None, 0), [b"0", "Hugo", "hugo-type", b"N/A", "", b"WARNING"]),
        # false positive (no non-critical state): let state come through
        (SensorReading(['Present'], 1, "Dingeling", 0.2, b"\xc2\xb0C", [], "FancyDevice",
                       3.14159265,
                       1), [b"0", "Dingeling", "FancyDevice", b"3.14", b"C", b"Present"]),
    ])
def test_ipmi_parse_sensor_reading(reading, parsed):
    assert IPMIManagementBoardDataSource._parse_sensor_reading(0, reading) == parsed
