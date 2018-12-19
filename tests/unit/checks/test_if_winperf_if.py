import pytest

from checktestlib import DiscoveryResult

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
      [
          u'Node', u'MACAddress', u'Name', u'NetConnectionID', u'NetConnectionStatus', u'Speed',
          u'GUID'
      ],
      [
          u'NODE1 ', u' 00:00:00:00:00:00 ', u' A_B-C_1 ', u' Ethernet1-XYZ ', u' 2 ',
          u' 10000000000 ', u' {FOO-123-BAR}'
      ]], [{
          "use_alias": True
      }], ['Ethernet1-XYZ']),
])
def test_winperf_if_netconnection_id(check_manager, monkeypatch, info, settings, items):
    check = check_manager.get_check("winperf_if")
    monkeypatch.setitem(check.context, "host_extra_conf", lambda _, __: settings)
    monkeypatch.setitem(check.context, "_prepare_if_group_patterns_from_conf", lambda: {})
    parsed = check.run_parse(info)
    discovered_items = [e[0] for e in check.run_discovery(parsed)]
    assert discovered_items == items


info_winperf_if_teaming = [
    [u'1542018413.59', u'510', u'2341040'],
    [
        u'4',
        u'instances:',
        u'HPE_Ethernet_1Gb_4-port_331i_Adapter__3',
        u'HPE_Ethernet_1Gb_4-port_331i_Adapter__4',
        u'HPE_Ethernet_1Gb_4-port_331i_Adapter',
        u'HPE_Ethernet_1Gb_4-port_331i_Adapter__2',
    ],
    [u'-122', u'201612106', u'187232778', u'200985680546908', u'969308895925', u'bulk_count'],
    [u'-110', u'2938459', u'2713782', u'141023109713', u'7143818358', u'bulk_count'],
    [u'-244', u'2920458', u'2695781', u'133889346630', u'9159143', u'bulk_count'],
    [u'-58', u'18001', u'18001', u'7133763083', u'7134659215', u'bulk_count'],
    [u'10', u'1000000000', u'1000000000', u'1000000000', u'1000000000', u'large_rawcount'],
    [u'-246', u'189182492', u'174803164', u'200050287945665', u'730174911', u'bulk_count'],
    [u'14', u'0', u'0', u'133879714188', u'131929', u'bulk_count'],
    [u'16', u'2920458', u'2695781', u'8946694', u'9027210', u'bulk_count'],
    [u'18', u'0', u'0', u'685748', u'4', u'large_rawcount'],
    [u'20', u'0', u'0', u'0', u'0', u'large_rawcount'],
    [u'22', u'0', u'0', u'0', u'0', u'large_rawcount'],
    [u'-4', u'12429614', u'12429614', u'935392601243', u'968578721014', u'bulk_count'],
    [u'26', u'0', u'0', u'7133594582', u'7134655376', u'bulk_count'],
    [u'28', u'18001', u'18001', u'168501', u'3839', u'bulk_count'],
    [u'30', u'0', u'0', u'0', u'0', u'large_rawcount'],
    [u'32', u'0', u'0', u'0', u'0', u'large_rawcount'],
    [u'34', u'0', u'0', u'0', u'0', u'large_rawcount'],
    [u'1086', u'0', u'0', u'0', u'0', u'large_rawcount'],
    [u'1088', u'0', u'0', u'0', u'0', u'large_rawcount'],
    [u'1090', u'0', u'0', u'0', u'0', u'bulk_count'],
    [u'1092', u'0', u'0', u'0', u'0', u'bulk_count'],
    [u'1094', u'0', u'0', u'0', u'0', u'large_rawcount'],
    [u'[teaming_start]'],
    [
        u'TeamName', u'TeamingMode', u'LoadBalancingAlgorithm', u'MemberMACAddresses',
        u'MemberNames', u'MemberDescriptions', u'Speed', u'GUID'
    ],
    [
        u'LAN ', u'SwitchIndependent ', u'Dynamic ', u'38:63:BB:44:D0:24;38:63:BB:44:D0:25',
        u'nic1;nic2',
        u'HPE Ethernet 1Gb 4-port 331i Adapter;HPE Ethernet 1Gb 4-port 331i Adapter #2',
        u'1000000000;1000000000',
        u'{4DA62AA0-8163-459C-9ACE-95B1E729A7DD};{FEF2305A-57FD-4AEC-A817-C082565B6AA7}'
    ],
    [u'[teaming_end]'],
    [
        u'Node', u'MACAddress', u'Name', u'NetConnectionID', u'NetConnectionStatus', u'Speed',
        u'GUID'
    ],
    [
        u'S5EXVM318 ', u' 38:63:BB:44:D0:26 ', u' HPE Ethernet 1Gb 4-port 331i Adapter #3 ',
        u' nic3-vl302 ', u' 2 ', u' 1000000000 ', u' {5FBD3455-980D-4AD6-BDEE-79B42B7BBDBC}'
    ],
    [
        u'S5EXVM318 ', u' 38:63:BB:44:D0:27 ', u' HPE Ethernet 1Gb 4-port 331i Adapter #4 ',
        u' nic4-vl303 ', u' 2 ', u' 1000000000 ', u' {8A1D9DD0-DF30-46CD-87FC-ACB13A5AB2BA}'
    ],
    [
        u'S5EXVM318 ', u' 38:63:BB:44:D0:24 ', u' HPE Ethernet 1Gb 4-port 331i Adapter ', u' nic1 ',
        u' 2 ', u'  ', u' {4DA62AA0-8163-459C-9ACE-95B1E729A7DD}'
    ],
    [
        u'S5EXVM318 ', u' 38:63:BB:44:D0:25 ', u' HPE Ethernet 1Gb 4-port 331i Adapter ', u' nic2 ',
        u' 2 ', u'  ', u' {FEF2305A-57FD-4AEC-A817-C082565B6AA7}'
    ],
    [
        u'S5EXVM318 ', u' 38:63:BB:44:D0:24 ', u' Microsoft Network Adapter Multiplexor Driver ',
        u' LAN ', u' 2 ', u' 2000000000 ', u' {69DCC9F6-FD98-474C-87F8-DD1023C6117C}'
    ],
]

discovery_winperf_if_teaming = [
    ('HPE Ethernet 1Gb 4-port 331i Adapter 3', "{'state': ['1'], 'speed': 1000000000}"),
    ('HPE Ethernet 1Gb 4-port 331i Adapter 4', "{'state': ['1'], 'speed': 1000000000}"),
    (u'LAN',
     "{'aggregate': {'item_type': 'description', 'group_patterns': {'unknown': {'items': [], 'iftype': '6'}}}, 'state': ['1'], 'speed': 2000000000}"
    ),
]


@pytest.mark.parametrize(
    "settings,info,expected_discovery",
    [
        (
            [{
                'use_desc': True
            }],
            info_winperf_if_teaming,
            discovery_winperf_if_teaming,
        ),
    ],
)
def test_winperf_if_inventory_teaming(check_manager, monkeypatch, settings, info,
                                      expected_discovery):
    check = check_manager.get_check("winperf_if")
    monkeypatch.setitem(check.context, "host_extra_conf", lambda _, __: settings)
    monkeypatch.setitem(check.context, "_prepare_if_group_patterns_from_conf", lambda: {})
    parsed = check.run_parse(info)
    actual_discovery = check.run_discovery(parsed)
    assert DiscoveryResult(expected_discovery) == DiscoveryResult(actual_discovery)
