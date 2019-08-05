import pytest  # type: ignore
from cmk_base.check_api import MKCounterWrapped
from checktestlib import CheckResult, assertCheckResultsEqual

pytestmark = pytest.mark.checks


def parsed_change(bandwidth_change):
    return [
        [
            None, '1', 'lo', '24', '', '1', '266045395', '97385', '0', '0', '0', '0', '266045395',
            '97385', '0', '0', '0', '0', '0', 'lo', '\x00\x00\x00\x00\x00\x00'
        ],
        [
            None, '2', 'docker0', '6', '', '2', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0',
            '0', '0', '0', 'docker0', '\x02B\x9d\xa42/'
        ],
        [
            None, '3', 'enp0s31f6', '6', '', '2', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0',
            '0', '0', '0', 'enp0s31f6', '\xe4\xb9z6\x93\xad'
        ],
        [
            None, '4', 'enxe4b97ab99f99', '6', '10000000', '2', '0', '0', '0', '0', '0', '0', '0',
            '0', '0', '0', '0', '0', '0', 'enxe4b97ab99f99', '\xe4\xb9z\xb9\x9f\x99'
        ],
        [
            None, '5', 'vboxnet0', '6', '10000000', '1', '0', '0', '0', '0', '0', '0', '20171',
            '113', '0', '0', '0', '0', '0', 'vboxnet0', "\n\x00'\x00\x00\x00"
        ],
        [
            None, '6', 'wlp2s0', '6', '', '1',
            str(346922243 + bandwidth_change), '244867', '0', '0', '0', '0',
            str(6570143 + 4 * bandwidth_change), '55994', '0', '0', '0', '0', '0', 'wlp2s0',
            'd]\x86\xe4P/'
        ],
    ], {}


DISCOVERY = [
    ('5', "%r" % {
        'state': ['1'],
        'speed': 10000000
    }),
    ('6', "%r" % {
        'state': ['1'],
        'speed': 0
    }),
]


@pytest.mark.parametrize('item, params, result', [
    ('5', {
        'errors': (0.01, 0.1),
        'speed': 10000000,
        'traffic': [('both', ('upper', ('perc', (5.0, 20.0))))],
        'state': ['1']
    }, [(
        0,
        '[vboxnet0] (up) MAC: 0A:00:27:00:00:00, 10 Mbit/s, In: 0.00 B/s (0.0%), Out: 0.00 B/s (0.0%)',
        [
            ('in', 0.0, 62500.0, 250000.0, 0, 1250000.0),
            ('inucast', 0.0, None, None, None, None),
            ('innucast', 0.0, None, None, None, None),
            ('indisc', 0.0, None, None, None, None),
            ('inerr', 0.0, 0.01, 0.1, None, None),
            ('out', 0.0, 62500.0, 250000.0, 0, 1250000.0),
            ('outucast', 0.0, None, None, None, None),
            ('outnucast', 0.0, None, None, None, None),
            ('outdisc', 0.0, None, None, None, None),
            ('outerr', 0.0, 0.01, 0.1, None, None),
            ('outqlen', 0, None, None, None, None),
        ],
    )]),
    ('6', {
        'errors': (0.01, 0.1),
        'speed': 100000000,
        'traffic': [('both', ('upper', ('perc', (5.0, 20.0))))],
        'state': ['1']
    }, [(
        2,
        '[wlp2s0] (up) MAC: 64:5D:86:E4:50:2F, assuming 100 Mbit/s, In: 781.25 kB/s (warn/crit at 610.35 kB/s/2.38 MB/s)(!) (6.4%), Out: 3.05 MB/s (warn/crit at 610.35 kB/s/2.38 MB/s)(!!) (25.6%)',
        [
            ('in', 800000.0, 625000.0, 2500000.0, 0, 12500000.0),
            ('inucast', 0.0, None, None, None, None),
            ('innucast', 0.0, None, None, None, None),
            ('indisc', 0.0, None, None, None, None),
            ('inerr', 0.0, 0.01, 0.1, None, None),
            ('out', 3200000.0, 625000.0, 2500000.0, 0, 12500000.0),
            ('outucast', 0.0, None, None, None, None),
            ('outnucast', 0.0, None, None, None, None),
            ('outdisc', 0.0, None, None, None, None),
            ('outerr', 0.0, 0.01, 0.1, None, None),
            ('outqlen', 0, None, None, None, None),
        ],
    )]),
])
def test_if_check(check_manager, monkeypatch, item, params, result):
    check = check_manager.get_check('lnx_if')
    assert check.run_discovery(parsed_change(0)) == DISCOVERY

    monkeypatch.setattr('time.time', lambda: 0)
    with pytest.raises(MKCounterWrapped):
        CheckResult(check.run_check(item, params, parsed_change(0)))

    monkeypatch.setattr('time.time', lambda: 5)
    output = check.run_check(item, params, parsed_change(4000000))

    assertCheckResultsEqual(CheckResult(output), CheckResult(result))
