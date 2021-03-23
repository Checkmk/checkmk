import pytest
from checktestlib import (
    CheckResult,
    DiscoveryResult,
    assertDiscoveryResultsEqual,
    assertCheckResultsEqual,
)
from testlib import Check  # type: ignore[import]

pytestmark = pytest.mark.checks


@pytest.mark.parametrize("info, expected_parsed", [
    (
        [
            [
                ['1', 'PA-500'],
                ['2', 'Fan #1 Operational'],
                ['3', 'Fan #2 Operational'],
                ['4', 'Temperature at MP [U6]'],
                ['5', 'Temperature at DP [U7]'],
            ],
            [
                ['2', '10', '9', '1', '1'],
                ['3', '10', '9', '1', '1'],
                ['4', '8', '9', '37', '1'],
                ['5', '8', '9', '40', '1'],
            ],
        ],
        {
            'fan': {
                'Sensor 1 Operational': {
                    'unit': 'RPM',
                    'reading': 1.0,
                    'status_descr': 'OK',
                    'state': 0
                },
                'Sensor 2 Operational': {
                    'unit': 'RPM',
                    'reading': 1.0,
                    'status_descr': 'OK',
                    'state': 0
                }
            },
            'temp': {
                'Sensor at MP [U6]': {
                    'unit': 'c',
                    'reading': 37.0,
                    'status_descr': 'OK',
                    'state': 0
                },
                'Sensor at DP [U7]': {
                    'unit': 'c',
                    'reading': 40.0,
                    'status_descr': 'OK',
                    'state': 0
                },
            },
        },
    ),
])
def test_parse_entity_sensors(info, expected_parsed):
    check = Check("entity_sensors")
    assert check.run_parse(info) == expected_parsed


@pytest.mark.parametrize('info, expected_discovery_temp, expected_discovery_fan', [
    (
        [
            [
                ['1', 'PA-500'],
                ['2', 'Fan #1 Operational'],
                ['3', 'Fan #2 Operational'],
                ['4', 'Temperature at MP [U6]'],
                ['5', 'Temperature at DP [U7]'],
            ],
            [
                ['2', '10', '9', '1', '1'],
                ['3', '10', '9', '1', '1'],
                ['4', '8', '9', '37', '1'],
                ['5', '8', '9', '40', '1'],
            ],
        ],
        [
            ('Sensor at MP [U6]', {}),
            ('Sensor at DP [U7]', {}),
        ],
        [
            ('Sensor 1 Operational', {}),
            ('Sensor 2 Operational', {}),
        ],
    ),
])
def test_discover_entity_sensors(info, expected_discovery_temp, expected_discovery_fan):
    check = Check('entity_sensors')
    parsed = check.run_parse(info)
    assertDiscoveryResultsEqual(
        check,
        DiscoveryResult(check.run_discovery(parsed)),
        DiscoveryResult(expected_discovery_temp),
    )

    check = Check('entity_sensors.fan')
    assertDiscoveryResultsEqual(
        check,
        DiscoveryResult(check.run_discovery(parsed)),
        DiscoveryResult(expected_discovery_fan),
    )


@pytest.mark.parametrize('item, params, parsed, expected_result', [
    (
        'Sensor at DP [U7]',
        {
            'lower': (35.0, 40.0),
        },
        {
            'fan': {
                'Sensor 1 Operational': {
                    'unit': 'RPM',
                    'reading': 1.0,
                    'status_descr': 'OK',
                    'state': 0
                },
                'Sensor 2 Operational': {
                    'unit': 'RPM',
                    'reading': 1.0,
                    'status_descr': 'OK',
                    'state': 0
                }
            },
            'temp': {
                'Sensor at MP [U6]': {
                    'unit': 'c',
                    'reading': 37.0,
                    'status_descr': 'OK',
                    'state': 0
                },
                'Sensor at DP [U7]': {
                    'unit': 'c',
                    'reading': 40.0,
                    'status_descr': 'OK',
                    'state': 0
                },
            },
        },
        [
            (0, '40.0 °C', [('temp', 40.0, None, None, None)]),
        ],
    ),
])
def test_check_entity_sensors_temp(item, params, parsed, expected_result):
    check = Check('entity_sensors')
    assertCheckResultsEqual(
        CheckResult(check.run_check(item, params, parsed)),
        CheckResult(expected_result),
    )


@pytest.mark.parametrize('item, params, parsed, expected_result', [
    (
        'Sensor 1 Operational',
        {
            'lower': (2000, 1000),
        },
        {
            'fan': {
                'Sensor 1 Operational': {
                    'unit': 'RPM',
                    'reading': 1.0,
                    'status_descr': 'OK',
                    'state': 0
                },
                'Sensor 2 Operational': {
                    'unit': 'RPM',
                    'reading': 1.0,
                    'status_descr': 'OK',
                    'state': 0
                }
            },
            'temp': {
                'Sensor at MP [U6]': {
                    'unit': 'c',
                    'reading': 37.0,
                    'status_descr': 'OK',
                    'state': 0
                },
                'Sensor at DP [U7]': {
                    'unit': 'c',
                    'reading': 40.0,
                    'status_descr': 'OK',
                    'state': 0
                },
            },
        },
        [
            (0, 'Operational status: OK'),
            (2, 'Speed: 1 RPM (warn/crit below 2000 RPM/1000 RPM)'),
        ],
    ),
])
def test_check_entity_sensors_fan(item, params, parsed, expected_result):
    check = Check('entity_sensors.fan')
    assertCheckResultsEqual(
        CheckResult(check.run_check(item, params, parsed)),
        CheckResult(expected_result),
    )
