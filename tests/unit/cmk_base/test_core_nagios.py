# encoding: utf-8
# pylint: disable=redefined-outer-name
import itertools
from StringIO import StringIO

import pytest  # type: ignore
from testlib.base import Scenario
import six

import cmk_base.core_config as core_config
import cmk_base.core_nagios as core_nagios


def test_format_nagios_object():
    spec = {
        "use": "ding",
        "bla": u"däng",
        "check_interval": u"hüch",
        u"_HÄÄÄÄ": "XXXXXX_YYYY",
    }
    cfg = core_nagios._format_nagios_object("service", spec)
    assert isinstance(cfg, six.text_type)
    assert cfg == """define service {
  %-29s %s
  %-29s %s
  %-29s %s
  %-29s %s
}

""" % tuple(itertools.chain(*sorted(spec.items(), key=lambda x: x[0])))


@pytest.mark.parametrize("hostname,result", [
    ("localhost", {
        '_ADDRESS_4': '127.0.0.1',
        '_ADDRESS_6': '',
        '_ADDRESS_FAMILY': '4',
        '_TAGS': '/wato/ auto-piggyback cmk-agent ip-v4 ip-v4-only lan no-snmp prod site:unit tcp',
        u'__TAG_address_family': u'ip-v4-only',
        u'__TAG_agent': u'cmk-agent',
        u'__TAG_criticality': u'prod',
        u'__TAG_ip-v4': u'ip-v4',
        u'__TAG_networking': u'lan',
        u'__TAG_piggyback': u'auto-piggyback',
        u'__TAG_site': u'unit',
        u'__TAG_snmp_ds': u'no-snmp',
        u'__TAG_tcp': u'tcp',
        '_FILENAME': '/wato/hosts.mk',
        'address': '127.0.0.1',
        'alias': 'localhost',
        'check_command': 'check-mk-host-ping!-w 200.00,80.00% -c 500.00,100.00%',
        'host_name': 'localhost',
        'hostgroups': 'check_mk',
        'use': 'check_mk_host',
    }),
    ("host2", {
        '_ADDRESS_4': '0.0.0.0',
        '_ADDRESS_6': '',
        '_ADDRESS_FAMILY': '4',
        '_FILENAME': '/wato/hosts.mk',
        '_TAGS': '/wato/ auto-piggyback cmk-agent ip-v4 ip-v4-only lan no-snmp prod site:unit tcp',
        u'__TAG_address_family': u'ip-v4-only',
        u'__TAG_agent': u'cmk-agent',
        u'__TAG_criticality': u'prod',
        u'__TAG_ip-v4': u'ip-v4',
        u'__TAG_networking': u'lan',
        u'__TAG_piggyback': u'auto-piggyback',
        u'__TAG_site': u'unit',
        u'__TAG_snmp_ds': u'no-snmp',
        u'__TAG_tcp': u'tcp',
        'address': '0.0.0.0',
        'alias': u'lOCALhost',
        'check_command': 'check-mk-host-ping!-w 200.00,80.00% -c 500.00,100.00%',
        'host_name': 'host2',
        'hostgroups': 'check_mk',
        'use': 'check_mk_host',
    }),
    ("cluster1", {
        '_ADDRESS_4': '',
        '_ADDRESS_6': '',
        '_ADDRESS_FAMILY': '4',
        '_FILENAME': '/wato/hosts.mk',
        '_NODEIPS': '',
        '_NODEIPS_4': '',
        '_NODEIPS_6': '',
        '_NODENAMES': '',
        '_TAGS': '/wato/ auto-piggyback cmk-agent ip-v4 ip-v4-only lan no-snmp prod site:unit tcp',
        u'__TAG_address_family': u'ip-v4-only',
        u'__TAG_agent': u'cmk-agent',
        u'__TAG_criticality': u'prod',
        u'__TAG_ip-v4': u'ip-v4',
        u'__TAG_networking': u'lan',
        u'__TAG_piggyback': u'auto-piggyback',
        u'__TAG_site': u'unit',
        u'__TAG_snmp_ds': u'no-snmp',
        u'__TAG_tcp': u'tcp',
        'address': '0.0.0.0',
        'alias': 'cluster1',
        'check_command': 'check-mk-host-ping-cluster!-w 200.00,80.00% -c 500.00,100.00%',
        'host_name': 'cluster1',
        'hostgroups': 'check_mk',
        'parents': '',
        'use': 'check_mk_cluster',
    }),
    ("cluster2", {
        '_ADDRESS_4': '',
        '_ADDRESS_6': '',
        '_ADDRESS_FAMILY': '4',
        '_FILENAME': '/wato/hosts.mk',
        '_NODEIPS': '127.0.0.1 127.0.0.2',
        '_NODEIPS_4': '127.0.0.1 127.0.0.2',
        '_NODEIPS_6': '',
        '_NODENAMES': 'node1 node2',
        '_TAGS': '/wato/ auto-piggyback cmk-agent ip-v4 ip-v4-only lan no-snmp prod site:unit tcp',
        u'__TAG_address_family': u'ip-v4-only',
        u'__TAG_agent': u'cmk-agent',
        u'__TAG_criticality': u'prod',
        u'__TAG_ip-v4': u'ip-v4',
        u'__TAG_networking': u'lan',
        u'__TAG_piggyback': u'auto-piggyback',
        u'__TAG_site': u'unit',
        u'__TAG_snmp_ds': u'no-snmp',
        u'__TAG_tcp': u'tcp',
        'address': '0.0.0.0',
        'alias': u'CLUSTer',
        'check_command': 'check-mk-host-ping-cluster!-w 200.00,80.00% -c 500.00,100.00%',
        'host_name': 'cluster2',
        'hostgroups': 'check_mk',
        'parents': 'node1,node2',
        'use': 'check_mk_cluster',
    }),
    ("node1", {
        '_ADDRESS_4': '127.0.0.1',
        '_ADDRESS_6': '',
        '_ADDRESS_FAMILY': '4',
        '_FILENAME': '/wato/hosts.mk',
        '_TAGS': '/wato/ auto-piggyback cmk-agent ip-v4 ip-v4-only lan no-snmp prod site:unit tcp',
        u'__TAG_address_family': u'ip-v4-only',
        u'__TAG_agent': u'cmk-agent',
        u'__TAG_criticality': u'prod',
        u'__TAG_ip-v4': u'ip-v4',
        u'__TAG_networking': u'lan',
        u'__TAG_piggyback': u'auto-piggyback',
        u'__TAG_site': u'unit',
        u'__TAG_snmp_ds': u'no-snmp',
        u'__TAG_tcp': u'tcp',
        'address': '127.0.0.1',
        'alias': 'node1',
        'check_command': 'check-mk-host-ping!-w 200.00,80.00% -c 500.00,100.00%',
        'host_name': 'node1',
        'hostgroups': 'check_mk',
        'parents': 'switch',
        'use': 'check_mk_host',
    }),
])
def test_create_nagios_host_spec(hostname, result, monkeypatch):
    ts = Scenario().add_host("localhost")
    ts.add_host("host2")
    ts.add_cluster("cluster1")

    ts.add_cluster("cluster2", nodes=["node1", "node2"])
    ts.add_host("node1")
    ts.add_host("node2")
    ts.add_host("switch")
    ts.set_option("ipaddresses", {
        "node1": "127.0.0.1",
        "node2": "127.0.0.2",
    })

    ts.set_option("extra_host_conf", {
        "alias": [(u'lOCALhost', ['localhost']),],
    })

    ts.set_option(
        "extra_host_conf", {
            "alias": [
                (u'lOCALhost', ['host2']),
                (u'CLUSTer', ['cluster2']),
            ],
            "parents": [('switch', ['node1', 'node2']),],
        })

    outfile = StringIO()
    cfg = core_nagios.NagiosConfig(outfile, [hostname])

    config_cache = ts.apply(monkeypatch)
    host_attrs = core_config.get_host_attributes(hostname, config_cache)

    host_spec = core_nagios._create_nagios_host_spec(cfg, config_cache, hostname, host_attrs)
    assert host_spec == result
