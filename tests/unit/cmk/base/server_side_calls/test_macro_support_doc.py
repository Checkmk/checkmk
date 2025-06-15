#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Test documentation of supported macros in server side calls

These tests are a single point of truth about supported macros
in active check and special agent SSC plugins.
"""

import socket
from collections.abc import Iterable, Iterator, Sequence

import pytest

from tests.testlib.unit.base_configuration_scenario import Scenario

import cmk.ccc.version as cmk_version
from cmk.ccc.hostaddress import HostAddress, HostName

import cmk.utils.paths
from cmk.utils.ip_lookup import IPStackConfig

import cmk.base.config as base_config
from cmk.base.config import ConfigCache

DOCUMENTED_ACTIVE_CHECK_MACROS = {
    "required": [
        "$HOSTNAME$",
        "$HOSTADDRESS$",
        "$HOSTALIAS$",
        "$HOST_TAGS$",
        "$_HOSTTAGS$",
        "$HOST_ADDRESS_4$",
        "$_HOSTADDRESS_4$",
        "$HOST_ADDRESS_6$",
        "$_HOSTADDRESS_6$",
        "$HOST_ADDRESS_FAMILY$",
        "$_HOSTADDRESS_FAMILY$",
        "$HOST_ADDRESSES_4$",
        "$_HOSTADDRESSES_4$",
        "$HOST_ADDRESSES_6$",
        "$_HOSTADDRESSES_6$",
        "$HOST_FILENAME$",
        "$_HOSTFILENAME$",
        "$USER1$",
        "$USER2$",
        "$USER3$",
        "$USER4$",
    ],
    "CME_only": [
        "$HOST_CUSTOMER$",
        "$_HOSTCUSTOMER$",
    ],
    "per_tag": [
        "$HOST__TAG_{name}$",
        "$_HOST_TAG_{name}$",
    ],
    "per_label": [
        "$HOST__LABEL_{name}$",
        "$_HOST_LABEL_{name}$",
    ],
    "per_label_source": [
        "$HOST__LABELSOURCE_{name}$",
        "$_HOST_LABELSOURCE_{name}$",
    ],
    "per_custom_host_attribute": [
        "$HOST_{name}$",  # host attribute name is capitalized
        "$_HOST{name}$",
    ],
    "per_custom_macro": ["${name}$"],  # user defined macros from etc/nagios/resource.cfg file
}

DOCUMENTED_SPECIAL_AGENT_MACROS = {
    "required": [
        "<IP>",
        "<HOST>",
        "$HOSTNAME$",
        "$HOSTADDRESS$",
        "$HOSTALIAS$",
        "$HOST_TAGS$",
        "$_HOSTTAGS$",
        "$HOST_ADDRESS_4$",
        "$_HOSTADDRESS_4$",
        "$HOST_ADDRESS_6$",
        "$_HOSTADDRESS_6$",
        "$HOST_ADDRESS_FAMILY$",
        "$_HOSTADDRESS_FAMILY$",
        "$HOST_ADDRESSES_4$",
        "$_HOSTADDRESSES_4$",
        "$HOST_ADDRESSES_6$",
        "$_HOSTADDRESSES_6$",
        "$HOST_FILENAME$",
        "$_HOSTFILENAME$",
    ],
    "CME_only": [
        "$HOST_CUSTOMER$",
        "$_HOSTCUSTOMER$",
    ],
    "per_tag": [
        "$HOST__TAG_{name}$",
        "$_HOST_TAG_{name}$",
    ],
    "per_label": [
        "$HOST__LABEL_{name}$",
        "$_HOST_LABEL_{name}$",
    ],
    "per_label_source": [
        "$HOST__LABELSOURCE_{name}$",
        "$_HOST_LABELSOURCE_{name}$",
    ],
    "per_custom_host_attribute": [
        "$HOST_{name}$",  # host attribute name is capitalized
        "$_HOST{name}$",
    ],
}


@pytest.fixture(name="config_cache")
def fixture_core_scenario(monkeypatch):
    ts = Scenario()
    ts.add_host(HostName("test-host"))
    ts.set_option("ipaddresses", {"test-host": "127.0.0.1"})
    ts.set_option("explicit_host_conf", {"_custom_attr": {"test-host": "attr_value"}})
    return ts.apply(monkeypatch)


@pytest.fixture(name="resource_cfg_file")
def fixture_resource_cfg_file():
    file_path = cmk.utils.paths.omd_root / "etc/nagios/resource.cfg"
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(
        "############################################\n"
        "# OMD settings, please use them to make your config\n"
        "# portable, but don't change them\n"
        "$USER1$=/omd/sites/prod/lib/nagios/plugins\n"
        "$USER2$=/omd/sites/prod/local/lib/nagios/plugins\n"
        "$USER3$=prod\n"
        "$USER4$=/omd/sites/prod\n"
        "############################################\n"
        "# set your own macros here:\n"
        "$CUSTOM_MACRO$=wrdlpfrmpt\n"
    )


def _iter_macros(documented_macros: Sequence[str], resources: Iterable[str]) -> Iterator[str]:
    for resource in resources:
        for macro_template in documented_macros:
            yield macro_template.replace("{name}", resource)


def test_active_checks_macros(config_cache: ConfigCache, resource_cfg_file: None) -> None:
    host_name = HostName("test-host")
    ip_address_of = lambda *a: HostAddress("")
    host_attrs = config_cache.get_host_attributes(
        host_name, socket.AddressFamily.AF_INET, ip_address_of
    )

    host_macros = base_config.ConfigCache.get_host_macros_from_attributes(host_name, host_attrs)
    resource_macros = base_config.get_resource_macros()
    macros = {**host_macros, **resource_macros}

    additional_addresses_ipv4, additional_addresses_ipv6 = config_cache.additional_ipaddresses(
        host_name
    )
    host_config = base_config.get_ssc_host_config(
        host_name,
        config_cache.alias(host_name),
        socket.AddressFamily.AF_INET,
        IPStackConfig.IPv4,
        additional_addresses_ipv4,
        additional_addresses_ipv6,
        macros,
        ip_address_of,
    )

    documented = DOCUMENTED_ACTIVE_CHECK_MACROS

    label_sources = config_cache.label_manager.label_sources_of_host(host_name).keys()
    custom_attrs = [
        attr[1:].upper() for attr in config_cache.explicit_host_attributes(host_name).keys()
    ]

    expected_macros = (
        documented["required"]
        + list(_iter_macros(documented["per_tag"], config_cache.host_tags.tags(host_name).keys()))
        + list(
            _iter_macros(
                documented["per_label"], config_cache.label_manager.labels_of_host(host_name).keys()
            )
        )
        + list(_iter_macros(documented["per_label_source"], label_sources))
        + list(_iter_macros(documented["per_custom_host_attribute"], custom_attrs))
        + list(_iter_macros(documented["per_custom_macro"], ["CUSTOM_MACRO"]))
    )

    if cmk_version.edition(cmk.utils.paths.omd_root).short == "cme":
        expected_macros.extend(documented["CME_only"])

    assert sorted(host_config.macros.keys()) == sorted(expected_macros)


def test_special_agent_macros(
    config_cache: ConfigCache,
) -> None:
    host_name = HostName("test-host")
    ip_address_of = lambda *a: HostAddress("")

    host_attrs = config_cache.get_host_attributes(
        host_name, socket.AddressFamily.AF_INET, ip_address_of
    )
    macros = {
        "<IP>": "127.0.0.1",
        "<HOST>": host_name,
        **base_config.ConfigCache.get_host_macros_from_attributes(host_name, host_attrs),
    }

    additional_addresses_ipv4, additional_addresses_ipv6 = config_cache.additional_ipaddresses(
        host_name
    )
    host_config = base_config.get_ssc_host_config(
        host_name,
        config_cache.alias(host_name),
        socket.AddressFamily.AF_INET,
        IPStackConfig.IPv4,
        additional_addresses_ipv4,
        additional_addresses_ipv6,
        macros,
        ip_address_of,
    )

    documented = DOCUMENTED_SPECIAL_AGENT_MACROS

    label_sources = config_cache.label_manager.label_sources_of_host(host_name).keys()
    custom_attrs = [
        attr[1:].upper() for attr in config_cache.explicit_host_attributes(host_name).keys()
    ]

    expected_macros = (
        documented["required"]
        + list(_iter_macros(documented["per_tag"], config_cache.host_tags.tags(host_name).keys()))
        + list(
            _iter_macros(
                documented["per_label"], config_cache.label_manager.labels_of_host(host_name).keys()
            )
        )
        + list(_iter_macros(documented["per_label_source"], label_sources))
        + list(_iter_macros(documented["per_custom_host_attribute"], custom_attrs))
    )

    if cmk_version.edition(cmk.utils.paths.omd_root).short == "cme":
        expected_macros.extend(documented["CME_only"])

    assert sorted(host_config.macros.keys()) == sorted(expected_macros)
