#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

import pytest
from pydantic import BaseModel

from cmk.ccc import store

from cmk.utils.host_storage import (
    get_hosts_file_variables,
    get_standard_hosts_storage,
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


def tests_standard_format_loader():
    # More tests will follow once the UnifiedHostStorage has been changed to a dataclass
    standard_loader = StandardStorageLoader(get_standard_hosts_storage())
    variables = get_hosts_file_variables()
    standard_loader.apply(_hosts_mk_test_data, variables)
    assert variables["all_hosts"] == ["test"]


def test_pydantic_store_serialization(tmp_path: Path) -> None:
    store_path = tmp_path / "MyModel"

    class MyModel(BaseModel):
        unit: str
        test: int

    my_store = store.PydanticStore(store_path, MyModel)
    with my_store.locked():
        my_store.write_obj(MyModel(unit="bar", test=42))
    assert store_path.read_text() == '{"unit":"bar","test":42}'

    other_store = store.PydanticStore(store_path, MyModel)
    with other_store.locked():
        deserialized_object = other_store.read_obj(default=MyModel(unit="foo", test=0))
    assert isinstance(deserialized_object, MyModel)
    assert deserialized_object.unit == "bar"
    assert deserialized_object.test == 42
