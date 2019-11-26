import os
import pytest

pytestmark = pytest.mark.checks

execfile(os.path.join(os.path.dirname(__file__), '../../../checks/cisco_sensor_item.include'))

FALLBACK = '999'


@pytest.mark.parametrize('status_description, expected_item', [
    ("", FALLBACK),
    ("chassis", "chassis %s" % FALLBACK),
    ("XPP", "XPP %s" % FALLBACK),
    ("Exhaust Fan", "Exhaust Fan %s" % FALLBACK),
    ("Main Power Supply", "Main Power Supply %s" % FALLBACK),
    ("input power A", "input power A %s" % FALLBACK),
    ("Unknown", "Unknown %s" % FALLBACK),
    ("Internal-ambient", "Internal-ambient %s" % FALLBACK),
    ("Exhaust Right(Bezel)", "Exhaust Right(Bezel) %s" % FALLBACK),
    ("Module 15 MSFC Exhaust", "Module 15 MSFC Exhaust %s" % FALLBACK),
    ("Power Supply 1 Fan", "Power Supply 1 Fan %s" % FALLBACK),
    ("Chassis VTT1", "Chassis VTT1"),
    ("Chassis Fan 1", "Chassis Fan 1"),
    ("AC C49-540", "AC C49-540"),
    ("Power Supply 1", "Power Supply 1"),
    ("Power Supply  1", "Power Supply  1"),
    ("Switch 1 Chassis Fan Tray 1", "Switch 1 Chassis Fan Tray 1"),
    ("Power supply 1, WS-CAC-1300W", "Power supply 1"),
    ("Power supply 2, empty", "Power supply 2"),
    ("Sw1, PSA Normal", "Sw1 PSA %s" % FALLBACK),
    ("Sw1, PS1 Normal, RPS Normal", "Sw1 PS1"),
    ("Switch 1 Power Supply 1", "Switch 1 Power Supply 1"),
    ("Switch#1, PowerSupply 1", "Switch 1 PowerSupply 1"),
    ("Switch#1, PowerSupply#1, Status is Normal, RPS is Normal", "Switch 1 PowerSupply 1"),
    ("Switch#3, PowerSupply#1, Status is Critical, RPS is Normal", "Switch 3 PowerSupply 1"),
    ("Switch 1 - Power Supply A, Normal", "Switch 1 - Power Supply A %s" % FALLBACK),
    ("Switch 2 - Power Supply A, Normal", "Switch 2 - Power Supply A %s" % FALLBACK),
    ("Switch 3 - Power Supply A, Normal", "Switch 3 - Power Supply A %s" % FALLBACK),
    ("SW#1, Sensor#1, YELLOW ", "SW 1 Sensor 1"),
    ("Switch 1 - Temp Sensor 0, GREEN", "Switch 1 - Temp Sensor 0"),
    ("Switch#2, Sensor#1, Status is GREEN", "Switch 2 Sensor 1"),
    ("Power Supply 1B Temp Sensor : GREEN ", "Power Supply 1B Temp Sensor : GREEN  %s" % FALLBACK),
    ("Switch 1 - HotSpot Temp Sensor, GREEN ", "Switch 1 - HotSpot Temp Sensor %s" % FALLBACK),
    ("Switch#1, Fan#1", "Switch 1 Fan 1"),
    ("Switch 1 - FAN 1, Normal", "Switch 1 - FAN 1"),
    ("Switch#1, Fan#2", "Switch 1 Fan 2"),
    ("Switch#1, Fan#1, Status is Normal", "Switch 1 Fan 1"),
    ("Switch 1 - FAN - T1 1, Normal", "Switch 1 - FAN - T1 1"),
])
def test_cisco_sensor_item(status_description, expected_item):
    assert cisco_sensor_item(status_description, FALLBACK) == expected_item
