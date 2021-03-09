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
                u'snapvault my_snap',
                u'state snapmirrored',
                u'source-system c1',
                u'destination-location d3:my_snap',
                u'policy ABCDefault',
                u'lag-time 91486',
                u'destination-system a2-b0-02',
                u'status idle',
            ],
            [
                u'snapvault my_snap',
                u'state snapmirrored',
                u'source-system i1',
                u'destination-location d1:my_snap',
                u'policy Default',
                u'lag-time 82486',
                u'destination-system a2-b0-02',
                u'status idle',
            ],
            [
                u'snapvault my_snap',
                u'state snapmirrored',
                u'source-system t1',
                u'destination-location d2:my_snap',
                u'policy Default',
                u'lag-time 73487',
                u'destination-system a2-b0-02',
                u'status idle',
            ],
        ],
        {
            'my_snap': {
                'snapvault': 'my_snap',
                'state': 'snapmirrored',
                'source-system': 't1',
                'destination-location': 'd2:my_snap',
                'policy': 'Default',
                'lag-time': '73487',
                'destination-system': 'a2-b0-02',
                'status': 'idle',
            },
        },
    ),
])
@pytest.mark.usefixtures("config_load_all_checks")
def test_parse_netapp_api_snapvault(info, expected_parsed):
    check = Check("netapp_api_snapvault")
    for (actual_item, actual_parsed), (expected_item, expected_parsed) in zip(
            sorted(check.run_parse(info).items()),
            sorted(expected_parsed.items()),
    ):
        assert actual_item == expected_item
        assert sorted(actual_parsed.items()) == sorted(expected_parsed.items())


@pytest.mark.parametrize('info, expected_discovery', [
    (
        [
            [
                u'snapvault my_snap',
                u'state snapmirrored',
                u'source-system c1',
                u'destination-location d3:my_snap',
                u'policy ABCDefault',
                u'lag-time 91486',
                u'destination-system a2-b0-02',
                u'status idle',
            ],
            [
                u'snapvault my_snap',
                u'state snapmirrored',
                u'source-system i1',
                u'destination-location d1:my_snap',
                u'policy Default',
                u'lag-time 82486',
                u'destination-system a2-b0-02',
                u'status idle',
            ],
            [
                u'snapvault my_snap',
                u'state snapmirrored',
                u'source-system t1',
                u'destination-location d2:my_snap',
                u'policy Default',
                u'lag-time 73487',
                u'destination-system a2-b0-02',
                u'status idle',
            ],
        ],
        [
            ('my_snap', {}),
        ],
    ),
])
@pytest.mark.usefixtures("config_load_all_checks")
def test_discover_netapp_api_snapvault(info, expected_discovery):
    check = Check('netapp_api_snapvault')
    assertDiscoveryResultsEqual(
        check,
        DiscoveryResult(check.run_discovery(check.run_parse(info))),
        DiscoveryResult(expected_discovery),
    )


@pytest.mark.parametrize('item, params, parsed, expected_result', [
    (
        'my_snap',
        {},
        {
            'my_snap': {
                'snapvault': 'my_snap',
                'state': 'snapmirrored',
                'source-system': 'c1',
                'destination-location': 'd3:my_snap',
                'policy': 'ABCDefault',
                'lag-time': '91486',
                'destination-system': 'a2-b0-02',
                'status': 'idle',
            },
        },
        [
            (0, 'Source-System: c1'),
            (0, 'Destination-System: a2-b0-02'),
            (0, 'Policy: ABCDefault'),
            (0, 'Status: idle'),
            (0, 'State: snapmirrored'),
            (0, 'Lag-Time: 25 h'),
        ],
    ),
])
@pytest.mark.usefixtures("config_load_all_checks")
def test_check_netapp_api_snapvault(item, params, parsed, expected_result):
    check = Check('netapp_api_snapvault')
    assertCheckResultsEqual(
        CheckResult(check.run_check(item, params, parsed)),
        CheckResult(expected_result),
    )
