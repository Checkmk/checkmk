import pytest  # type: ignore
# No stub file
from testlib.base import Scenario  # type: ignore[import]
import cmk_base.config as config
import cmk_base.check_api as check_api
import cmk_base.check_table as check_table
from cmk_base.check_utils import Service


# TODO: This misses a lot of cases
# - different get_check_table arguments
@pytest.mark.parametrize(
    "hostname,expected_result",
    [
        ("empty-host", {}),
        # Skip the autochecks automatically for ping hosts
        ("ping-host", {}),
        ("no-autochecks", {
            ('smart.temp', '/dev/sda'): Service(
                check_plugin_name="smart.temp",
                item=u"/dev/sda",
                parameters={'levels': (35, 40)},
                description=u'Temperature SMART /dev/sda',
            ),
        }),
        # Static checks overwrite the autocheck definitions
        ("autocheck-overwrite", {
            ('smart.temp', '/dev/sda'): Service(
                check_plugin_name="smart.temp",
                item=u"/dev/sda",
                parameters={'levels': (35, 40)},
                description=u'Temperature SMART /dev/sda',
            ),
            ('smart.temp', '/dev/sdb'): Service(
                check_plugin_name='smart.temp',
                item=u'/dev/sdb',
                parameters={'is_autocheck': True},
                description=u'Temperature SMART /dev/sdb',
            ),
        }),
        ("ignore-not-existing-checks", {}),
        ("ignore-disabled-rules", {
            ('smart.temp', 'ITEM2'): Service(
                check_plugin_name='smart.temp',
                item=u"ITEM2",
                parameters={'levels': (35, 40)},
                description=u'Temperature SMART ITEM2',
            ),
        }),
        ("static-check-overwrite", {
            ('smart.temp', '/dev/sda'): Service(
                check_plugin_name="smart.temp",
                item=u"/dev/sda",
                parameters={
                    'levels': (35, 40),
                    'rule': 1
                },
                description=u'Temperature SMART /dev/sda',
            )
        }),
        ("node1", {
            ('smart.temp', 'auto-not-clustered'): Service(
                check_plugin_name="smart.temp",
                item=u"auto-not-clustered",
                parameters={},
                description=u'Temperature SMART auto-not-clustered',
            ),
            ('smart.temp', 'static-node1'): Service(check_plugin_name="smart.temp",
                                                    item=u"static-node1",
                                                    parameters={'levels': (35, 40)},
                                                    description=u'Temperature SMART static-node1'),
        }),
        ("cluster1", {
            ('smart.temp', 'static-cluster'): Service(
                check_plugin_name="smart.temp",
                item=u"static-cluster",
                parameters={'levels': (35, 40)},
                description=u'Temperature SMART static-cluster',
            ),
            ('smart.temp', 'auto-clustered'): Service(
                check_plugin_name="smart.temp",
                item=u"auto-clustered",
                parameters={'levels': (35, 40)},
                description=u'Temperature SMART auto-clustered',
            ),
        }),
    ])
def test_get_check_table(monkeypatch, hostname, expected_result):
    autochecks = {
        "ping-host": [Service("smart.temp", "bla", u'Temperature SMART bla', {})],
        "autocheck-overwrite": [
            Service('smart.temp', '/dev/sda', u'Temperature SMART /dev/sda',
                    {"is_autocheck": True}),
            Service('smart.temp', '/dev/sdb', u'Temperature SMART /dev/sdb',
                    {"is_autocheck": True}),
        ],
        "ignore-not-existing-checks": [Service("bla.blub", "ITEM", u'Blub ITEM', {}),],
        "node1": [
            Service("smart.temp", "auto-clustered", u"Temperature SMART auto-clustered", {}),
            Service("smart.temp", "auto-not-clustered", u'Temperature SMART auto-not-clustered', {})
        ],
    }

    ts = Scenario().add_host(hostname, tags={"criticality": "test"})
    ts.add_host("ping-host", tags={"agent": "no-agent"})
    ts.add_host("node1")
    ts.add_cluster("cluster1", nodes=["node1"])
    ts.set_option(
        "static_checks",
        {
            "temperature": [
                (('smart.temp', '/dev/sda', {}), [], ["no-autochecks", "autocheck-overwrite"]),
                (('blub.bla', 'ITEM', {}), [], ["ignore-not-existing-checks"]),
                (('smart.temp', 'ITEM1', {}), [], ["ignore-disabled-rules"], {
                    "disabled": True
                }),
                (('smart.temp', 'ITEM2', {}), [], ["ignore-disabled-rules"]),
                (('smart.temp', '/dev/sda', {
                    "rule": 1
                }), [], ["static-check-overwrite"]),
                (('smart.temp', '/dev/sda', {
                    "rule": 2
                }), [], ["static-check-overwrite"]),
                (('smart.temp', 'static-node1', {}), [], ["node1"]),
                (('smart.temp', 'static-cluster', {}), [], ["cluster1"]),
            ]
        },
    )
    ts.set_ruleset("clustered_services", [
        ([], ['node1'], [u'Temperature SMART auto-clustered$']),
    ])
    config_cache = ts.apply(monkeypatch)
    monkeypatch.setattr(config_cache, "get_autochecks_of", lambda h: autochecks.get(h, []))

    config.load_checks(check_api.get_check_api_context, ["checks/smart"])
    assert check_table.get_check_table(hostname) == expected_result


@pytest.mark.parametrize("hostname, expected_result", [
    ("mgmt-board-ipmi", [("mgmt_ipmi_sensors", "TEMP X")]),
    ("ipmi-host", [("ipmi_sensors", "TEMP Y")]),
])
def test_get_check_table_of_mgmt_boards(monkeypatch, hostname, expected_result):
    autochecks = {
        "mgmt-board-ipmi": [
            Service("mgmt_ipmi_sensors", "TEMP X", "Management Interface: IPMI Sensor TEMP X", {}),
        ],
        "ipmi-host": [Service("ipmi_sensors", "TEMP Y", "IPMI Sensor TEMP Y", {}),]
    }

    ts = Scenario().add_host("mgmt-board-ipmi",
                             tags={
                                 'piggyback': 'auto-piggyback',
                                 'networking': 'lan',
                                 'address_family': 'no-ip',
                                 'criticality': 'prod',
                                 'snmp_ds': 'no-snmp',
                                 'site': 'heute',
                                 'agent': 'no-agent'
                             })
    ts.add_host("ipmi-host",
                tags={
                    'piggyback': 'auto-piggyback',
                    'networking': 'lan',
                    'agent': 'cmk-agent',
                    'criticality': 'prod',
                    'snmp_ds': 'no-snmp',
                    'site': 'heute',
                    'address_family': 'ip-v4-only'
                })
    ts.set_option("management_protocol", {"mgmt-board-ipmi": "ipmi"})

    config_cache = ts.apply(monkeypatch)
    monkeypatch.setattr(config_cache, "get_autochecks_of", lambda h: autochecks.get(h, []))

    config.load_checks(check_api.get_check_api_context,
                       ["checks/mgmt_ipmi_sensors", "checks/ipmi_sensors"])
    assert check_table.get_check_table(hostname).keys() == expected_result


# verify static check outcome, including timespecific and None params
@pytest.mark.parametrize(
    "hostname,expected_result",
    [
        ("df_host", [("df", "/snap/core/9066")]),
        # old format, without TimespecificParamList
        ("df_host_1", [("df", "/snap/core/9067")]),
        # params = None
        ("df_host_2", [("df", "/snap/core/9068")]),
    ])
def test_get_check_table_of_static_check(monkeypatch, hostname, expected_result):
    static_checks = {
        "df_host": [
            Service('df', '/snap/core/9066', u'Filesystem /snap/core/9066', [{
                'tp_values': [('24X7', {
                    'inodes_levels': None
                })],
                'tp_default_value': {}
            }, {
                'trend_range': 24,
                'show_levels': 'onmagic',
                'inodes_levels': (10.0, 5.0),
                'magic_normsize': 20,
                'show_inodes': 'onlow',
                'levels': (80.0, 90.0),
                'show_reserved': False,
                'levels_low': (50.0, 60.0),
                'trend_perfdata': True
            }]),
        ],
        "df_host_1": [
            Service(
                'df', '/snap/core/9067', u'Filesystem /snap/core/9067', {
                    'trend_range': 24,
                    'show_levels': 'onmagic',
                    'inodes_levels': (10.0, 5.0),
                    'magic_normsize': 20,
                    'show_inodes': 'onlow',
                    'levels': (80.0, 90.0),
                    'tp_default_value': {
                        'levels': (87.0, 90.0)
                    },
                    'show_reserved': False,
                    'tp_values': [('24X7', {
                        'inodes_levels': None
                    })],
                    'levels_low': (50.0, 60.0),
                    'trend_perfdata': True
                })
        ],
        "df_host_2": [Service('df', '/snap/core/9068', u'Filesystem /snap/core/9068', None)],
    }

    ts = Scenario().add_host(hostname, tags={"criticality": "test"})
    ts.add_host("df_host")
    ts.add_host("df_host_1")
    ts.add_host("df_host_2")
    ts.set_option(
        "static_checks",
        {
            "filesystem": [
                (('df', '/snap/core/9066', [{
                    'tp_values': [('24X7', {
                        'inodes_levels': None
                    })],
                    'tp_default_value': {}
                }, {
                    'trend_range': 24,
                    'show_levels': 'onmagic',
                    'inodes_levels': (10.0, 5.0),
                    'magic_normsize': 20,
                    'show_inodes': 'onlow',
                    'levels': (80.0, 90.0),
                    'show_reserved': False,
                    'levels_low': (50.0, 60.0),
                    'trend_perfdata': True
                }]), [], ["df_host"]),
                (('df', '/snap/core/9067', [{
                    'tp_values': [('24X7', {
                        'inodes_levels': None
                    })],
                    'tp_default_value': {}
                }, {
                    'trend_range': 24,
                    'show_levels': 'onmagic',
                    'inodes_levels': (10.0, 5.0),
                    'magic_normsize': 20,
                    'show_inodes': 'onlow',
                    'levels': (80.0, 90.0),
                    'show_reserved': False,
                    'levels_low': (50.0, 60.0),
                    'trend_perfdata': True
                }]), [], ["df_host_1"]),
                (('df', '/snap/core/9068', None), [], ["df_host_2"]),
            ],
        },
    )

    config_cache = ts.apply(monkeypatch)
    monkeypatch.setattr(config_cache, "get_autochecks_of", lambda h: static_checks.get(h, []))

    config.load_checks(check_api.get_check_api_context, ["checks/df"])
    assert list(check_table.get_check_table(hostname).keys()) == expected_result


@pytest.mark.parametrize("check_group_parameters", [
    {},
    {
        'levels': (4, 5, 6, 7),
    },
])
def test_check_table__get_static_check_entries(monkeypatch, check_group_parameters):
    hostname = "hostname"
    static_parameters = {
        'levels': (1, 2, 3, 4),
    }
    static_checks = {
        "ps": [(('ps', 'item', static_parameters), [], [hostname], {})],
    }

    ts = Scenario().add_host(hostname)
    ts.set_option("static_checks", static_checks)

    ts.set_ruleset("checkgroup_parameters", {
        'ps': [(check_group_parameters, [hostname], [], {})],
    })

    config_cache = ts.apply(monkeypatch)

    host_config = config_cache.get_host_config(hostname)
    static_check_parameters = [
        service.parameters for service in check_table.HostCheckTable(
            config_cache, host_config)._get_static_check_entries(host_config)
    ]

    entries = config._get_checkgroup_parameters(
        config_cache,
        hostname,
        "ps",
        "item",
        "Process item",
    )

    assert len(entries) == 1
    assert entries[0] == check_group_parameters

    assert len(static_check_parameters) == 1
    static_check_parameter = static_check_parameters[0]
    assert static_check_parameter == static_parameters
