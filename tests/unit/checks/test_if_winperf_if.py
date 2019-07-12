import pytest

from checktestlib import (
    BasicCheckResult,
    CheckResult,
    DiscoveryResult,
    PerfValue,
    assertCheckResultsEqual,
    assertDiscoveryResultsEqual,
)

# Mark all tests in this file as check related tests
pytestmark = pytest.mark.checks


@pytest.mark.parametrize("info,settings,items", [
    ([], [{}], []),
    ([[u'1527487554.76', u'510']], [{}], []),
    (
        [
            ['123', '456', '789'],
            ['1', 'instances:', 'A_B-C_1'],
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
                u'Node', u'MACAddress', u'Name', u'NetConnectionID', u'NetConnectionStatus',
                u'Speed', u'GUID'
            ],
            [
                u'NODE1 ', u' 00:00:00:00:00:00 ', u' A_B-C_1 ', u' Ethernet1-XYZ ', u' 2 ',
                u' 10000000000 ', u' {FOO-123-BAR}'
            ],
        ],
        [{
            "use_alias": True
        }],
        ['Ethernet1-XYZ'],
    ),
    ([[u'1559837585.63', u'510', u'2929686'], [u'1', u'instances:', u'vmxnet3_Ethernet_Adapter'],
      [u'-122', u'38840302775', u'bulk_count'], [u'-110', u'206904763', u'bulk_count'],
      [u'-244', u'173589803', u'bulk_count'], [u'-58', u'33314960', u'bulk_count'],
      [u'10', u'10000000000', u'large_rawcount'], [u'-246', u'21145988302', u'bulk_count'],
      [u'14', u'36886547', u'bulk_count'], [u'16', u'136703256', u'bulk_count'],
      [u'18', u'0', u'large_rawcount'], [u'20', u'0', u'large_rawcount'],
      [u'22', u'0', u'large_rawcount'], [u'-4', u'17694314473', u'bulk_count'],
      [u'26', u'33127032', u'bulk_count'], [u'28', u'187928', u'bulk_count'],
      [u'30', u'0', u'large_rawcount'], [u'32', u'0', u'large_rawcount'],
      [u'34', u'0', u'large_rawcount'], [u'1086', u'0', u'large_rawcount'],
      [u'1088', u'0', u'large_rawcount'], [u'1090', u'0', u'bulk_count'],
      [u'1092', u'0', u'bulk_count'], [u'1094', u'0', u'large_rawcount']], [{}], ['1']),
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
    ('HPE Ethernet 1Gb 4-port 331i Adapter', "{'state': ['1'], 'speed': 1000000000}"),
    ('HPE Ethernet 1Gb 4-port 331i Adapter 2', "{'state': ['1'], 'speed': 1000000000}"),
    ('HPE Ethernet 1Gb 4-port 331i Adapter 3', "{'state': ['1'], 'speed': 1000000000}"),
    ('HPE Ethernet 1Gb 4-port 331i Adapter 4', "{'state': ['1'], 'speed': 1000000000}"),
    (u'LAN',
     "{'aggregate': {'item_type': 'description', 'group_patterns': {'non-existent-testhost': {'items': [], 'iftype': '6'}}}, 'state': ['1'], 'speed': 2000000000}"
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
    assertDiscoveryResultsEqual(check, DiscoveryResult(sorted(expected_discovery)),
                                DiscoveryResult(sorted(actual_discovery)))


winperf_if_section_44 = [
    [u'Node', u'MACAddress', u'Name', u'NetConnectionID', u'NetConnectionStatus'],
    [u'NODE1', u'', u'WAN Miniport (L2TP)', u'', u''],
    [u'NODE1', u'', u'WAN Miniport (SSTP)', u'', u''],
    [u'NODE1', u'', u'WAN Miniport (IKEv2)', u'', u''],
    [u'NODE1', u'', u'WAN Miniport (PPTP)', u'', u''],
    [u'NODE1', u'', u'WAN Miniport (PPPOE)', u'', u''],
    [u'NODE1', u'', u'WAN Miniport (IP)', u'', u''],
    [u'NODE1', u'', u'WAN Miniport (IPv6)', u'', u''],
    [u'NODE1', u'', u'WAN Miniport (Network Monitor)', u'', u''],
    [u'NODE1', u'', u'Hyper-V Virtual Ethernet Adapter', u'', u''],
    [u'NODE1', u'', u'Microsoft Kernel Debug Network Adapter', u'', u''],
    [u'NODE1', u'', u'RAS Async Adapter', u'', u''],
    [u'NODE1', u'', u'Broadcom NetXtreme Gigabit Ethernet', u'SLOT 3 Port 1', u'4'],
    [u'NODE1', u'', u'Broadcom NetXtreme Gigabit Ethernet', u'SLOT 3 Port 2', u'4'],
    [
        u'NODE1', u'AA:AA:AA:AA:AA:AA', u'Broadcom BCM57800 NetXtreme II 10 GigE (NDIS VBD Client)',
        u'NIC2', u'2'
    ],
    [u'NODE1', u'', u'Broadcom NetXtreme Gigabit Ethernet', u'SLOT 3 Port 4', u'4'],
    [u'NODE1', u'', u'Broadcom NetXtreme Gigabit Ethernet', u'SLOT 3 Port 3', u'4'],
    [u'NODE1', u'', u'Broadcom BCM57800 NetXtreme II 1 GigE (NDIS VBD Client)', u'NIC4', u'4'],
    [u'NODE1', u'', u'Broadcom BCM57800 NetXtreme II 1 GigE (NDIS VBD Client)', u'NIC3', u'4'],
    [
        u'NODE1', u'AA:AA:AA:AA:AA:AA', u'Broadcom BCM57800 NetXtreme II 10 GigE (NDIS VBD Client)',
        u'NIC1', u'2'
    ],
    [u'NODE1', u'', u'Microsoft ISATAP Adapter', u'', u''],
    [u'NODE1', u'', u'Microsoft ISATAP Adapter #2', u'', u''],
    [u'NODE1', u'', u'Microsoft ISATAP Adapter #3', u'', u''],
    [u'NODE1', u'', u'Microsoft ISATAP Adapter #4', u'', u''],
    [u'NODE1', u'', u'Microsoft Network Adapter Multiplexor Default Miniport', u'', u''],
    [
        u'NODE1', u'AA:AA:AA:AA:AA:AA', u'Microsoft Network Adapter Multiplexor Driver', u'10GTeam',
        u'2'
    ],
    [u'NODE1', u'', u'Hyper-V Virtual Switch Extension Adapter', u'', u''],
    [u'NODE1', u'AA:AA:AA:AA:AA:AA', u'Hyper-V Virtual Ethernet Adapter #2', u'Management', u'2'],
    [u'NODE1', u'AA:AA:AA:AA:AA:AA', u'Hyper-V Virtual Ethernet Adapter #3', u'CSV', u'2'],
    [u'NODE1', u'AA:AA:AA:AA:AA:AA', u'Hyper-V Virtual Ethernet Adapter #4', u'Live', u'2'],
    [u'NODE1', u'AA:AA:AA:AA:AA:AA', u'Hyper-V Virtual Ethernet Adapter #5', u'iSCSI1', u'2'],
    [u'NODE1', u'AA:AA:AA:AA:AA:AA', u'Hyper-V Virtual Ethernet Adapter #6', u'iSCSI2', u'2'],
    [u'NODE1', u'', u'Microsoft ISATAP Adapter #5', u'', u''],
    [u'NODE1', u'AA:AA:AA:AA:AA:AA', u'Microsoft Failover Cluster Virtual Adapter', u'', u''],
    [u'NODE1', u'', u'Microsoft ISATAP Adapter #6', u'', u''],
]

winperf_if_section = [
    [u'1418225545.73', u'510'],
    [
        u'8',
        u'instances:',
        u'Broadcom_ABC123_NetXtreme_123_GigE_[Client1]__138',
        u'Broadcom_ABC456_NetXtreme_456_GigE_[Client2]__137',
        u'isatap.{A1A1A1A1-A1A1-A1A1-A1A1-A1A1A1A1A1A1}',
        u'isatap.{B1B1B1B1-B1B1-B1B1-B1B1-B1B1B1B1B1B1}',
        u'isatap.{C1C1C1C1-C1C1-C1C1-C1C1-C1C1C1C1C1C1}',
        u'isatap.{D1D1D1D1-D1D1-D1D1-D1D1-D1D1D1D1D1D1}',
        u'isatap.{E1E1E1E1-E1E1-E1E1-E1E1-E1E1E1E1E1E1}',
        u'isatap.{F1F1F1F1-F1F1-F1F1-F1F1-F1F1F1F1F1F1}',
    ],
    [u'-122', u'3361621296', u'97386123', u'0', u'0', u'0', u'0', u'0', u'0', u'bulk_count'],
    [u'-110', u'3437962', u'13245121', u'0', u'0', u'0', u'0', u'0', u'0', u'bulk_count'],
    [u'-244', u'2946102', u'6234996', u'0', u'0', u'0', u'0', u'0', u'0', u'bulk_count'],
    [u'-58', u'491860', u'7010125', u'0', u'0', u'0', u'0', u'0', u'0', u'bulk_count'],
    [
        u'10', u'1410065408', u'1410065408', u'100000', u'100000', u'100000', u'100000', u'100000',
        u'100000', u'large_rawcount'
    ],
    [u'-246', u'3188924403', u'3975676452', u'0', u'0', u'0', u'0', u'0', u'0', u'bulk_count'],
    [u'14', u'1707835', u'4996570', u'0', u'0', u'0', u'0', u'0', u'0', u'bulk_count'],
    [u'16', u'1237965', u'1238278', u'0', u'0', u'0', u'0', u'0', u'0', u'bulk_count'],
    [u'18', u'302', u'148', u'0', u'0', u'0', u'0', u'0', u'0', u'large_rawcount'],
    [u'20', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'large_rawcount'],
    [u'22', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'large_rawcount'],
    [u'-4', u'172696893', u'416676967', u'0', u'0', u'0', u'0', u'0', u'0', u'bulk_count'],
    [u'26', u'484056', u'7001439', u'0', u'0', u'0', u'0', u'0', u'0', u'bulk_count'],
    [u'28', u'7804', u'8686', u'0', u'0', u'0', u'0', u'0', u'0', u'bulk_count'],
    [u'30', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'large_rawcount'],
    [u'32', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'large_rawcount'],
    [u'34', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'large_rawcount'],
    [u'1086', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'large_rawcount'],
    [u'1088', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'large_rawcount'],
    [u'1090', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'bulk_count'],
    [u'1092', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'bulk_count'],
    [u'1094', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'large_rawcount'],
]


@pytest.mark.parametrize(
    "info",
    [
        winperf_if_section + winperf_if_section_44,
        #winperf_if_section_44 + winperf_if_section,
    ])
def test_winperf_if_parse_sections(check_manager, info):
    check = check_manager.get_check('winperf_if')
    check.run_parse(info)


discovery_winperf_if_group_patterns = [
    (
        u'Broadcom ABC456 NetXtreme 456 GigE [Client2] 137',
        {
            'state': ['1'],
            'speed': 1410065408
        },
    ),
    (
        u'Broadcom ABC123 NetXtreme 123 GigE [Client1] 138',
        {
            'state': ['1'],
            'speed': 1410065408
        },
    ),
    (
        'isatap',
        {
            'aggregate': {
                'item_type': 'description',
                'group_patterns': {
                    'test-host': {
                        'items': [
                            u'isatap.{A1A1A1A1-A1A1-A1A1-A1A1-A1A1A1A1A1A1}',
                            u'isatap.{B1B1B1B1-B1B1-B1B1-B1B1-B1B1B1B1B1B1}',
                            u'isatap.{C1C1C1C1-C1C1-C1C1-C1C1-C1C1C1C1C1C1}',
                            u'isatap.{D1D1D1D1-D1D1-D1D1-D1D1-D1D1D1D1D1D1}',
                            u'isatap.{E1E1E1E1-E1E1-E1E1-E1E1-E1E1E1E1E1E1}',
                            u'isatap.{F1F1F1F1-F1F1-F1F1-F1F1-F1F1F1F1F1F1}',
                        ]
                    }
                }
            },
            'state': ['1'],
            'speed': 600000,
        },
    ),
    (
        'Broadcom',
        {
            'aggregate': {
                'item_type': 'description',
                'group_patterns': {
                    'test-host': {
                        'items': [
                            u'Broadcom ABC123 NetXtreme 123 GigE [Client1] 138',
                            u'Broadcom ABC456 NetXtreme 456 GigE [Client2] 137'
                        ],
                    },
                },
            },
            'state': ['1'],
            'speed': 2820130816,
        },
    ),
]

check_results_winperf_if_group_patterns = [
    CheckResult([(
        0,
        "[2] (Connected) 1.41 Gbit/s",
        [],
    )]),
    CheckResult([(
        0,
        "[1] (Connected) 1.41 Gbit/s",
        [],
    )]),
    CheckResult([(
        0,
        "Teaming Status (up), Members: [isatap.{F1F1F1F1-F1F1-F1F1-F1F1-F1F1F1F1F1F1} (Connected), isatap.{E1E1E1E1-E1E1-E1E1-E1E1-E1E1E1E1E1E1} (Connected), isatap.{D1D1D1D1-D1D1-D1D1-D1D1-D1D1D1D1D1D1} (Connected), isatap.{C1C1C1C1-C1C1-C1C1-C1C1-C1C1C1C1C1C1} (Connected), isatap.{B1B1B1B1-B1B1-B1B1-B1B1-B1B1B1B1B1B1} (Connected), isatap.{A1A1A1A1-A1A1-A1A1-A1A1-A1A1A1A1A1A1} (Connected)] 600.0 Kbit/s",
        [],
    )]),
    CheckResult([(
        0,
        "Teaming Status (up), Members: [Broadcom ABC456 NetXtreme 456 GigE [Client2] 137 (Connected), Broadcom ABC123 NetXtreme 123 GigE [Client1] 138 (Connected)] 2.82 Gbit/s",
        [],
    )]),
]


@pytest.mark.parametrize(
    "settings,group_patterns,info,expected_discovery,expected_check_results",
    [
        (
            [{
                'use_desc': True
            }],
            {
                'Broadcom': {
                    'group_patterns': {
                        'test-host': {
                            'items': [
                                u'Broadcom ABC123 NetXtreme 123 GigE [Client1] 138',
                                u'Broadcom ABC456 NetXtreme 456 GigE [Client2] 137'
                            ],
                        },
                    },
                    'group_presence': 'separate',  # discover group interfaces additionally
                    'group_type': 'single_host',
                },
                'isatap': {
                    'group_patterns': {
                        'test-host': {
                            'items': [
                                u'isatap.{A1A1A1A1-A1A1-A1A1-A1A1-A1A1A1A1A1A1}',
                                u'isatap.{B1B1B1B1-B1B1-B1B1-B1B1-B1B1B1B1B1B1}',
                                u'isatap.{C1C1C1C1-C1C1-C1C1-C1C1-C1C1C1C1C1C1}',
                                u'isatap.{D1D1D1D1-D1D1-D1D1-D1D1-D1D1D1D1D1D1}',
                                u'isatap.{E1E1E1E1-E1E1-E1E1-E1E1-E1E1E1E1E1E1}',
                                u'isatap.{F1F1F1F1-F1F1-F1F1-F1F1-F1F1F1F1F1F1}',
                            ],
                        },
                    },
                    'group_presence': 'instead',  # only discover group interfaces
                    'group_type': 'single_host'
                }
            },
            winperf_if_section,
            discovery_winperf_if_group_patterns,
            check_results_winperf_if_group_patterns,
        ),
    ],
)
def test_winperf_if_inventory_group_patterns(check_manager, monkeypatch, settings, group_patterns,
                                             info, expected_discovery, expected_check_results):
    check = check_manager.get_check("winperf_if")
    monkeypatch.setitem(check.context, "host_name", lambda: "test-host")
    monkeypatch.setitem(check.context, "host_extra_conf", lambda _, __: settings)
    monkeypatch.setitem(check.context, "_prepare_if_group_patterns_from_conf",
                        lambda: group_patterns)
    parsed = check.run_parse(info)

    actual_discovery = check.run_discovery(parsed)
    assertDiscoveryResultsEqual(check, DiscoveryResult(sorted(expected_discovery)),
                                DiscoveryResult(sorted(actual_discovery)))

    # check if grouped interfaces return the "Teaming Status" and "Members" of the group
    for (item, params), expected_result in zip(expected_discovery, expected_check_results):
        actual_result = CheckResult(check.run_check(item, params, parsed))
        assertCheckResultsEqual(actual_result, expected_result)


def winperf_if_teaming_parsed(time, out_octets):
    return (
        time,
        [
            ((u'DAG-NET', '8'), u'Intel[R] Ethernet 10G 2P X520 Adapter 4', '6', 10000000000,
             ('1', 'Connected'), 145209040, 0, 0, 2099072, 0, 0, out_octets, 0, 0, 0, 0, 0, 0,
             u'SLOT 4 Port 2 DAG', '\xa06\x9f\xb0\xb3f'),
            ((u'DAG-NET', '3'), u'Intel[R] Ethernet 10G 2P X520 Adapter 2', '6', 10000000000,
             ('1',
              'Connected'), 410232131549, 376555354, 0, 225288, 0, 0, 1171662236873 + out_octets,
             833538016, 0, 63489, 0, 0, 0, u'SLOT 6 Port 1 DAG', '\xa06\x9f\xb0\xa3`'),
        ],
        {},
    )


def test_winperf_if_teaming_performance_data(check_manager, monkeypatch):
    check = check_manager.get_check("winperf_if")
    monkeypatch.setitem(check.context, "host_extra_conf", lambda _, __: [{}])
    monkeypatch.setitem(check.context, "_prepare_if_group_patterns_from_conf", lambda: {})

    params_single = {'state': ['1'], 'speed': 10000000000}
    params_teamed = {
        'aggregate': {
            'item_type': 'index',
            'group_patterns': {
                'non-existent-testhost': {
                    'items': [],
                    'iftype': '6'
                }
            }
        },
        'state': ['1'],
        'speed': 20000000000
    }

    # Initalize counters
    monkeypatch.setattr('time.time', lambda: 0)
    parsed = winperf_if_teaming_parsed(time=0, out_octets=0)
    CheckResult(check.run_check(u'3', params_single, parsed))
    CheckResult(check.run_check(u'8', params_single, parsed))
    CheckResult(check.run_check(u'DAG-NET', params_teamed, parsed))

    # winperf_if should use the timestamp of the parsed data. To check
    # that it does not use time.time by accident we set it to 20s instead
    # of 10s. If winperf_if would now use time.time the Out value would only
    # be 512 MB/s instead of 1 GB/s.
    monkeypatch.setattr('time.time', lambda: 20)
    parsed = winperf_if_teaming_parsed(time=10, out_octets=1024 * 1024 * 1024 * 10)
    result_3 = CheckResult(check.run_check(u'3', params_single, parsed))
    result_8 = CheckResult(check.run_check(u'8', params_single, parsed))
    result_dag_net = CheckResult(check.run_check(u'DAG-NET', params_teamed, parsed))

    assert result_3 == CheckResult([
        BasicCheckResult(
            0,
            u'[SLOT 6 Port 1 DAG] (Connected) MAC: A0:36:9F:B0:A3:60, 10.00 Gbit/s, In: 0.00 B/s (0.0%), Out: 1.00 GB/s (85.9%)',
            [
                PerfValue('in', 0.0, None, None, 0, 1250000000.0),
                PerfValue('inucast', 0.0, None, None, None, None),
                PerfValue('innucast', 0.0, None, None, None, None),
                PerfValue('indisc', 0.0, None, None, None, None),
                PerfValue('inerr', 0.0, None, None, None, None),
                PerfValue('out', 1073741824.0, None, None, 0, 1250000000.0),
                PerfValue('outucast', 0.0, None, None, None, None),
                PerfValue('outnucast', 0.0, None, None, None, None),
                PerfValue('outdisc', 0.0, None, None, None, None),
                PerfValue('outerr', 0.0, None, None, None, None),
                PerfValue('outqlen', 0, None, None, None, None),
                PerfValue('in', 0.0, None, None, None, None),
                PerfValue('out', 1073741824.0, None, None, None, None)
            ])
    ])
    assert result_8 == CheckResult([
        BasicCheckResult(
            0,
            u'[SLOT 4 Port 2 DAG] (Connected) MAC: A0:36:9F:B0:B3:66, 10.00 Gbit/s, In: 0.00 B/s (0.0%), Out: 1.00 GB/s (85.9%)',
            [
                PerfValue('in', 0.0, None, None, 0, 1250000000.0),
                PerfValue('inucast', 0.0, None, None, None, None),
                PerfValue('innucast', 0.0, None, None, None, None),
                PerfValue('indisc', 0.0, None, None, None, None),
                PerfValue('inerr', 0.0, None, None, None, None),
                PerfValue('out', 1073741824.0, None, None, 0, 1250000000.0),
                PerfValue('outucast', 0.0, None, None, None, None),
                PerfValue('outnucast', 0.0, None, None, None, None),
                PerfValue('outdisc', 0.0, None, None, None, None),
                PerfValue('outerr', 0.0, None, None, None, None),
                PerfValue('outqlen', 0, None, None, None, None),
                PerfValue('in', 0.0, None, None, None, None),
                PerfValue('out', 1073741824.0, None, None, None, None)
            ])
    ])
    assert result_dag_net == CheckResult([
        BasicCheckResult(
            0,
            'Teaming Status (up), Members: [8 (Connected), 3 (Connected)] 20.00 Gbit/s, In: 0.00 B/s (0.0%), Out: 2.00 GB/s (85.9%)',
            [
                PerfValue('in', 0.0, None, None, 0, 2500000000.0),
                PerfValue('inucast', 0.0, None, None, None, None),
                PerfValue('innucast', 0.0, None, None, None, None),
                PerfValue('indisc', 0.0, None, None, None, None),
                PerfValue('inerr', 0.0, None, None, None, None),
                PerfValue('out', 2147483648.0, None, None, 0, 2500000000.0),
                PerfValue('outucast', 0.0, None, None, None, None),
                PerfValue('outnucast', 0.0, None, None, None, None),
                PerfValue('outdisc', 0.0, None, None, None, None),
                PerfValue('outerr', 0.0, None, None, None, None),
                PerfValue('outqlen', 0, None, None, None, None),
                PerfValue('in', 0.0, None, None, None, None),
                PerfValue('out', 2147483648.0, None, None, None, None)
            ])
    ])
