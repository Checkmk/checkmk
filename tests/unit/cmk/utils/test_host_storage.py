#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

import pytest

from cmk.ccc.hostaddress import HostName
from cmk.utils.host_storage import (
    apply_hosts_file_to_object,
    ContactGroupsField,
    get_host_storage_loaders,
    get_hosts_file_variables,
    get_standard_hosts_storage,
    HostsStorageData,
    PickleHostsStorage,
    StandardStorageLoader,
    StorageFormat,
)


@pytest.mark.parametrize(
    "text, storage_format",
    [
        ("standard", StorageFormat.STANDARD),
        ("raw", StorageFormat.RAW),
        ("pickle", StorageFormat.PICKLE),
    ],
)
def test_storage_format(text: str, storage_format: StorageFormat) -> None:
    assert StorageFormat(text) == storage_format
    assert str(storage_format) == text
    assert StorageFormat.from_str(text) == storage_format


@pytest.mark.parametrize(
    "storage_format, expected_extension",
    [
        (StorageFormat.STANDARD, ".mk"),
        (StorageFormat.RAW, ".cfg"),
        (StorageFormat.PICKLE, ".pkl"),
    ],
)
def test_storage_format_extension(storage_format: StorageFormat, expected_extension: str) -> None:
    assert storage_format.extension() == expected_extension


def test_storage_format_other() -> None:
    assert StorageFormat("standard") != StorageFormat.RAW
    with pytest.raises(KeyError):
        StorageFormat.from_str("bad")


_hosts_mk_test_data = """
# Created by WATO
# encoding: utf-8

host_contactgroups += [{'value': 'contactgroup_omni', 'condition': {'host_name': ['test']}},
                       {'value': 'testgroup', 'condition': {'host_name': ['test']}}]

service_contactgroups += [{'value': 'contactgroup_omni', 'condition': {'host_name': ['test']}},
                          {'value': 'testgroup', 'condition': {'host_name': ['test']}}]

all_hosts += ['test']

host_tags.update({'test': {'site': 'heute', 'address_family': 'ip-v4-only', 'ip-v4': 'ip-v4',
                  'dns_forward': 'dns_forward_active', 'agent': 'cmk-agent', 'tcp': 'tcp',
                  'agent_encryption': 'encryption_enforce', 'piggyback': 'auto-piggyback',
                  'snmp_ds': 'no-snmp', 'criticality': 'prod', 'networking': 'lan'}})

host_labels.update({})

# ipaddresses
ipaddresses.update({'test': '1.2.3.4'})

# Explicit settings for alias
explicit_host_conf.setdefault('alias', {})
explicit_host_conf['alias'].update({'test': 'testalias'})

host_contactgroups.insert(0,
[{'value': ['testgroup', 'contactgroup_omnibus'], 'condition': {'host_folder': '/wato/'}}])

service_contactgroups.insert(0, {'value': 'testgroup', 'condition': {'host_folder': '/wato/'}})
service_contactgroups.insert(0, {'value': 'contactgroup_omni', 'condition': {'host_folder': '/wato/'}})
# Host attributes (needed for WATO)
host_attributes.update({'test': {'contactgroups': {'groups': ['contactgroup_omni', 'testgroup'], 'recurse_perms': False, 'use': True,
                    'use_for_services': True, 'recurse_use': False}, 'alias': 'testalias',
                    'ipaddress': '1.2.3.4', 'additional_ipv4addresses': ['1.2.3.4', '2.3.4.5'],
                    'meta_data': {'created_at': 1628585059.0, 'created_by': 'cmkadmin', 'updated_at': 1628694855.4644992},
                    'tag_address_family': 'ip-v4-only'}})
"""


def tests_standard_format_loader() -> None:
    # More tests will follow once the UnifiedHostStorage has been changed to a dataclass
    standard_loader = StandardStorageLoader(get_standard_hosts_storage())
    variables = get_hosts_file_variables()
    standard_loader.apply(_hosts_mk_test_data, variables)
    assert variables["all_hosts"] == ["test"]


def _hosts_storage_data() -> HostsStorageData:
    host = HostName("host1")
    return HostsStorageData(
        locked_hosts=False,
        all_hosts=[host],
        clusters={HostName("cluster1"): [host]},
        attributes={"ipaddresses": {host: "1.2.3.4"}},
        custom_macros={"_CUSTOM": [("value", [host])]},
        host_tags={host: {}},
        host_labels={host: {"label": "value"}},
        contact_groups=ContactGroupsField(
            hosts=[{"value": "group", "condition": {"host_name": [host]}}],
            services=[],
            folder_hosts=[{"value": ["group"], "condition": {"host_folder": "/wato/"}}],
            folder_services=[],
        ),
        explicit_host_conf={"alias": {host: "An alias"}},
        host_attributes={host: {"ipaddress": "1.2.3.4"}},
        folder_attributes={"/": {"bake_agent_package": False}},
    )


def _write_hosts_files(path_without_extension: Path) -> None:
    data = _hosts_storage_data()
    # The pickled file is only used if it is not older than hosts.mk.
    get_standard_hosts_storage().write(path_without_extension, data, repr)
    PickleHostsStorage().write(path_without_extension, data, repr)


def test_pickled_hosts_apply_to_an_empty_namespace(tmp_path: Path) -> None:
    path = tmp_path / "hosts"
    _write_hosts_files(path)
    loaders = get_host_storage_loaders(StorageFormat.PICKLE)

    seeded = get_hosts_file_variables()
    apply_hosts_file_to_object(path, loaders, seeded)
    unseeded: dict[str, object] = {}
    apply_hosts_file_to_object(path, loaders, unseeded)

    assert unseeded["all_hosts"] == ["host1"]
    assert unseeded["extra_host_conf"] == {"_CUSTOM": [("value", ["host1"])]}
    # The seed predefines an alias macro; everything else is the same.
    assert {k: v for k, v in seeded.items() if k in unseeded and k != "extra_host_conf"} == {
        k: v for k, v in unseeded.items() if k != "extra_host_conf"
    }


def test_pickled_hosts_extend_the_predefined_objects(tmp_path: Path) -> None:
    path = tmp_path / "hosts"
    _write_hosts_files(path)
    variables = get_hosts_file_variables()
    all_hosts, extra_host_conf = variables["all_hosts"], variables["extra_host_conf"]

    apply_hosts_file_to_object(path, get_host_storage_loaders(StorageFormat.PICKLE), variables)

    assert variables["all_hosts"] is all_hosts
    assert variables["extra_host_conf"] is extra_host_conf
    assert extra_host_conf["_CUSTOM"] == [("value", ["host1"])]


def test_written_hosts_mk_loads_into_an_empty_namespace(tmp_path: Path) -> None:
    path = tmp_path / "hosts"
    _write_hosts_files(path)
    loaders = get_host_storage_loaders(StorageFormat.STANDARD)

    seeded = get_hosts_file_variables()
    apply_hosts_file_to_object(path, loaders, seeded)
    unseeded: dict[str, object] = {}
    apply_hosts_file_to_object(path, loaders, unseeded)

    assert unseeded["all_hosts"] == ["host1"]
    assert unseeded["host_contactgroups"] == seeded["host_contactgroups"]
    assert {k: v for k, v in seeded.items() if k in unseeded and k != "extra_host_conf"} == {
        k: v for k, v in unseeded.items() if k != "extra_host_conf"
    }


def test_written_hosts_mk_bootstraps_each_variable_once(tmp_path: Path) -> None:
    path = tmp_path / "hosts"
    get_standard_hosts_storage().write(path, _hosts_storage_data(), repr)

    content = path.with_suffix(".mk").read_text()

    # host_contactgroups is extended twice: by the host rules and the folder rules.
    assert content.count("host_contactgroups = locals().setdefault(") == 1
    assert content.index("host_contactgroups = locals()") < content.index("host_contactgroups +=")


def test_written_hosts_mk_ends_each_update_with_a_blank_line(tmp_path: Path) -> None:
    """The diagnostics redaction of the SNMP credentials relies on it."""
    path = tmp_path / "hosts"
    data = _hosts_storage_data()
    data.attributes["management_snmp_credentials"] = {HostName("host1"): "public"}
    get_standard_hosts_storage().write(path, data, repr)

    content = path.with_suffix(".mk").read_text()

    assert "management_snmp_credentials.update({'host1': 'public'})\n\n" in content
