import pytest

from testlib import Check
from checktestlib import assertEqual, DiscoveryResult, assertDiscoveryResultsEqual


@pytest.mark.parametrize("info, expected_discovery_result", [([None], [(None, {})])])
@pytest.mark.usefixtures("config_load_all_checks")
def test_zypper_discovery(info, expected_discovery_result):
    check_zypper = Check("zypper")
    discovery_result = DiscoveryResult(check_zypper.run_discovery(info))
    assertDiscoveryResultsEqual("zypper", discovery_result,
                                DiscoveryResult(expected_discovery_result))


@pytest.mark.parametrize("info, expected_parse_result",
                         [([
                             [
                                 "ERROR: An error occurred",
                             ],
                         ], (3, "ERROR: An error occurred")),
                          ([
                              [
                                  "0 patches needed. ( 0 security patches )",
                              ],
                          ], (0, "0 updates")),
                          ([[
                              'Updates for openSUSE 12.1 12.1-1.4 ',
                              ' openSUSE-2012-324 ',
                              ' 1       ',
                              ' recommended ',
                              ' needed ',
                              " util-linux: make mount honor 'noexec' and 'user' option",
                          ], [
                              '1 ',
                              ' apache ',
                              ' package ',
                              ' (any)',
                          ], [
                              '2 ',
                              ' mysql  ',
                              ' package ',
                              ' (any)',
                          ]], (1, "1 updates (recommended: 1(!)), 2 locks(!)")),
                          ([[
                              '4 patches needed (2 security patches)',
                          ],
                            [
                                'SLE11-SDK-SP4-Updates ',
                                ' sdksp4-apache2-mod_fcgid-12653 ',
                                ' 1       ',
                                ' security    ',
                                ' needed',
                            ],
                            [
                                'SLES11-SP4-Updates    ',
                                ' slessp4-mysql-12847            ',
                                ' 1       ',
                                ' security    ',
                                ' needed',
                            ],
                            [
                                'SLES11-SP4-Updates    ',
                                ' slessp4-timezone-12844         ',
                                ' 1       ',
                                ' recommended ',
                                ' needed',
                            ],
                            [
                                'SLES11-SP4-Updates    ',
                                ' slessp4-wget-12826             ',
                                ' 1       ',
                                ' recommended ',
                                ' needed',
                            ]], (2, "4 updates (recommended: 2(!), security: 2(!!))")),
                          ([[
                              'SLES12-SP1-Updates ',
                              ' SUSE-SLE-SERVER-12-SP1-2016-1150 ',
                              ' recommended ',
                              ' low       ',
                              ' ---         ',
                              ' needed ',
                              ' Recommended update for release-notes-sles# SLES12-SP1-Updates',
                          ]], (1, "1 updates (recommended: 1(!))")),
                          ([[
                              'SLES12-SP1-Updates ',
                              ' SUSE-SLE-SERVER-12-SP1-2016-1150 ',
                              ' not relevant ',
                              ' low       ',
                              ' ---         ',
                              ' needed ',
                              ' Recommended update for release-notes-sles# SLES12-SP1-Updates',
                          ]], (0, "1 updates (not relevant: 1)"))])
@pytest.mark.usefixtures("config_load_all_checks")
def test_zypper_check(info, expected_parse_result):
    assertEqual(Check("zypper").run_check(None, {}, info), expected_parse_result)
