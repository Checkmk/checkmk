import pytest
from checktestlib import (
    CheckResult,
    DiscoveryResult,
    assertDiscoveryResultsEqual,
    assertCheckResultsEqual,
)

pytestmark = pytest.mark.checks


@pytest.mark.parametrize("info, expected_parsed", [
    (
        [
            [
                u'snapvault sv_home',
                u'state snapmirrored',
                u'source-system cnlan1snas001',
                u'destination-location nlhoo2snas003:sv_home',
                u'policy XPDefaultCompression',
                u'lag-time 91486',
                u'destination-system nlhoo2-scl020-02',
                u'status idle',
            ],
            [
                u'snapvault sv_home',
                u'state snapmirrored',
                u'source-system inpnq1snas001',
                u'destination-location nlhoo2snas001:sv_home',
                u'policy XDPDefault',
                u'lag-time 82486',
                u'destination-system nlhoo2-scl020-02',
                u'status idle',
            ],
            [
                u'snapvault sv_home',
                u'state snapmirrored',
                u'source-system trizm1snas001',
                u'destination-location nlhoo2snas002:sv_home',
                u'policy XDPDefault',
                u'lag-time 73487',
                u'destination-system nlhoo2-scl020-01',
                u'status idle',
            ],
        ],
        {
            'sv_home': {
                'snapvault': 'sv_home',
                'state': 'snapmirrored',
                'source-system': 'trizm1snas001',
                'destination-location': 'nlhoo2snas002:sv_home',
                'policy': 'XDPDefault',
                'lag-time': '73487',
                'destination-system': 'nlhoo2-scl020-01',
                'status': 'idle',
            },
        },
    ),
])
def test_parse_netapp_api_snapvault(check_manager, info, expected_parsed):
    check = check_manager.get_check("netapp_api_snapvault")
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
                u'snapvault sv_home',
                u'state snapmirrored',
                u'source-system cnlan1snas001',
                u'destination-location nlhoo2snas003:sv_home',
                u'policy XPDefaultCompression',
                u'lag-time 91486',
                u'destination-system nlhoo2-scl020-02',
                u'status idle',
            ],
            [
                u'snapvault sv_home',
                u'state snapmirrored',
                u'source-system inpnq1snas001',
                u'destination-location nlhoo2snas001:sv_home',
                u'policy XDPDefault',
                u'lag-time 82486',
                u'destination-system nlhoo2-scl020-02',
                u'status idle',
            ],
            [
                u'snapvault sv_home',
                u'state snapmirrored',
                u'source-system trizm1snas001',
                u'destination-location nlhoo2snas002:sv_home',
                u'policy XDPDefault',
                u'lag-time 73487',
                u'destination-system nlhoo2-scl020-01',
                u'status idle',
            ],
        ],
        [
            ('sv_home', {}),
        ],
    ),
])
def test_discover_netapp_api_snapvault(check_manager, info, expected_discovery):
    check = check_manager.get_check('netapp_api_snapvault')
    assertDiscoveryResultsEqual(
        check,
        DiscoveryResult(check.run_discovery(check.run_parse(info))),
        DiscoveryResult(expected_discovery),
    )


@pytest.mark.parametrize('item, params, parsed, expected_result', [
    (
        'sv_home',
        {},
        {
            'sv_home': {
                'snapvault': 'sv_home',
                'state': 'snapmirrored',
                'source-system': 'trizm1snas001',
                'destination-location': 'nlhoo2snas002:sv_home',
                'policy': 'XDPDefault',
                'lag-time': '73487',
                'destination-system': 'nlhoo2-scl020-01',
                'status': 'idle',
            },
        },
        [
            (0, 'Source-System: trizm1snas001'),
            (0, 'Destination-System: nlhoo2-scl020-01'),
            (0, 'Policy: XDPDefault'),
            (0, 'Status: idle'),
            (0, 'State: snapmirrored'),
            (0, 'Lag-Time: 20 h'),
        ],
    ),
])
def test_check_netapp_api_snapvault(check_manager, item, params, parsed, expected_result):
    check = check_manager.get_check('netapp_api_snapvault')
    assertCheckResultsEqual(
        CheckResult(check.run_check(item, params, parsed)),
        CheckResult(expected_result),
    )
