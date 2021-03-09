import os
import imp
import pytest

from testlib import repo_path

cisco_cpu_scan_functions = imp.load_source(
    'cisco_cpu_scan_functions.include',
    os.path.join(repo_path(), 'checks/cisco_cpu_scan_functions.include'))


@pytest.mark.parametrize(
    "oid_values, result",
    [
        # Has table 2
        ((True, True, True), False),
        ((True, False, True), True),
        ((True, True, False), False),
        # No table 2
        ((False, True, True), True),
        ((False, False, True), True),
        ((False, True, False), True),
    ])
def test_cisco_cpu_scan_functions_cisco_cpu(monkeypatch, oid_values, result):
    has_table_2, has_cpmCPUTotal5minRev, has_deprecated_cpmCPUTotal5min = oid_values

    monkeypatch.setattr(cisco_cpu_scan_functions, "_is_cisco", lambda oid: True)
    monkeypatch.setattr(cisco_cpu_scan_functions, "_is_cisco_nexus", lambda oid: False)
    monkeypatch.setattr(cisco_cpu_scan_functions, "_has_table_2", lambda oid: has_table_2)
    monkeypatch.setattr(cisco_cpu_scan_functions, "_has_cpmCPUTotal5minRev",
                        lambda oid: has_cpmCPUTotal5minRev)
    monkeypatch.setattr(cisco_cpu_scan_functions, "_has_deprecated_cpmCPUTotal5min",
                        lambda oid: has_deprecated_cpmCPUTotal5min)

    assert cisco_cpu_scan_functions.snmp_scan_cisco_cpu("MOCKED_OID_FUNC") == result
    assert cisco_cpu_scan_functions.snmp_scan_cisco_cpu_multiitem("MOCKED_OID_FUNC") == (not result)
