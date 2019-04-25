# encoding: utf-8
# pylint: disable=redefined-outer-name
import itertools
from StringIO import StringIO

import pytest  # type: ignore
from testlib.base import Scenario

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
    assert isinstance(cfg, unicode)
    assert cfg == """define service {
  %-29s %s
  %-29s %s
  %-29s %s
  %-29s %s
}

""" % tuple(itertools.chain(*sorted(spec.items(), key=lambda x: x[0])))


def ts():
    ts1 = Scenario().add_host("localhost")
    result1 = {
        '_ADDRESS_4': '127.0.0.1',
        '_ADDRESS_6': '',
        '_ADDRESS_FAMILY': '4',
        '_TAGS': '',
        '_FILENAME': '/',
        'address': '127.0.0.1',
        'alias': 'localhost',
        'check_command': 'check-mk-host-ping!-w 200.00,80.00% -c 500.00,100.00%',
        'host_name': 'localhost',
        'hostgroups': 'check_mk',
        'use': 'check_mk_host',
    }

    yield ts1, result1

    ts2 = Scenario().add_host("localhost")
    ts2.set_option("extra_host_conf", {
        "alias": [(u'lOCALhost', ['localhost']),],
    })
    result2 = {
        '_ADDRESS_4': '127.0.0.1',
        '_ADDRESS_6': '',
        '_ADDRESS_FAMILY': '4',
        '_FILENAME': '/',
        '_TAGS': '',
        'address': '127.0.0.1',
        'alias': u'lOCALhost',
        'check_command': 'check-mk-host-ping!-w 200.00,80.00% -c 500.00,100.00%',
        'host_name': 'localhost',
        'hostgroups': 'check_mk',
        'use': 'check_mk_host',
    }

    yield ts2, result2

    ts3 = Scenario().add_cluster("localhost")
    result3 = {
        '_ADDRESS_4': '127.0.0.1',
        '_ADDRESS_6': '',
        '_ADDRESS_FAMILY': '4',
        '_FILENAME': '/',
        '_NODEIPS': '',
        '_NODEIPS_4': '',
        '_NODEIPS_6': '',
        '_NODENAMES': '',
        '_TAGS': '',
        'address': '127.0.0.1',
        'alias': 'localhost',
        'check_command': 'check-mk-host-ping!-w 200.00,80.00% -c 500.00,100.00%',
        'host_name': 'localhost',
        'hostgroups': 'check_mk',
        'parents': '',
        'use': 'check_mk_cluster',
    }

    yield ts3, result3

    ts4 = Scenario().add_cluster("localhost", nodes=["node1", "node2"])
    ts4.add_host("node1")
    ts4.add_host("node2")
    ts4.add_host("switch")
    ts4.set_option("ipaddresses", {
        "node1": "127.0.0.1",
        "node2": "127.0.0.2",
    })
    ts4.set_option("extra_host_conf", {
        "alias": [(u'lOCALhost', ['localhost']),],
        "parents": [('switch', ['node1', 'node2']),],
    })
    result4 = {
        '_ADDRESS_4': '127.0.0.1',
        '_ADDRESS_6': '',
        '_ADDRESS_FAMILY': '4',
        '_FILENAME': '/',
        '_NODEIPS': '127.0.0.1 127.0.0.2',
        '_NODEIPS_4': '127.0.0.1 127.0.0.2',
        '_NODEIPS_6': '',
        '_NODENAMES': 'node1 node2',
        '_TAGS': '',
        'address': '127.0.0.1',
        'alias': u'lOCALhost',
        'check_command': 'check-mk-host-ping!-w 200.00,80.00% -c 500.00,100.00%',
        'host_name': 'localhost',
        'hostgroups': 'check_mk',
        'parents': 'node1,node2',
        'use': 'check_mk_cluster',
    }

    yield ts4, result4


@pytest.mark.parametrize("ts,result", ts())
def test_create_nagios_host_spec(ts, result, monkeypatch):
    outfile = StringIO()
    cfg = core_nagios.NagiosConfig(outfile, ["localhost"])

    config_cache = ts.apply(monkeypatch)
    host_attrs = core_config.get_host_attributes("localhost", config_cache)

    host_spec = core_nagios._create_nagios_host_spec(cfg, config_cache, "localhost", host_attrs)
    assert host_spec == result

    if "node1" in config_cache.all_configured_hosts():
        host_attrs = core_config.get_host_attributes("node1", config_cache)
        host_spec = core_nagios._create_nagios_host_spec(cfg, config_cache, "node1", host_attrs)
        assert host_spec == {
            '_ADDRESS_4': '127.0.0.1',
            '_ADDRESS_6': '',
            '_ADDRESS_FAMILY': '4',
            '_FILENAME': '/',
            '_TAGS': '',
            'address': '127.0.0.1',
            'alias': 'node1',
            'check_command': 'check-mk-host-ping!-w 200.00,80.00% -c 500.00,100.00%',
            'host_name': 'node1',
            'hostgroups': 'check_mk',
            'parents': 'switch',
            'use': 'check_mk_host',
        }
