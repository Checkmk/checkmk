import pytest
import ast
from testlib import cmk_path

# Mark all tests in this file as check related tests
pytestmark = pytest.mark.checks

@pytest.mark.parametrize("info,settings,items", [
    ([], [{}], []),
    ([['123', '456', '789'], ['1', 'instances:', 'A_B-C_1'],
      [u'-122', u'29370873405', u'5887351577', u'0', u'0', u'bulk_count'],
      [u'-110', u'5692885', u'5153077', u'0', u'0', u'bulk_count'],
      [u'-244', u'5018312', u'4921974', u'0', u'0', u'bulk_count'],
      [u'-58', u'674573', u'231103', u'0', u'0', u'bulk_count'],
      [u'10', u'10000000000', u'10000000000', u'100000', u'100000', u'large_rawcount'],
      [u'-246', u'20569013293', u'5685847946', u'0', u'0', u'bulk_count'],
      [u'14', u'4961765', u'4425455', u'0', u'0', u'bulk_count'],
      [u'16', u'4447', u'490897', u'0', u'0', u'bulk_count'],
      [u'18', u'52100', u'5622', u'0', u'0', u'large_rawcount'],
      [u'20', u'0', u'0', u'0', u'0', u'large_rawcount'],
      [u'22', u'0', u'0', u'0', u'0', u'large_rawcount'],
      [u'-4', u'8801860112', u'201503631', u'0', u'0', u'bulk_count'],
      [u'26', u'673929', u'230448', u'0', u'0', u'bulk_count'],
      [u'28', u'644', u'655', u'0', u'0', u'bulk_count'],
      [u'30', u'0', u'0', u'0', u'0', u'large_rawcount'],
      [u'32', u'0', u'0', u'0', u'0', u'large_rawcount'],
      [u'34', u'0', u'0', u'0', u'0', u'large_rawcount'],
      [u'1086', u'0', u'0', u'0', u'0', u'large_rawcount'],
      [u'1088', u'1', u'0', u'0', u'0', u'large_rawcount'],
      [u'1090', u'3734320', u'4166703', u'0', u'0', u'bulk_count'],
      [u'1092', u'0', u'0', u'0', u'0', u'bulk_count'],
      [u'1094', u'22618', u'22618', u'22618', u'22618', u'large_rawcount'],
      [u'Node', u'MACAddress', u'Name', u'NetConnectionID', u'NetConnectionStatus', u'Speed', u'GUID'],
      [u'NODE1 ', u' 00:00:00:00:00:00 ', u' A_B-C_1 ', u' Ethernet1-XYZ ', u' 2 ', u' 10000000000 ', u' {FOO-123-BAR}']],
      [{"use_alias": True}], ['Ethernet1-XYZ']),
])
def test_winperf_if_netconnection_id(check_manager, monkeypatch, info, settings, items):
    check = check_manager.get_check("winperf_if")
    monkeypatch.setitem(check.context, "host_extra_conf", lambda _, __: settings)
    monkeypatch.setitem(check.context, "_prepare_if_group_patterns_from_conf", lambda: {})
    parsed = check.run_parse(info)
    discovered_items = [e[0] for e in check.run_discovery(parsed)]
    assert discovered_items == items
