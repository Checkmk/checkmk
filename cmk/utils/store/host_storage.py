#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from __future__ import annotations

import abc
import enum
import io
from dataclasses import asdict, dataclass
from functools import lru_cache
from pathlib import Path
from typing import (
    Any,
    Callable,
    Dict,
    Generic,
    List,
    Optional,
    Set,
    Tuple,
    TypedDict,
    TypeVar,
    Union,
)

from cmk.utils import store
from cmk.utils.rulesets.tuple_rulesets import ALL_HOSTS, ALL_SERVICES
from cmk.utils.store import PickleSerializer
from cmk.utils.type_defs import ContactgroupName, HostName, Labels, TaggroupIDToTagID

HostAttributeMapping = Tuple[
    str, str, Dict[str, Any], str
]  # host attr, cmk.base var name, value, title


class GroupRuleType(TypedDict):
    value: Union[List[ContactgroupName], ContactgroupName]
    condition: Dict[str, Union[str, List[str]]]


HostsData = Dict[str, Any]
THostsReadData = TypeVar("THostsReadData")


def host_storage_fileheader() -> str:
    return "# Created by HostStorage\n\n"


def get_hosts_file_variables():
    """These parameters imitate a cmk.base environment"""
    return {
        "FOLDER_PATH": "",
        "ALL_HOSTS": ALL_HOSTS,
        "ALL_SERVICES": ALL_SERVICES,
        "all_hosts": [],
        "host_labels": {},
        "host_tags": {},
        "clusters": {},
        "ipaddresses": {},
        "ipv6addresses": {},
        "explicit_snmp_communities": {},
        "management_snmp_credentials": {},
        "management_ipmi_credentials": {},
        "management_protocol": {},
        "explicit_host_conf": {},
        "extra_host_conf": {"alias": []},
        "extra_service_conf": {"_WATO": []},
        "host_attributes": {},
        "host_contactgroups": [],
        "service_contactgroups": [],
        "_lock": False,
    }


class ContactGroupsField(TypedDict):
    hosts: List[GroupRuleType]
    services: List[GroupRuleType]
    folder_hosts: List[GroupRuleType]
    folder_services: List[GroupRuleType]


@dataclass
class HostsStorageData:
    locked_hosts: bool
    all_hosts: List[HostName]
    clusters: Dict[HostName, Any]
    attributes: Dict[str, Any]
    custom_macros: Dict[str, Any]
    host_tags: Dict[HostName, TaggroupIDToTagID]
    host_labels: Dict[HostName, Labels]
    contact_groups: ContactGroupsField
    explicit_host_conf: Dict[str, Dict[HostName, Any]]
    host_attributes: Dict[HostName, Any]


class HostsStorageFieldsGenerator:
    @classmethod
    def contact_groups(
        cls,
        host_service_group_rules: List[Tuple[List[GroupRuleType], bool]],
        folder_host_service_group_rules: Tuple[Set[str], Set[ContactgroupName], bool],
        folder_path: str,
    ) -> ContactGroupsField:

        contact_group_fields = ContactGroupsField(
            hosts=[], services=[], folder_hosts=[], folder_services=[]
        )
        for group_rules, use_for_services in host_service_group_rules:
            contact_group_fields["hosts"].extend(group_rules)
            if use_for_services:
                contact_group_fields["services"].extend(group_rules)

        # If the contact groups of the folder are set to be used for the monitoring,
        # we create an according rule for the folder here and an according rule for
        # each host that has an explicit setting for that attribute (see above).
        _, folder_contact_groups, use_for_services = folder_host_service_group_rules
        if folder_contact_groups:
            contact_group_fields["folder_hosts"].append(
                {
                    "value": list(folder_contact_groups),
                    "condition": {
                        "host_folder": folder_path,
                    },
                }
            )
            if use_for_services:
                # Currently service_contactgroups requires single values. Lists are not supported
                contact_group_fields["folder_services"] = list(
                    {
                        "value": cg,
                        "condition": {
                            "host_folder": folder_path,
                        },
                    }
                    for cg in folder_contact_groups
                )

        return contact_group_fields

    @classmethod
    def custom_macros(
        cls, custom_macros: Dict[str, Dict[str, str]]
    ) -> Dict[str, List[Tuple[str, List[HostName]]]]:
        macros: Dict[str, List[Tuple[str, List[HostName]]]] = {}
        for custom_varname, entries in custom_macros.items():
            if len(entries) == 0:
                continue
            macros[custom_varname] = []
            for hostname, nagstring in entries.items():
                macros[custom_varname].append((nagstring, [hostname]))
        return macros


class ABCHostsStorage(Generic[THostsReadData]):
    def __init__(self, storage_format: StorageFormat):
        self._storage_format = storage_format

    def exists(self, file_path_without_extension: Path):
        return self.add_file_extension(file_path_without_extension).exists()

    def remove(self, file_path_without_extension: Path):
        Path(self.add_file_extension(file_path_without_extension)).unlink(missing_ok=True)

    def add_file_extension(self, file_path: Path):
        return file_path.with_suffix(self._storage_format.extension())

    def write(
        self, file_path: Path, data: HostsStorageData, value_formatter: Callable[[Any], str]
    ) -> None:
        return self._write(self.add_file_extension(file_path), data, value_formatter)

    def read(self, file_path_without_extension: Path) -> THostsReadData:
        return self._read(self.add_file_extension(file_path_without_extension))

    @abc.abstractmethod
    def _write(
        self, file_path: Path, data: HostsStorageData, value_formatter: Callable[[Any], str]
    ) -> None:
        raise NotImplementedError()

    @abc.abstractmethod
    def _read(self, file_path: Path) -> THostsReadData:
        raise NotImplementedError()


class StandardHostsStorage(ABCHostsStorage[str]):
    def __init__(self):
        super().__init__(StorageFormat.STANDARD)

    def _write(
        self, file_path: Path, data: HostsStorageData, value_formatter: Callable[[Any], str]
    ) -> None:
        out = io.StringIO()
        contact_groups = data.contact_groups
        if contact_groups["hosts"]:
            out.write("\nhost_contactgroups += %s\n\n" % (value_formatter(contact_groups["hosts"])))
        if contact_groups["services"]:
            out.write(
                "\nservice_contactgroups += %s\n\n" % (value_formatter(contact_groups["services"]))
            )

        if data.all_hosts:
            out.write("all_hosts += %s\n" % value_formatter(data.all_hosts))

        if data.clusters:
            out.write("\nclusters.update(%s)\n" % value_formatter(data.clusters))

        if data.host_tags:
            out.write("\nhost_tags.update(%s)\n" % (value_formatter(data.host_tags)))
        if data.host_labels:
            out.write("\nhost_labels.update(%s)\n" % (value_formatter(data.host_labels)))

        for cmk_base_varname, dictionary in data.attributes.items():
            if dictionary:
                out.write("\n# %s\n" % cmk_base_varname)
                out.write("%s.update(" % cmk_base_varname)
                out.write(value_formatter(dictionary))
                out.write(")\n")

        for custom_varname, macro_list in data.custom_macros.items():
            out.write("\n# Settings for %s\n" % custom_varname)
            out.write("extra_host_conf.setdefault(%r, []).extend(\n" % custom_varname)
            out.write("  %s)\n" % value_formatter(macro_list))

        for varname, entries in data.explicit_host_conf.items():
            if len(entries) > 0:
                out.write("\n# Explicit settings for %s\n" % varname)
                out.write("explicit_host_conf.setdefault(%r, {})\n" % varname)
                out.write("explicit_host_conf['%s'].update(%r)\n" % (varname, entries))

        if folder_host_contactgroups := contact_groups["folder_hosts"]:
            out.write("\nhost_contactgroups.insert(0, \n%r)\n" % folder_host_contactgroups)

        if folder_service_contactgroups := contact_groups["folder_services"]:
            for group in folder_service_contactgroups:
                out.write("\nservice_contactgroups.insert(0, %r)" % group)

        # TODO: discuss. cmk.base also parses host_attributes. ipaddresses, mgmtboard, etc.
        out.write("\n# Host attributes (needed for WATO)")
        out.write("\nhost_attributes.update(%s)\n" % value_formatter(data.host_attributes))

        # final
        store.save_text_to_file(file_path, host_storage_fileheader() + out.getvalue())

    def _read(self, file_path: Path) -> str:
        return store.load_text_from_file(str(file_path))


class PickleHostsStorage(ABCHostsStorage[HostsData]):
    def __init__(self):
        super().__init__(StorageFormat.PICKLE)

    def _write(
        self, file_path: Path, data: HostsStorageData, value_formatter: Callable[[Any], str]
    ) -> None:
        pickle_store = store.ObjectStore(file_path, serializer=PickleSerializer())
        with pickle_store.locked():
            pickle_store.write_obj(asdict(data))

    def _read(self, file_path: Path) -> HostsData:
        return store.ObjectStore(file_path, serializer=PickleSerializer()).read_obj(default={})


class RawHostsStorage(ABCHostsStorage[HostsData]):
    def __init__(self):
        super().__init__(StorageFormat.RAW)

    def _write(
        self, file_path: Path, data: HostsStorageData, value_formatter: Callable[[Any], str]
    ) -> None:
        store.save_text_to_file(str(file_path), value_formatter(data))

    def _read(self, file_path: Path) -> HostsData:
        return store.load_object_from_file(str(file_path), default={})


@lru_cache
def make_experimental_hosts_storage(storage_format: StorageFormat) -> Optional[ABCHostsStorage]:
    if storage_format == StorageFormat.RAW:
        return RawHostsStorage()
    if storage_format == StorageFormat.PICKLE:
        return PickleHostsStorage()
    return None


def get_standard_hosts_storage():
    return StandardHostsStorage()


@lru_cache
def get_host_storage_loaders(storage_format_option: str) -> List[ABCHostsStorageLoader]:
    host_storage_loaders: List[ABCHostsStorageLoader] = [
        StandardStorageLoader(get_standard_hosts_storage())
    ]
    if storage := _make_experimental_base_hosts_storage_loader(
        get_storage_format(storage_format_option)
    ):
        host_storage_loaders.insert(0, storage)
    return host_storage_loaders


def _make_experimental_base_hosts_storage_loader(
    storage_format: StorageFormat,
) -> Optional[ABCHostsStorageLoader]:
    if storage := make_experimental_hosts_storage(storage_format):
        return ExperimentalStorageLoader(storage)
    return None


def apply_hosts_file_to_object(
    path_without_extension: Path,
    host_storage_loaders: List[ABCHostsStorageLoader],
    global_dict: Dict[str, Any],
) -> None:
    for storage_loader in host_storage_loaders:
        if storage_loader.file_exists(path_without_extension) and storage_loader.file_valid(
            path_without_extension
        ):
            storage_loader.read_and_apply(path_without_extension, global_dict)
            return


class ABCHostsStorageLoader(abc.ABC, Generic[THostsReadData]):
    __slots__ = ["_storage"]
    """This is WIP class: minimal working functionality. OOP and more clear API is planned"""

    def __init__(self, storage: ABCHostsStorage) -> None:
        self._storage = storage

    def file_exists(self, file_path: Path) -> bool:
        return self._storage.exists(file_path)

    def file_valid(self, file_path: Path) -> bool:
        return True

    def read_and_apply(self, file_path: Path, global_dict: Dict[str, Any]) -> bool:
        return self.apply(self._storage.read(file_path), global_dict)

    @abc.abstractmethod
    def apply(self, data: THostsReadData, global_dict: Dict[str, Any]) -> bool:
        raise NotImplementedError()


class StandardStorageLoader(ABCHostsStorageLoader[str]):
    def apply(self, data: str, global_dict: Dict[str, Any]) -> bool:
        exec(data, global_dict, global_dict)
        return True


class ExperimentalStorageLoader(ABCHostsStorageLoader[HostsData]):
    def file_valid(self, file_path: Path) -> bool:
        # The experimental file must not be older than the corresponding hosts.mk
        # The file is also invalid if no matching hosts.mk file exists
        hosts_mk_path = file_path.with_suffix(StorageFormat.STANDARD.extension())
        if not hosts_mk_path.exists():
            return False

        return (
            hosts_mk_path.stat().st_mtime
            <= self._storage.add_file_extension(file_path).stat().st_mtime
        )

    def apply(self, data: HostsData, global_dict: Dict[str, Any]) -> bool:
        """Integrates HostsData from PickleHostsStorage/RawHostsStorage into the global_dict"""

        # List based settings, append based
        # TODO: all_hosts can be computed out of host_attributes.keys() -> remove?
        if all_hosts := data["all_hosts"]:
            global_dict["all_hosts"].extend(all_hosts)

        cgs = data["contact_groups"]
        for name, global_key in [
            ("hosts", "host_contactgroups"),
            ("services", "service_contactgroups"),
        ]:
            if new_cgs := cgs[name]:
                global_dict[global_key].extend(new_cgs)

        for name, global_key in [
            ("folder_hosts", "host_contactgroups"),
            ("folder_services", "service_contactgroups"),
        ]:
            if new_cgs := cgs[name]:
                global_dict[global_key].extend(new_cgs)
            new_cgs.extend(global_dict[global_key])
            # Do not replace the list reference (in case some outer instance already uses it)
            global_dict[global_key].clear()
            global_dict[global_key].extend(new_cgs)

        # Dict based settings with {key: value}
        for key in [
            "clusters",
            "host_tags",
            "host_labels",
            "ipaddresses",
            "ipv6addresses",
            "explicit_snmp_communities",
            "management_ipmi_credentials",
            "management_snmp_credentials",
            "management_protocol",
            "host_attributes",
        ]:
            global_dict[key].update(data.get(key, {}))

        # Dict based setting with {key: {another_key: value}}
        for explicit_name, values in data.get("explicit_host_conf", {}).items():
            global_dict["explicit_host_conf"].setdefault(explicit_name, {}).update(values)

        # "attributes" are moved to global scope
        # 'attributes': {'ipaddresses': {'test': '1.2.3.4'}}
        # This field should be removed in an upcoming commit
        # It is pretty much the same than the already existing explicit_host_conf
        # and has no dynamic components
        for key, values in data["attributes"].items():
            global_dict.setdefault(key, {}).update(values)

        # Custom macros are moved into extra_host_conf
        for key, values in data["custom_macros"].items():
            global_dict["extra_host_conf"].setdefault(key, []).extend(values)

        global_dict["_lock"] = data["locked_hosts"]
        return True


class StorageFormat(enum.Enum):
    STANDARD = "standard"
    PICKLE = "pickle"
    RAW = "raw"

    def __str__(self) -> str:
        return str(self.value)

    @classmethod
    def from_str(cls, value: str) -> StorageFormat:
        return cls[value.upper()]

    def extension(self) -> str:
        # This typing error is a false positive.  There are tests to demonstrate that.
        return {  # type: ignore[return-value]
            StorageFormat.STANDARD: ".mk",
            StorageFormat.PICKLE: ".pkl",
            StorageFormat.RAW: ".cfg",
        }[self]


def get_all_storage_readers() -> List[ABCHostsStorage]:
    return [
        StandardHostsStorage(),
        RawHostsStorage(),
        PickleHostsStorage(),
    ]


def get_storage_format(format_str: str) -> StorageFormat:
    return StorageFormat.from_str(format_str)
