import pytest

pytestmark = pytest.mark.checks

esx_output = [[[u'hardware.cpuInfo.hz', u'2599999766'], [u'hardware.cpuInfo.numCpuCores', u'16'],
               [u'hardware.cpuInfo.numCpuPackages', u'2'],
               [u'hardware.cpuInfo.numCpuThreads', u'16'],
               [u'summary.quickStats.overallCpuUsage', u'7393']], None]


@pytest.mark.parametrize("info,params,result", [
    (esx_output, {}, (0, 3)),
    (esx_output, {
        'core_util_time_total': (0.0, 0, 0)
    }, (2, 4)),
])
def test_esx_vsphere_hostsystem_cpu_usage(check_manager, monkeypatch, info, params, result):
    max_state, len_result = result
    # To be indenpendent on NOW we use len(result)
    check = check_manager.get_check("esx_vsphere_hostsystem.cpu_usage")
    # Mock timestamp = get_item_state to zero
    # Then we calculate: high_load_duration = (this_time - timestamp)
    # Thereby we get     high_load_duration = NOW which is always greater than above levels
    #                    and we get an additional sub result
    monkeypatch.setitem(check.context, "get_item_state", lambda _, __: 1)
    check_result = list(check.run_check(None, params, info))
    assert len_result == len(check_result)
    assert max_state == max([entry[0] for entry in check_result])
