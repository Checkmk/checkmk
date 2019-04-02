# encoding: utf-8
import pytest  # type: ignore

from cmk.utils.exceptions import MKGeneralException
import cmk_base.config as config
import cmk_base.core_config as core_config


def test_active_check_arguments(mocker):
    with pytest.raises(MKGeneralException):
        core_config.active_check_arguments("bla", "blub", 1)

    with pytest.raises(MKGeneralException):
        core_config.active_check_arguments("bla", "blub", (1, 2))

    prepare_check_command = mocker.patch.object(config, "prepare_check_command")
    core_config.active_check_arguments("bla", "blub", u"args 123 -x 1 -y 2")
    assert prepare_check_command.called_once()


def test_get_host_attributes(monkeypatch):
    monkeypatch.setattr(config, "all_hosts", ["test-host|abc"])
    monkeypatch.setattr(config, "host_paths", {"test-host": "/"})
    monkeypatch.setattr(config, "host_tags", {
        "test-host": {
            "tag_group": "abc",
        },
    })

    config_cache = config.get_config_cache()
    config_cache.initialize()

    attrs = core_config.get_host_attributes("test-host", config_cache)
    assert attrs == {
        '_ADDRESS_4': '0.0.0.0',
        '_ADDRESS_6': '',
        '_ADDRESS_FAMILY': '4',
        '_FILENAME': '/',
        '_TAGS': 'abc',
        '__TAG_tag_group': 'abc',
        'address': '0.0.0.0',
        'alias': 'test-host',
    }


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
    attributes = core_config._get_tag_attributes(tag_groups)
    assert attributes == result
    for k, v in attributes.items():
        assert isinstance(k, unicode)
        assert isinstance(v, unicode)


def test_get_service_attributes(monkeypatch):
    monkeypatch.setattr(config, "all_hosts", ["test-host|abc"])
    monkeypatch.setattr(config, "host_paths", {"test-host": "/"})
    monkeypatch.setattr(config, "host_tags", {
        "test-host": {
            "tag_group": "abc",
        },
    })

    ruleset = [
        ([("criticality", "prod")], [], ["test-host"], ["CPU load$"], {}),
    ]
    monkeypatch.setattr(config, "service_tag_rules", ruleset)

    config_cache = config.get_config_cache()
    config_cache.initialize()

    attrs = core_config.get_service_attributes("test-host", "CPU load", config_cache)
    assert attrs == {
        '__TAG_criticality': 'prod',
    }


def test_custom_service_attributes_of(monkeypatch):
    attributes = core_config.custom_service_attributes_of("luluhost", "laladescr")
    assert attributes == {}

    monkeypatch.setattr(config, "all_hosts", ["luluhost"])
    monkeypatch.setattr(config, "host_paths", {"luluhost": "/"})
    monkeypatch.setattr(config, "custom_service_attributes", [
        ([('deng', '1')], [], config.ALL_HOSTS, config.ALL_SERVICES, {}),
        ([('ding', '2'), ('ding', '2a'),
          ('dong', '3')], [], config.ALL_HOSTS, config.ALL_SERVICES, {}),
    ])
    config.get_config_cache().initialize()

    attributes = core_config.custom_service_attributes_of("luluhost", "laladescr")
    assert attributes == {
        "deng": "1",
        "ding": "2a",
        "dong": "3",
    }
