# -*- coding: utf-8 -*-

import pytest
from checktestlib import BasicCheckResult

pytestmark = pytest.mark.checks


@pytest.mark.parametrize(
    'info,discoveries_expected,checks_expected',
    [
        (  # internal temperature
            [[[u'2070', u'', u'']], []], [
                ('ra32e_sensors', [('Internal', {})]),
                ('ra32e_sensors.humidity', []),
            ], [
                ('ra32e_sensors', "Internal", {}, BasicCheckResult(0, u'20.7 °C',
                                                                   [('temp', 20.70)])),
                ('ra32e_sensors', "Heat Index", {}, BasicCheckResult(3, 'no data for sensor')),
                ('ra32e_sensors.humidity', "Internal", {}, BasicCheckResult(
                    3, 'no data for sensor')),
            ]),
        (  # internal humidity and heat index
            [[[u'', u'6000', u'2070']], []], [
                ('ra32e_sensors', [('Heat Index', {})]),
                ('ra32e_sensors.humidity', [('Internal', {})]),
            ], [
                ('ra32e_sensors', "Internal", {}, BasicCheckResult(3, 'no data for sensor')),
                ('ra32e_sensors', "Heat Index", {},
                 BasicCheckResult(0, u'20.7 °C', [('temp', 20.70)])),
                ('ra32e_sensors.humidity', "Internal", {},
                 BasicCheckResult(0, '60.0%', [('humidity', 60.0, 101, 101, 0, 100)])),
            ]),
        (  # temp sensor (ignores fahrenheit value)
            [[[u'', u'', u'']], [[u'2.0', u'2580', u'9999', '', '', '']]], [
                ('ra32e_sensors', [('Sensor 2', {})]),
            ], [
                ('ra32e_sensors', "Sensor 2", {}, BasicCheckResult(0, u'25.8 °C',
                                                                   [('temp', 25.8)])),
            ]),
        (  # temp/active sensor
            [[[u'', u'', u'']], [[u'5.0', u'3100', '9999', '0', '', '']]], [
                ('ra32e_sensors', [('Sensor 5', {})]),
                ('ra32e_sensors.power', [('Sensor 5', {})]),
            ], [
                ('ra32e_sensors', "Sensor 5", {
                    'levels': (30.0, 35.0)
                },
                 BasicCheckResult(1, u'31.0 °C (warn/crit at 30.0/35.0 °C)',
                                  [('temp', 31.0, 30.0, 35.0)])),
                ('ra32e_sensors.power', "Sensor 5", {},
                 BasicCheckResult(2, 'Device status: no power detected(2)')),
                ('ra32e_sensors.power', "Sensor 5", {
                    'map_device_states': [('no power detected', 1)]
                }, BasicCheckResult(1, 'Device status: no power detected(2)')),
            ]),
        (  # temp/analog and humidity sensor
            [[[u'', u'', u'']],
             [[u'1.0', u'2790', '9999', '7500', '9999', '2800'],
              [u'8.0', u'2580', '9999', '200', '9999', '']]], [
                  ('ra32e_sensors', [('Heat Index 1', {}), ('Sensor 1', {}), ('Sensor 8', {})]),
                  ('ra32e_sensors.voltage', [('Sensor 8', {})]),
                  ('ra32e_sensors.humidity', [('Sensor 1', {})]),
              ], [
                  ('ra32e_sensors', "Sensor 8", {}, BasicCheckResult(0, u'25.8 °C',
                                                                     [('temp', 25.8)])),
                  ('ra32e_sensors', "Heat Index 1", {
                      'levels': (27.0, 28.0)
                  },
                   BasicCheckResult(2, u'28.0 °C (warn/crit at 27.0/28.0 °C)',
                                    [('temp', 28.0, 27.0, 28.0)])),
                  ('ra32e_sensors.voltage', "Sensor 8", {
                      'voltage': (210, 180)
                  },
                   BasicCheckResult(1, 'Voltage: 200 V (warn/crit below 210/180 V)',
                                    [('voltage', 200)])),
                  ('ra32e_sensors', "Sensor 1", {
                      'levels_lower': (30.0, 25.0)
                  }, BasicCheckResult(1, u'27.9 °C (warn/crit below 30.0/25.0 °C)',
                                      [('temp', 27.9)])),
                  ('ra32e_sensors.humidity', "Sensor 1", {
                      'levels_lower': (85.0, 75.0)
                  },
                   BasicCheckResult(1, '75.0% (warn/crit below 85.0%/75.0%)',
                                    [('humidity', 75.0, None, None, 0, 100)])),
              ]),
    ])
def test_ra32e_sensors_inputs(check_manager, info, discoveries_expected, checks_expected):
    ra32e_sensors_checks = [
        'ra32e_sensors', 'ra32e_sensors.humidity', 'ra32e_sensors.voltage', 'ra32e_sensors.power'
    ]

    checks = {name: check_manager.get_check(name) for name in ra32e_sensors_checks}
    parsed = checks['ra32e_sensors'].run_parse(info)

    for check, expected in discoveries_expected:
        result = checks[check].run_discovery(parsed)
        assert sorted(result) == expected

    for check, item, params, expected in checks_expected:
        output = checks[check].run_check(item, params, parsed)
        result = BasicCheckResult(*output)
        assert result == expected
