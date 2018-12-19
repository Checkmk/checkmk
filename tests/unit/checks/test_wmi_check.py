import pytest

from checktestlib import (
    DiscoveryResult,
    CheckResult,
    assertDiscoveryResultsEqual,
)

from cmk_base.check_api import MKCounterWrapped

pytestmark = pytest.mark.checks

info_wmi_timeout = [[u'WMItimeout']]

info_subsection_wmi_timeout = [
    [u'[system_perf]'],
    [u'WMItimeout'],
    [u'[computer_system]'],
    [u'name', u'unimportant', u'data'],
]


@pytest.mark.parametrize("check_name,info,expected", [
    ('wmi_webservices', info_wmi_timeout, []),
    ('wmi_cpuload', info_subsection_wmi_timeout, []),
])
def test_wmi_cpu_load_discovery(check_manager, check_name, info, expected):
    check = check_manager.get_check(check_name)
    discovery_result = DiscoveryResult(check.run_discovery(check.run_parse(info)))
    discovery_expected = DiscoveryResult(expected)
    assertDiscoveryResultsEqual(check, discovery_result, discovery_expected)


@pytest.mark.parametrize("check_name,info,expected", [
    ('wmi_webservices', info_wmi_timeout, None),
    ('wmi_cpuload', info_subsection_wmi_timeout, None),
])
def test_wmi_cpuload_timeout_exceptions(check_manager, check_name, info, expected):
    check = check_manager.get_check(check_name)
    with pytest.raises(MKCounterWrapped):
        CheckResult(check.run_check(None, {}, check.run_parse(info)))
