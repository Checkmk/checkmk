# *--encoding: UTF-8--*
# yapf: disable
import pytest
from cmk_base.check_api import MKCounterWrapped
from checktestlib import (
    DiscoveryResult,
    CheckResult,
    assertDiscoveryResultsEqual,
    assertCheckResultsEqual,
    MockItemState,
)

pytestmark = pytest.mark.checks


INFO_MISSING_COUNTERS = [
    [None, '@docker_version_info', '{"PluginVersion": "0.1", "DockerPyVersion": "3.7.0", "ApiVersion": "1.38"}'],
    [None, '{"io_service_time_recursive": [], "sectors_recursive": [], "io_service_bytes_recursive": [], "io_serviced_recursive": [], "io_time_recursive": [], "names"    : {"7:9": "loop9", "8:0": "sda", "7:8": "loop8", "8:16": "sdb", "253:1": "dm-1", "253:0": "dm-0", "7:4": "loop4", "253:2": "dm-2", "7:2": "loop2", "7:3":     "loop3", "7:0": "loop0", "7:1": "loop1", "7:10": "loop10", "7:6": "loop6", "7:12": "loop12", "7:13": "loop13", "7:7": "loop7", "8:32": "sdc", "7:5": "loop    5", "7:11": "loop11"}, "time": 1568705427.380945, "io_queue_recursive": [], "io_merged_recursive": [], "io_wait_time_recursive": []}'],
]


def test_docker_container_diskstat_wrapped(check_manager):
    check = check_manager.get_check('docker_container_diskstat')
    parsed = check.run_parse(INFO_MISSING_COUNTERS)

    with pytest.raises(MKCounterWrapped):
        check.run_check("SUMMARY", {}, parsed)

    with MockItemState((0, 0)):
        # raise MKCounterWrapped anyway, because counters are missing in info
        with pytest.raises(MKCounterWrapped):
            check.run_check("SUMMARY", {}, parsed)


@pytest.mark.parametrize("info, discovery_expected", [
    (INFO_MISSING_COUNTERS, DiscoveryResult([("SUMMARY", {})])),
])
def test_docker_container_diskstat_discovery(check_manager, info, discovery_expected):
    check = check_manager.get_check('docker_container_diskstat')
    parsed = check.run_parse(info)
    discovery_actual = DiscoveryResult(check.run_discovery(parsed))
    assertDiscoveryResultsEqual(check, discovery_actual, discovery_expected)
