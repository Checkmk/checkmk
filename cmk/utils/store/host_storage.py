#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from __future__ import annotations

import abc
import enum
import io
from functools import lru_cache
from pathlib import Path
from typing import Any, Callable, Dict, Generic, List, Optional, Set, Tuple, TypedDict, TypeVar

from cmk.utils import store
from cmk.utils.store import PickleSerializer
from cmk.utils.type_defs import ContactgroupName

HostAttributeMapping = Tuple[str, str, Dict[str, Any],
                             str]  # host attr, cmk.base var name, value, title


class GroupRuleType(TypedDict):
    value: ContactgroupName
    condition: Dict[str, List[str]]


HostsData = Dict[str, Any]
THostsReadData = TypeVar("THostsReadData")

from cmk.utils.rulesets.tuple_rulesets import ALL_HOSTS, ALL_SERVICES


def host_storage_fileheader() -> str:
    return "# Created by HostStorage\n\n"


def get_hosts_file_variables():
    """ These parameters imitate a cmk.base environment """
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
        "cmk_agent_connection": {},
        "explicit_snmp_communities": {},
        "management_snmp_credentials": {},
        "management_ipmi_credentials": {},
        "management_protocol": {},
        "explicit_host_conf": {},
        "extra_host_conf": {
            "alias": []
        },
        "extra_service_conf": {
            "_WATO": []
        },
        "host_attributes": {},
        "host_contactgroups": [],
        "service_contactgroups": [],
        "_lock": False,
    }


# TODO: dataclass
class UnifiedHostStorage:
    """Engine to save variable in config file"""
    __slots__ = ['_data']
    """_data keeps all required data for config"""
    def __init__(self) -> None:
        self._data: HostsData = {}

    @property
    def data(self) -> HostsData:
        return self._data

    def save_locked_hosts(self, is_locked: bool = False) -> None:
        self._data["_lock"] = is_locked

    def save_host_contact_groups(self, group_rules_list: List[Tuple[List[GroupRuleType],
                                                                    bool]]) -> None:
        for group_rules, use_for_service in group_rules_list:
            self._save_group_rules(group_rules, use_for_service)

    def _save_group_rules(self, group_rules: List[GroupRuleType], use_for_services: bool) -> None:
        self._data.setdefault("host_contactgroups", []).extend(group_rules)
        if use_for_services:
            self._data.setdefault("service_contactgroups", []).extend(group_rules)

    def save_all_hosts(self, all_hosts: List[str]) -> None:
        self._data["all_hosts"] = all_hosts

    def save_clusters(self, clusters: Dict[str, List[str]]) -> None:
        self._data["clusters"] = clusters

    def save_host_tags(self, host_tags: Dict[str, Any]) -> None:
        self._data["host_tags"] = host_tags

    def save_host_labels(self, host_labels: Dict[str, Any]) -> None:
        self._data["host_labels"] = host_labels

    def save_extra_host_conf(self, custom_macros: Dict[str, Dict[str, str]]) -> None:
        for custom_varname, entries in custom_macros.items():
            macrolist = []
            for hostname, nagstring in entries.items():
                macrolist.append((nagstring, [hostname]))
            if len(macrolist) > 0:
                self._data.setdefault("custom_macros", {})[custom_varname] = macrolist

    def save_attributes(self, attribute_mappings: List[HostAttributeMapping]):
        for _host_attr, cmk_base_varname, dictionary, _title in attribute_mappings:
            if dictionary:
                self._data.setdefault("attributes", {})[cmk_base_varname] = dictionary

    def save_explicit_host_settings(self, explicit_host_settings: Dict[str, Dict[str, str]]):
        for varname, entries in explicit_host_settings.items():
            if len(entries) > 0:
                self._data.setdefault("explicit_host_conf", {})[varname] = entries

    def save_folder_contact_groups(self, folder_path: str, groups: Tuple[Set[str], Set[str], bool]):
        # If the contact groups of the folder are set to be used for the monitoring,
        # we create an according rule for the folder here and an according rule for
        # each host that has an explicit setting for that attribute (see above).
        _, contact_groups, use_for_services = groups
        if contact_groups:
            self._data["folder_host_contactgroups"] = [{
                "value": list(contact_groups),
                "condition": {
                    'host_folder': folder_path,
                }
            }]
            if use_for_services:
                # Currently service_contactgroups requires single values. Lists are not supported
                self._data["folder_service_contactgroups"] = []
                for cg in contact_groups:
                    self._data["folder_service_contactgroups"].append({
                        "value": cg,
                        "condition": {
                            'host_folder': folder_path,
                        }
                    })

    def save_cleaned_hosts(self, cleaned_hosts: Dict[str, Dict[str, Any]]) -> None:
        """Write information about all host attributes into special variable - even
        values stored for check_mk as well."""
        self._data["host_attributes"] = cleaned_hosts


class ABCHostsStorage(Generic[THostsReadData]):
    def __init__(self, storage_format: StorageFormat):
        self._storage_format = storage_format

    def exists(self, file_path_without_extension: Path):
        return self.add_file_extension(file_path_without_extension).exists()

    def add_file_extension(self, file_path: Path):
        return file_path.with_suffix(self._storage_format.extension())

    def write(self, file_path: Path, data: HostsData, value_formatter: Callable[[Any],
                                                                                str]) -> None:
        return self._write(self.add_file_extension(file_path), data, value_formatter)

    def read(self, file_path_without_extension: Path) -> THostsReadData:
        return self._read(self.add_file_extension(file_path_without_extension))

    @abc.abstractmethod
    def _write(self, file_path: Path, data: HostsData, value_formatter: Callable[[Any],
                                                                                 str]) -> None:
        raise NotImplementedError()

    @abc.abstractmethod
    def _read(self, file_path: Path) -> THostsReadData:
        raise NotImplementedError()


class StandardHostsStorage(ABCHostsStorage[str]):
    def __init__(self):
        super().__init__(StorageFormat.STANDARD)

    def _write(self, file_path: Path, data: HostsData, value_formatter: Callable[[Any],
                                                                                 str]) -> None:
        out = io.StringIO()
        for name in ["host_contactgroups", "service_contactgroups"]:
            if group_rules := data.get(name, []):
                out.write("\n%s += %s\n\n" % (name, value_formatter(group_rules)))

        if data["all_hosts"]:
            out.write("all_hosts += %s\n" % value_formatter(data["all_hosts"]))

        if data["clusters"]:
            out.write("\nclusters.update(%s)\n" % value_formatter(data["clusters"]))

        for name in ["host_tags", "host_labels"]:
            the_dict = data.get(name, {})
            out.write("\n%s.update(%s)\n" % (name, value_formatter(the_dict)))

        attributes = data.get("attributes", {})
        for cmk_base_varname, dictionary in attributes.items():
            if dictionary:
                out.write("\n# %s\n" % cmk_base_varname)
                out.write("%s.update(" % cmk_base_varname)
                out.write(value_formatter(dictionary))
                out.write(")\n")

        custom_macros = data.get("custom_macros", {})
        for custom_varname, macro_list in custom_macros.items():
            if len(macro_list) > 0:
                out.write("\n# Settings for %s\n" % custom_varname)
                out.write("extra_host_conf.setdefault(%r, []).extend(\n" % custom_varname)
                out.write("  %s)\n" % value_formatter(macro_list))

        explicit_host_settings = data.get("explicit_host_conf", {})
        for varname, entries in explicit_host_settings.items():
            if len(entries) > 0:
                out.write("\n# Explicit settings for %s\n" % varname)
                out.write("explicit_host_conf.setdefault(%r, {})\n" % varname)
                out.write("explicit_host_conf['%s'].update(%r)\n" % (varname, entries))

        if folder_host_contact_groups := data.get("folder_host_contactgroups"):
            out.write("\nhost_contactgroups.insert(0, \n%r)\n" % folder_host_contact_groups)

        if folder_service_contact_groups := data.get("folder_service_contactgroups"):
            for group in folder_service_contact_groups:
                out.write("\nservice_contactgroups.insert(0, %r)" % group)

        # TODO: discuss. cmk.base also parses host_attributes. ipaddresses, mgmtboard, etc.
        out.write("\n# Host attributes (needed for WATO)")
        out.write("\nhost_attributes.update(%s)\n" % value_formatter(data["host_attributes"]))

        # final
        store.save_text_to_file(file_path, host_storage_fileheader() + out.getvalue())

    def _read(self, file_path: Path) -> str:
        return store.load_text_from_file(str(file_path))


class PickleHostsStorage(ABCHostsStorage[HostsData]):
    def __init__(self):
        super().__init__(StorageFormat.PICKLE)

    def _write(self, file_path: Path, data: HostsData, value_formatter: Callable[[Any],
                                                                                 str]) -> None:
        pickle_store = store.ObjectStore(file_path, serializer=PickleSerializer())
        with pickle_store.locked():
            pickle_store.write_obj(data)

    def _read(self, file_path: Path) -> HostsData:
        return store.ObjectStore(file_path, serializer=PickleSerializer()).read_obj(default={})


class RawHostsStorage(ABCHostsStorage[HostsData]):
    def __init__(self):
        super().__init__(StorageFormat.RAW)

    def _write(self, file_path: Path, data: HostsData, value_formatter: Callable[[Any],
                                                                                 str]) -> None:
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
            get_storage_format(storage_format_option)):
        host_storage_loaders.insert(0, storage)
    return host_storage_loaders


def _make_experimental_base_hosts_storage_loader(
        storage_format: StorageFormat) -> Optional[ABCHostsStorageLoader]:
    if storage := make_experimental_hosts_storage(storage_format):
        return ExperimentalStorageLoader(storage)
    return None


def apply_hosts_file_to_object(
    path_without_extension: Path,
    host_storage_loaders: List[ABCHostsStorageLoader],
    global_dict: Dict[str, Any],
) -> None:
    for storage_loader in host_storage_loaders:
        if storage_loader.file_exists(path_without_extension):
            storage_loader.read_and_apply(path_without_extension, global_dict)
            return


class ABCHostsStorageLoader(abc.ABC, Generic[THostsReadData]):
    __slots__ = ["_storage"]
    """This is WIP class: minimal working functionality. OOP and more clear API is planned"""
    def __init__(self, storage: ABCHostsStorage) -> None:
        self._storage = storage

    def file_exists(self, file_path: Path) -> bool:
        return self._storage.exists(file_path)

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
    def apply(self, data: HostsData, global_dict: Dict[str, Any]) -> bool:
        """ Integrates HostsData from PickleHostsStorage/RawHostsStorage into the global_dict """

        # List based settings, append based
        for key in ["all_hosts", "host_contactgroups", "service_contactgroups"]:
            global_dict[key].extend(data.get(key, {}))

        # List based settings, prepend based
        for (actual_key, storage_key) in [
            ("host_contactgroups", "folder_host_contactgroups"),
            ("service_contactgroups", "folder_service_contactgroups"),
        ]:
            for entry in data.get(storage_key, []):
                global_dict[actual_key].insert(0, entry)

        # Dict based settings
        for key in [
                "clusters",
                "host_tags",
                "host_labels",
                "ipaddresses",
                "ipv6addresses",
                "cmk_agent_connection",  # TODO: will be changed to explicit_attribute
                "explicit_snmp_communities",
                "management_ipmi_credentials",
                "management_snmp_credentials",
                "management_protocol",
                "explicit_host_conf",
                "host_attributes",
        ]:
            global_dict[key].update(data.get(key, {}))

        # "attributes" are moved to global scope
        # 'attributes': {'cmk_agent_connection': {'test': 'pull-agent'},
        #                'ipaddresses': {'test': '1.2.3.4'}}
        # This field should be removed in an upcoming commit
        # It is pretty much the same than the already existing explicit_host_conf
        # and has no dynamic components
        for key, values in data.get("attributes", {}).items():
            global_dict["extra_host_conf"].setdefault(key, []).extend(values)

        # Custom macros are moved into extra_host_conf
        for key, values in data.get("custom_macros", {}).items():
            global_dict["extra_host_conf"].setdefault(key, []).extend(values)

        # TODO: locked -> _lock
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


def get_storage_format(format_str: str) -> StorageFormat:
    return StorageFormat.from_str(format_str)
