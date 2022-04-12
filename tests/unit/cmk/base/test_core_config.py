#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest  # type: ignore[import]
from contextlib import suppress
from pathlib import Path
import shutil

from testlib.base import Scenario

import cmk.utils.paths
import cmk.utils.version as cmk_version
from cmk.utils.exceptions import MKGeneralException
from cmk.utils.type_defs import CheckPluginName, ConfigSerial, LATEST_SERIAL

import cmk.base.config as config
import cmk.base.core_config as core_config
import cmk.base.nagios_utils
from cmk.base.core_factory import create_core
from cmk.base.check_utils import Service


def test_do_create_config_nagios(core_scenario):
    core_config.do_create_config(create_core("nagios"))

    assert Path(cmk.utils.paths.nagios_objects_file).exists()
    assert config.PackedConfigStore(LATEST_SERIAL).path.exists()


def test_active_check_arguments_basics():
    assert core_config.active_check_arguments("bla", "blub", u"args 123 -x 1 -y 2") \
        == u"args 123 -x 1 -y 2"

    assert core_config.active_check_arguments("bla", "blub", ["args", "123", "-x", "1", "-y", "2"]) \
        == "'args' '123' '-x' '1' '-y' '2'"

    assert core_config.active_check_arguments("bla", "blub", ["args", "1 2 3", "-d=2",
        "--hallo=eins", 9]) \
        == "'args' '1 2 3' '-d=2' '--hallo=eins' 9"

    with pytest.raises(MKGeneralException):
        core_config.active_check_arguments("bla", "blub", (1, 2))  # type: ignore[arg-type]


@pytest.mark.parametrize("pw", ["abc", "123", "x'äd!?", u"aädg"])
def test_active_check_arguments_password_store(monkeypatch, pw):
    monkeypatch.setattr(config, "stored_passwords", {"pw-id": {"password": pw,}})
    assert core_config.active_check_arguments("bla", "blub", ["arg1", ("store", "pw-id", "--password=%s"), "arg3"]) \
        == "--pwstore=2@11@pw-id 'arg1' '--password=%s' 'arg3'" % ("*" * len(pw))


def test_active_check_arguments_not_existing_password(capsys):
    assert core_config.active_check_arguments("bla", "blub", ["arg1", ("store", "pw-id", "--password=%s"), "arg3"]) \
        == "--pwstore=2@11@pw-id 'arg1' '--password=***' 'arg3'"
    stderr = capsys.readouterr().err
    assert "The stored password \"pw-id\" used by service \"blub\" on host \"bla\"" in stderr


def test_active_check_arguments_wrong_types():
    with pytest.raises(MKGeneralException):
        core_config.active_check_arguments("bla", "blub", 1)  # type: ignore[arg-type]

    with pytest.raises(MKGeneralException):
        core_config.active_check_arguments("bla", "blub", (1, 2))  # type: ignore[arg-type]


def test_active_check_arguments_str():
    assert core_config.active_check_arguments("bla", "blub",
                                              u"args 123 -x 1 -y 2") == 'args 123 -x 1 -y 2'


def test_active_check_arguments_list():
    assert core_config.active_check_arguments("bla", "blub", ["a", "123"]) == "'a' '123'"


def test_active_check_arguments_list_with_numbers():
    assert core_config.active_check_arguments("bla", "blub", [1, 1.2]) == "1 1.2"


def test_active_check_arguments_list_with_pwstore_reference():
    assert core_config.active_check_arguments(
        "bla", "blub",
        ["a", ("store", "pw1", "--password=%s")]) == "--pwstore=2@11@pw1 'a' '--password=***'"


def test_active_check_arguments_list_with_invalid_type():
    with pytest.raises(MKGeneralException):
        core_config.active_check_arguments("bla", "blub", [None])  # type: ignore[list-item]


def test_get_host_attributes(fixup_ip_lookup, monkeypatch):
    ts = Scenario().add_host("test-host", tags={"agent": "no-agent"})
    ts.set_option("host_labels", {
        "test-host": {
            "ding": "dong",
        },
    })
    config_cache = ts.apply(monkeypatch)

    expected_attrs = {
        '_ADDRESSES_4': '',
        '_ADDRESSES_6': '',
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

    if cmk_version.is_managed_edition():
        expected_attrs['_CUSTOMER'] = 'provider'

    attrs = core_config.get_host_attributes("test-host", config_cache)
    assert attrs == expected_attrs


@pytest.mark.usefixtures("config_load_all_checks")
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

    service = Service(CheckPluginName("cpu_loads"), None, "CPU load", {})
    service_spec = core_config.get_cmk_passive_service_attributes(config_cache, host_config,
                                                                  service, check_mk_attrs)
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
        assert isinstance(k, str)
        assert isinstance(v, str)


class TestHelperConfig:
    @pytest.fixture
    def serial(self):
        return "13"

    @pytest.fixture
    def store(self, serial):
        return core_config.HelperConfig(serial)

    def test_given_serial_path(self):
        store = core_config.HelperConfig(serial=ConfigSerial("42"))
        assert store.serial_path == cmk.utils.paths.core_helper_config_dir / "42"

    def test_create_success(self, store, serial):
        assert not store.serial_path.exists()
        assert not store.latest_path.exists()

        with store.create():
            assert store.serial_path.exists()
            assert not store.latest_path.exists()

        assert store.serial_path.exists()
        assert store.latest_path.exists()

    def test_create_success_replace_latest_link(self, store, serial):
        prev_serial = ConfigSerial("1")
        prev_path = cmk.utils.paths.core_helper_config_dir / prev_serial
        prev_path.mkdir(parents=True, exist_ok=True)
        store.latest_path.symlink_to(prev_serial)
        assert store.latest_path.exists()

        with store.create():
            assert store.serial_path.exists()

        assert store.serial_path.exists()
        assert store.latest_path.resolve().name == serial

    def test_create_no_latest_link_creation_on_failure(self, store, serial):
        assert not store.serial_path.exists()
        assert not store.latest_path.exists()

        with suppress(RuntimeError):
            with store.create():
                assert store.serial_path.exists()
                raise RuntimeError("boom")

        assert store.serial_path.exists()
        assert not store.latest_path.exists()

    def test_create_no_latest_link_replace_on_failure(self, store, serial):
        assert not store.serial_path.exists()
        assert not store.latest_path.exists()

        prev_serial = "13"
        prev_path = cmk.utils.paths.core_helper_config_dir / prev_serial
        prev_path.mkdir(parents=True, exist_ok=True)
        store.latest_path.symlink_to("13")
        assert store.latest_path.exists()

        with suppress(RuntimeError):
            with store.create():
                assert store.serial_path.exists()
                raise RuntimeError("boom")

        assert store.serial_path.exists()
        assert store.latest_path.resolve().name == prev_serial

    @pytest.fixture
    def nagios_core(self, monkeypatch):
        ts = Scenario().set_option("monitoring_core", "nagios")
        ts.apply(monkeypatch)

    @pytest.fixture
    def cmc_core(self, monkeypatch):
        ts = Scenario().set_option("monitoring_core", "cmc")
        ts.apply(monkeypatch)

    @pytest.fixture
    def prev_serial(self, serial):
        return ConfigSerial(str(int(serial) - 1))

    @pytest.fixture
    def prev_prev_serial(self, prev_serial):
        return ConfigSerial(str(int(prev_serial) - 1))

    @pytest.fixture
    def prev_helper_config(self, store, prev_serial, prev_prev_serial):
        assert not store.latest_path.exists()

        def _create_helper_config_dir(serial):
            path = cmk.utils.paths.core_helper_config_dir / serial
            path.mkdir(parents=True, exist_ok=True)
            with suppress(FileNotFoundError):
                store.latest_path.unlink()
            store.latest_path.symlink_to(serial)

        _create_helper_config_dir(prev_prev_serial)
        _create_helper_config_dir(prev_serial)

        assert cmk.utils.paths.make_helper_config_path(prev_prev_serial).exists()
        assert cmk.utils.paths.make_helper_config_path(prev_serial).exists()
        assert store.latest_path.exists()

    @pytest.mark.usefixtures("nagios_core", "prev_helper_config")
    def test_cleanup_with_nagios(self, store, prev_helper_config, prev_serial, prev_prev_serial):
        assert config.monitoring_core == "nagios"
        prev_path = cmk.utils.paths.make_helper_config_path(prev_serial)

        assert not store.serial_path.exists()
        with store.create():
            assert not cmk.utils.paths.make_helper_config_path(prev_prev_serial).exists()
            assert prev_path.exists()
            assert store.serial_path.exists()
            assert store.latest_path.resolve() == prev_path

        assert store.latest_path.resolve() == store.serial_path

    @pytest.mark.usefixtures("nagios_core", "prev_helper_config")
    def test_cleanup_with_broken_latest_link(self, store, prev_serial, prev_prev_serial):
        assert config.monitoring_core == "nagios"
        prev_path = cmk.utils.paths.make_helper_config_path(prev_serial)
        shutil.rmtree(prev_path)

        assert not prev_path.exists()
        assert store.latest_path.resolve() == prev_path

        assert not store.serial_path.exists()
        with store.create():
            assert not cmk.utils.paths.make_helper_config_path(prev_prev_serial).exists()
            assert not prev_path.exists()
            assert store.serial_path.exists()
            assert store.latest_path.resolve() == prev_path

        assert store.latest_path.resolve() == store.serial_path

    @pytest.mark.usefixtures("cmc_core", "prev_helper_config")
    def test_no_cleanup_with_microcore(self, store, prev_serial, prev_prev_serial):
        assert config.monitoring_core == "cmc"
        assert not store.serial_path.exists()
        with store.create():
            pass

        assert cmk.utils.paths.make_helper_config_path(prev_prev_serial).exists()
        assert cmk.utils.paths.make_helper_config_path(prev_serial).exists()
        assert store.serial_path.exists()
        assert store.latest_path.resolve() == store.serial_path


def test_new_helper_config_serial():
    assert core_config.new_helper_config_serial() == ConfigSerial("1")
    assert core_config.new_helper_config_serial() == ConfigSerial("2")
    assert core_config.new_helper_config_serial() == ConfigSerial("3")
