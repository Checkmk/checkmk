import pytest

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
