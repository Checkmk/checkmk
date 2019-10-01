import pytest  # type: ignore
from testlib import CheckManager
from testlib.base import Scenario
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

    CheckManager().load(["smart"])
    assert check_table.get_check_table(hostname) == expected_result
