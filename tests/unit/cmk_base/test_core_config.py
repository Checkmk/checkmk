# encoding: utf-8
import pytest  # type: ignore
import socket
from testlib.base import Scenario

from cmk.utils.exceptions import MKGeneralException
import cmk_base.config as config
import cmk_base.core_config as core_config
import cmk_base.check_api as check_api


def test_active_check_arguments(mocker):
    with pytest.raises(MKGeneralException):
        core_config.active_check_arguments("bla", "blub", 1)

    with pytest.raises(MKGeneralException):
        core_config.active_check_arguments("bla", "blub", (1, 2))

    prepare_check_command = mocker.patch.object(config, "prepare_check_command")
    core_config.active_check_arguments("bla", "blub", u"args 123 -x 1 -y 2")
    assert prepare_check_command.called_once()


def test_get_host_attributes(fixup_ip_lookup, monkeypatch):
    ts = Scenario().add_host("test-host", tags={"agent": "no-agent"})
    ts.set_option("host_labels", {
        "test-host": {
            "ding": "dong",
        },
    })
    config_cache = ts.apply(monkeypatch)

    attrs = core_config.get_host_attributes("test-host", config_cache)
    assert attrs == {
        '_ADDRESS_4': '0.0.0.0',
        '_ADDRESS_6': '',
        '_ADDRESS_FAMILY': '4',
        '_FILENAME': '/wato/hosts.mk',
        '_TAGS': '/wato/ auto-piggyback ip-v4 ip-v4-only lan no-agent no-snmp prod site:unit',
        u'__TAG_address_family': u'ip-v4-only',
        u'__TAG_agent': u'no-agent',
        u'__TAG_criticality': u'prod',
        u'__TAG_ip-v4': u'ip-v4',
        u'__TAG_networking': u'lan',
        u'__TAG_piggyback': u'auto-piggyback',
        u'__TAG_site': u'unit',
        u'__TAG_snmp_ds': u'no-snmp',
        '__LABEL_ding': 'dong',
        '__LABELSOURCE_ding': 'explicit',
        'address': '0.0.0.0',
        'alias': 'test-host',
    }


@pytest.mark.parametrize("hostname,result", [
    ("localhost", {
        'check_interval': 1.0,
        'contact_groups': u'ding',
    }),
    ("blub", {
        'check_interval': 40.0
    }),
])
def test_get_cmk_passive_service_attributes(monkeypatch, hostname, result):
    config.load_checks(check_api.get_check_api_context, ["checks/cpu"])

    ts = Scenario().add_host("localhost")
    ts.add_host("blub")
    ts.set_option(
        "extra_service_conf", {
            "contact_groups": [(u'ding', ['localhost'], ["CPU load$"]),],
            "check_interval": [
                (40.0, ['blub'], ["Check_MK$"]),
                (33.0, ['localhost'], ["CPU load$"]),
            ],
        })
    config_cache = ts.apply(monkeypatch)
    host_config = config_cache.get_host_config(hostname)
    check_mk_attrs = core_config.get_service_attributes(hostname, "Check_MK", config_cache)

    service_spec = core_config.get_cmk_passive_service_attributes(config_cache, host_config,
                                                                  "CPU load", "cpu.loads", {},
                                                                  check_mk_attrs)
    assert service_spec == result


@pytest.mark.parametrize("tag_groups,result", [({
    "tg1": "val1",
    "tg2": "val1",
}, {
    u"__TAG_tg1": u"val1",
    u"__TAG_tg2": u"val1",
}), ({
    u"täg-113232_eybc": u"äbcdef"
}, {
    u"__TAG_täg-113232_eybc": u"äbcdef",
}), ({
    "a.d B/E u-f N_A": "a.d B/E u-f N_A"
}, {
    u"__TAG_a.d B/E u-f N_A": "a.d B/E u-f N_A",
})])
def test_get_tag_attributes(tag_groups, result):
    attributes = core_config._get_tag_attributes(tag_groups, "TAG")
    assert attributes == result
    for k, v in attributes.items():
        assert isinstance(k, unicode)
        assert isinstance(v, unicode)
