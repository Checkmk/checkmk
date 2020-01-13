import pytest  # type: ignore
from collections import namedtuple
from checktestlib import (
    BasicCheckResult,
    CheckResult,
    DiscoveryResult,
    PerfValue,
    assertCheckResultsEqual,
    assertDiscoveryResultsEqual,
)

# since both nfsmounts and cifsmounts use the parse, inventory
# and check functions from network_fs.include unchanged we test
# both checks here.

pytestmark = pytest.mark.checks

Size = namedtuple('Size', 'info,total,used,text')

size1 = Size(
    [u'491520', u'460182', u'460182', u'65536'],
    491520 * 65536,
    491520 * 65536 - 460182 * 65536,
    "6.38% used (1.91 of 30.00 GB), trend: 0.00 B / 24 hours",
)

size2 = Size(
    [u'201326592', u'170803720', u'170803720', u'32768'],
    None,  # not in use
    None,  # not in use
    "15.16% used (931.48 GB of 6.00 TB), trend: 0.00 B / 24 hours",
)


@pytest.mark.parametrize(
    "info,discovery_expected,check_expected",
    [
        (  # no info
            [], [], ()),
        (  # single mountpoint with data
            [[u'/ABCshare', u'ok'] + size1.info], [('/ABCshare', {})], [
                ('/ABCshare', {}, BasicCheckResult(0, size1.text, None)),
            ]),
        (  # two mountpoints with empty data
            [[u'/AB', u'ok', u'-', u'-', u'-', u'-'], [u'/ABC', u'ok', u'-', u'-', u'-', u'-']], [
                ('/AB', {}), ('/ABC', {})
            ], [('/AB', {}, BasicCheckResult(0, "Mount seems OK", None)),
                ('/ABC', {}, BasicCheckResult(0, "Mount seems OK", None))]),
        (  # Mountpoint with spaces and permission denied
            [[u'/var/dba', u'export', u'Permission',
              u'denied'], [u'/var/dbaexport', u'ok'] + size2.info], [
                  ('/var/dbaexport', {}), ('/var/dba export', {})
              ], [('/var/dba export', {}, BasicCheckResult(2, 'Permission denied', None)),
                  ('/var/dbaexport', {}, BasicCheckResult(0, size2.text, None))]),
        (  # with perfdata
            [[u'/PERFshare', u'ok'] + size1.info], [('/PERFshare', {})], [
                ('/PERFshare', {
                    'has_perfdata': True
                },
                 BasicCheckResult(0, size1.text, [
                     PerfValue('fs_used', size1.used, 0.8 * size1.total, 0.9 * size1.total, 0,
                               size1.total),
                     PerfValue('fs_size', size1.total),
                     PerfValue('fs_growth', 0),
                     PerfValue('fs_trend', 0, None, None, 0, 15534.459259259258),
                 ]))
            ]),
        (  # state == 'hanging'
            [[u'/test', u'hanging', u'hanging', u'0', u'0', u'0', u'0']
            ], [('/test hanging', {})], [('/test hanging', {
                'has_perfdata': True
            }, BasicCheckResult(2, "Server not responding", None))]),
        (  # unknown state
            [[u'/test', u'unknown', u'unknown', u'1', u'1', u'1', u'1']], [('/test unknown', {})], [
                ('/test unknown', {}, BasicCheckResult(2, "Unknown state: unknown", None))
            ]),
        (  # zero block size
            [[u'/test', u'perfdata', u'ok', u'0', u'460182', u'460182', u'0']],
            [('/test perfdata', {})],
            [(
                '/test perfdata',
                {
                    'has_perfdata': True
                },
                # TODO: display a better error message
                #BasicCheckResult(0, "server is responding", [PerfValue('fs_size', 0), PerfValue('fs_used', 0)]))]
                BasicCheckResult(2, "Stale fs handle", None))]),
    ])
def test_nfsmounts(check_manager, info, discovery_expected, check_expected):
    check_nfs = check_manager.get_check("nfsmounts")
    check_cifs = check_manager.get_check("cifsmounts")

    # assure that the code of both checks is identical
    assert (check_nfs.info['parse_function'].__code__.co_code ==
            check_cifs.info['parse_function'].__code__.co_code)
    assert (check_nfs.info['inventory_function'].__code__.co_code ==
            check_cifs.info['inventory_function'].__code__.co_code)
    assert (check_nfs.info['check_function'].__code__.co_code ==
            check_cifs.info['check_function'].__code__.co_code)

    parsed = check_nfs.run_parse(info)

    assertDiscoveryResultsEqual(
        check_nfs,
        DiscoveryResult(check_nfs.run_discovery(parsed)),  #
        DiscoveryResult(discovery_expected))

    for item, params, result_expected in check_expected:
        result = CheckResult(check_nfs.run_check(item, params, parsed))
        assertCheckResultsEqual(result, CheckResult([result_expected]))
