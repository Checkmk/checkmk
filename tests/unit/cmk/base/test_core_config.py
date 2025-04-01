#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import shutil
from collections.abc import Mapping
from pathlib import Path

import pytest
from pytest import MonkeyPatch

from tests.testlib.base import Scenario

import cmk.utils.config_path
import cmk.utils.paths
import cmk.utils.version as cmk_version
from cmk.utils import password_store
from cmk.utils.config_path import ConfigPath, LATEST_CONFIG, VersionedConfigPath
from cmk.utils.hostaddress import HostAddress, HostName
from cmk.utils.labels import Labels
from cmk.utils.rulesets.ruleset_matcher import LabelSources
from cmk.utils.tags import TagGroupID, TagID

from cmk.checkengine.checking import CheckPluginName, ConfiguredService
from cmk.checkengine.parameters import TimespecificParameters

import cmk.base.config as config
import cmk.base.core_config as core_config
import cmk.base.nagios_utils
from cmk.base.config import ConfigCache, ObjectAttributes
from cmk.base.core_config import (
    CollectedHostLabels,
    get_labels_from_attributes,
    read_notify_host_file,
    write_notify_host_file,
)
from cmk.base.core_factory import create_core


@pytest.fixture(name="config_path")
def fixture_config_path():
    ConfigPath.ROOT.mkdir(parents=True, exist_ok=True)
    try:
        yield ConfigPath.ROOT
    finally:
        shutil.rmtree(ConfigPath.ROOT)


@pytest.fixture(name="core_scenario")
def fixture_core_scenario(monkeypatch):
    ts = Scenario()
    ts.add_host(HostName("test-host"))
    ts.set_option("ipaddresses", {"test-host": "127.0.0.1"})
    ts.set_ruleset_bundle(
        "active_checks",
        {
            "norris": [
                {
                    "value": {
                        "description": "My active check",
                        "oh-god-this-is-nested": {"password": ("explicit", "p4ssw0rd!")},
                    },
                    "condition": {},
                    "id": "1",
                }
            ]
        },
    )
    return ts.apply(monkeypatch)


@pytest.mark.skip(reason="CMK-22671")
def test_do_create_config_nagios(
    core_scenario: ConfigCache, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(config, "get_resource_macros", lambda *_: {})
    core_config.do_create_config(
        create_core("nagios"),
        core_scenario,
        all_hosts=[HostName("test-host")],
        duplicates=(),
    )

    assert Path(cmk.utils.paths.nagios_objects_file).exists()
    assert config.PackedConfigStore.from_serial(LATEST_CONFIG).path.exists()


@pytest.mark.skip(reason="CMK-22671")
def test_do_create_config_nagios_collects_passwords(
    core_scenario: ConfigCache, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(config, "get_resource_macros", lambda *_: {})  # file IO :-(

    password_store.save(passwords := {"stored-secret": "123"}, password_store.password_store_path())

    core_store = password_store.core_password_store_path(LATEST_CONFIG)
    assert not password_store.load(core_store)

    core_config.do_create_config(
        create_core("nagios"),
        core_scenario,
        all_hosts=[HostName("test-host")],
        duplicates=(),
    )

    assert password_store.load(core_store) == passwords


def test_get_host_attributes(monkeypatch: MonkeyPatch) -> None:
    ts = Scenario()
    ts.add_host(HostName("test-host"), tags={TagGroupID("agent"): TagID("no-agent")})
    ts.set_option(
        "host_labels",
        {
            "test-host": {
                "ding": "dong",
            },
        },
    )
    config_cache = ts.apply(monkeypatch)

    expected_attrs = {
        "_ADDRESSES_4": "",
        "_ADDRESSES_6": "",
        "_ADDRESS_4": "0.0.0.0",
        "_ADDRESS_6": "",
        "_ADDRESS_FAMILY": "4",
        "_FILENAME": "/wato/hosts.mk",
        "_TAGS": "/wato/ auto-piggyback ip-v4 ip-v4-only lan no-agent no-snmp prod site:unit",
        "__TAG_address_family": "ip-v4-only",
        "__TAG_agent": "no-agent",
        "__TAG_criticality": "prod",
        "__TAG_ip-v4": "ip-v4",
        "__TAG_networking": "lan",
        "__TAG_piggyback": "auto-piggyback",
        "__TAG_site": "unit",
        "__TAG_snmp_ds": "no-snmp",
        "__LABEL_ding": "dong",
        "__LABEL_cmk/site": "unit",
        "__LABELSOURCE_cmk/site": "discovered",
        "__LABELSOURCE_ding": "explicit",
        "address": "0.0.0.0",
        "alias": "test-host",
    }

    if cmk_version.edition() is cmk_version.Edition.CME:
        expected_attrs["_CUSTOMER"] = "provider"

    assert config_cache.get_host_attributes(HostName("test-host")) == expected_attrs


@pytest.mark.usefixtures("fix_register")
@pytest.mark.parametrize(
    "hostname,result",
    [
        (
            HostName("localhost"),
            {
                "check_interval": 1.0,
                "contact_groups": "ding",
            },
        ),
        (HostName("blub"), {"check_interval": 40.0}),
    ],
)
def test_get_cmk_passive_service_attributes(
    monkeypatch: pytest.MonkeyPatch, hostname: HostName, result: ObjectAttributes
) -> None:
    ts = Scenario()
    ts.add_host(HostName("localhost"))
    ts.add_host(HostName("blub"))
    ts.set_option(
        "extra_service_conf",
        {
            "contact_groups": [
                {
                    "id": "01",
                    "condition": {
                        "service_description": [{"$regex": "CPU load$"}],
                        "host_name": ["localhost"],
                    },
                    "options": {},
                    "value": "ding",
                },
            ],
            "check_interval": [
                {
                    "id": "02",
                    "condition": {
                        "service_description": [{"$regex": "Check_MK$"}],
                        "host_name": ["blub"],
                    },
                    "options": {},
                    "value": 40.0,
                },
                {
                    "id": "03",
                    "condition": {
                        "service_description": [{"$regex": "CPU load$"}],
                        "host_name": ["localhost"],
                    },
                    "options": {},
                    "value": 33.0,
                },
            ],
        },
    )
    config_cache = ts.apply(monkeypatch)
    check_mk_attrs = core_config.get_service_attributes(hostname, "Check_MK", config_cache)

    service = ConfiguredService(
        check_plugin_name=CheckPluginName("cpu_loads"),
        item=None,
        description="CPU load",
        parameters=TimespecificParameters(),
        discovered_parameters={},
        service_labels={},
        is_enforced=False,
    )
    service_spec = core_config.get_cmk_passive_service_attributes(
        config_cache, hostname, service, check_mk_attrs
    )
    assert service_spec == result


@pytest.mark.parametrize(
    "tag_groups,result",
    [
        (
            {
                "tg1": "val1",
                "tg2": "val1",
            },
            {
                "__TAG_tg1": "val1",
                "__TAG_tg2": "val1",
            },
        ),
        (
            {"täg-113232_eybc": "äbcdef"},
            {
                "__TAG_täg-113232_eybc": "äbcdef",
            },
        ),
        (
            {"a.d B/E u-f N_A": "a.d B/E u-f N_A"},
            {
                "__TAG_a.d B/E u-f N_A": "a.d B/E u-f N_A",
            },
        ),
    ],
)
def test_get_tag_attributes(
    tag_groups: Mapping[TagGroupID, TagID] | Labels | LabelSources,
    result: ObjectAttributes,
) -> None:
    attributes = ConfigCache._get_tag_attributes(tag_groups, "TAG")
    assert attributes == result
    for k, v in attributes.items():
        assert isinstance(k, str)
        assert isinstance(v, str)


@pytest.mark.parametrize("ipaddress", [None, HostAddress("127.0.0.1")])
def test_template_translation(
    ipaddress: HostAddress | None, monkeypatch: pytest.MonkeyPatch
) -> None:
    template = "<NOTHING>x<IP>x<HOST>x<host>x<ip>x"
    hostname = HostName("testhost")
    ts = Scenario()
    ts.add_host(hostname)
    config_cache = ts.apply(monkeypatch)

    assert config_cache.translate_commandline(
        hostname, ipaddress, template
    ) == "<NOTHING>x{}x{}x<host>x<ip>x".format(ipaddress if ipaddress is not None else "", hostname)


@pytest.mark.parametrize(
    "attributes, expected",
    [
        pytest.param(
            {
                "_ADDRESSES_4": "",
                "_ADDRESSES_6": "",
                "__TAG_piggyback": "auto-piggyback",
                "__TAG_site": "unit",
                "__TAG_snmp_ds": "no-snmp",
                "__LABEL_ding": "dong",
                "__LABEL_cmk/site": "NO_SITE",
                "__LABELSOURCE_cmk/site": "discovered",
                "__LABELSOURCE_ding": "explicit",
                "address": "0.0.0.0",
                "alias": "test-host",
            },
            {
                "cmk/site": "NO_SITE",
                "ding": "dong",
            },
        ),
    ],
)
def test_get_labels_from_attributes(attributes: dict[str, str], expected: Labels) -> None:
    assert get_labels_from_attributes(list(attributes.items())) == expected


@pytest.mark.parametrize(
    "versioned_config_path, host_name, host_labels, expected",
    [
        pytest.param(
            VersionedConfigPath(1),
            "horsthost",
            CollectedHostLabels(
                host_labels={"owe": "owe"},
                service_labels={
                    "svc": {"lbl": "blub"},
                    "svc2": {},
                },
            ),
            CollectedHostLabels(
                host_labels={"owe": "owe"},
                service_labels={"svc": {"lbl": "blub"}},
            ),
        )
    ],
)
def test_write_and_read_notify_host_file(
    versioned_config_path: VersionedConfigPath,
    host_name: HostName,
    host_labels: CollectedHostLabels,
    expected: CollectedHostLabels,
    monkeypatch: MonkeyPatch,
) -> None:
    notify_labels_path: Path = Path(versioned_config_path) / "notify" / "labels"
    monkeypatch.setattr(
        cmk.base.core_config,
        "_get_host_file_path",
        lambda config_path: notify_labels_path,
    )

    write_notify_host_file(
        versioned_config_path,
        {host_name: host_labels},
    )

    assert notify_labels_path.exists()

    monkeypatch.setattr(
        cmk.base.core_config,
        "_get_host_file_path",
        lambda host_name: notify_labels_path / host_name,
    )
    assert read_notify_host_file(host_name) == expected
