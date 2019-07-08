import pytest  # type: ignore
from checktestlib import BasicCheckResult, PerfValue, DiscoveryResult, assertDiscoveryResultsEqual

# since both nfsmounts and cifsmounts use the parse, inventory
# and check functions from network_fs.include unchanged we test
# both checks here.

pytestmark = pytest.mark.checks


@pytest.mark.parametrize(
    "info,discovery_expected,check_expected",
    [
        (  # no info
            [], [], (['', None, BasicCheckResult(3, ' not mounted', None)],)),
        (  # single mountpoint with data
            [[u'/ABCshare', u'ok', u'491520', u'460182', u'460182', u'65536']], [
                ('/ABCshare', {})
            ], [('/ABCshare', {}, BasicCheckResult(0, "6.4% used (1.91 GB of 30.00 GB)", None)),
                ('/ZZZshare', {}, BasicCheckResult(3, "/ZZZshare not mounted", None))]),
        (  # two mountpoints with empty data
            [[u'/AB', u'ok', u'-', u'-', u'-', u'-'], [u'/ABC', u'ok', u'-', u'-', u'-', u'-']], [
                ('/AB', {}), ('/ABC', {})
            ], [('/AB', {}, BasicCheckResult(0, "Mount seems OK", None)),
                ('/ABC', {}, BasicCheckResult(0, "Mount seems OK", None))]),
        (  # Mountpoint with spaces and permission denied
            [[u'/var/dba', u'export', u'Permission', u'denied'],
             [u'/var/dbaexport', u'ok', u'201326592', u'170803720', u'170803720', u'32768']], [
                 ('/var/dbaexport', {}), ('/var/dba export', {})
             ], [('/var/dba export', {}, BasicCheckResult(2, 'Permission denied', None)),
                 ('/var/dbaexport', {},
                  BasicCheckResult(0, '15.2% used (931.48 GB of 6.00 TB)', None))]),
        (  # with perfdata
            [[u'/PERFshare', u'ok', u'491520', u'460182', u'460182', u'65536']
            ], [('/PERFshare', {})], [('/PERFshare', {
                'has_perfdata': True
            },
                                       BasicCheckResult(0, "6.4% used (1.91 GB of 30.00 GB)", [
                                           PerfValue('fs_size', 491520 * 65536),
                                           PerfValue('fs_used', 491520 * 65536 - 460182 * 65536)
                                       ]))]),
        (  # state == 'hanging'
            [[u'/test', u'hanging', u'hanging', u'0', u'0', u'0', u'0']
            ], [('/test hanging', {})], [('/test hanging', {
                'has_perfdata': True
            }, BasicCheckResult(2, "Server not responding", None))]),
        (  # unknown state
            [[u'/test', u'unknown', u'unknown', u'1', u'1', u'1', u'1']], [('/test unknown', {})], [
                ('/test unknown', {}, BasicCheckResult(2, "Unknown state", None))
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
    assert (check_nfs.info['parse_function'].func_code.co_code ==
            check_cifs.info['parse_function'].func_code.co_code)
    assert (check_nfs.info['inventory_function'].func_code.co_code ==
            check_cifs.info['inventory_function'].func_code.co_code)
    assert (check_nfs.info['check_function'].func_code.co_code ==
            check_cifs.info['check_function'].func_code.co_code)

    parsed = check_nfs.run_parse(info)

    assertDiscoveryResultsEqual(
        check_nfs,
        DiscoveryResult(check_nfs.run_discovery(parsed)),  #
        DiscoveryResult(discovery_expected))

    for item, params, result_expected in check_expected:
        result = BasicCheckResult(*check_nfs.run_check(item, params, parsed))
        assert result == result_expected
