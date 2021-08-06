#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import abc
import io
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, TypedDict

from cmk.utils import store
from cmk.utils.store import PickleSerializer, StorageFormat
from cmk.utils.type_defs import ContactgroupName

HostAttributeMapping = Tuple[str, str, Dict[str, Any],
                             str]  # host attr, cmk.base var name, value, title


class GroupRuleType(TypedDict):
    value: ContactgroupName
    condition: Dict[str, List[str]]


HostsData = Dict[str, Any]

from cmk.utils.rulesets.tuple_rulesets import ALL_HOSTS, ALL_SERVICES


def host_storage_fileheader() -> str:
    return "# Created by HostStorage\n\n"


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

    def save_group_rules_list(self, group_rules_list: List[Tuple[List[GroupRuleType], bool]]):
        for group_rules, use_for_service in group_rules_list:
            self._save_group_rules(group_rules, use_for_service)

    def _save_group_rules(self, group_rules: List[GroupRuleType],
                          use_for_services: Optional[bool]) -> None:
        self._data["host_contactgroups"] = group_rules
        if use_for_services:
            self._data["service_contactgroups"] = group_rules

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

    def save_contact_groups(self, folder_path: str, groups: Tuple[Set[str], Set[str], bool]):
        # If the contact groups of the folder are set to be used for the monitoring,
        # we create an according rule for the folder here and an according rule for
        # each host that has an explicit setting for that attribute (see above).
        _, contact_groups, use_for_services = groups
        if contact_groups:
            self._data.setdefault("contact_groups", {})["host"] = {
                "value": contact_groups,
                "condition": {
                    'host_folder': folder_path,
                }
            }
            if use_for_services:
                # Currently service_contactgroups requires single values. Lists are not supported
                for cg in contact_groups:
                    self._data.setdefault("contact_groups", {})["service"] = {
                        "value": cg,
                        "condition": {
                            'host_folder': folder_path,
                        }
                    }

    def save_cleaned_hosts(self, cleaned_hosts: Dict[str, Dict[str, Any]]) -> None:
        """Write information about all host attributes into special variable - even
        values stored for check_mk as well."""
        self._data["host_attributes"] = cleaned_hosts


class ABCHostsStorage:
    def __init__(self, storage_format: StorageFormat):
        self._storage_format = storage_format

    def exists(self, file_path_without_extension: Path):
        return self.add_file_extension(file_path_without_extension).exists()

    def add_file_extension(self, file_path: Path):
        return file_path.parent / (file_path.name + self._storage_format.extension())

    def write(self, file_path: Path, data: HostsData, value_formatter: Callable[[Any],
                                                                                str]) -> None:
        return self._write(self.add_file_extension(file_path), data, value_formatter)

    def read(self, file_path_without_extension: Path) -> HostsData:
        return self._read(self.add_file_extension(file_path_without_extension))

    @abc.abstractmethod
    def _write(self, file_path: Path, data: HostsData, value_formatter: Callable[[Any],
                                                                                 str]) -> None:
        raise NotImplementedError()

    @abc.abstractmethod
    def _read(self, file_path: Path) -> HostsData:
        raise NotImplementedError()


class StandardHostsStorage(ABCHostsStorage):
    def __init__(self):
        super().__init__(StorageFormat.STANDARD)

    def _write(self, file_path: Path, data: HostsData, value_formatter: Callable[[Any],
                                                                                 str]) -> None:
        out = io.StringIO()
        for name in ["host_contactgroups", "service_contactgroups"]:
            group_rules = data.get(name, [])
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

        if contact_groups := data.get("contact_groups"):
            if host_contact_groups := contact_groups.get("host", []):
                out.write(
                    "\nhost_contactgroups.insert(0, \n"
                    "  {'value': %r, 'condition': {'host_folder': '/%%s/' %% FOLDER_PATH}})\n" %
                    list(host_contact_groups))
            if service_contact_groups := contact_groups.get("service", []):
                # Currently service_contactgroups requires single values. Lists are not supported
                for cg in service_contact_groups:
                    out.write(
                        "\nservice_contactgroups.insert(0, \n"
                        "  {'value': %r, 'condition': {'host_folder': '/%%s/' %% FOLDER_PATH}})\n" %
                        cg)

        out.write("# Host attributes (needed for WATO)")
        out.write("\nhost_attributes.update(%s)\n" % value_formatter(data["host_attributes"]))

        # final
        store.save_text_to_file(file_path, host_storage_fileheader() + out.getvalue())

    def _read(self, file_path: Path) -> HostsData:
        variables = {
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
        store.load_mk_file(str(file_path), variables)
        return variables


class PickleHostsStorage(ABCHostsStorage):
    def __init__(self):
        super().__init__(StorageFormat.PICKLE)

    def _write(self, file_path: Path, data: HostsData, value_formatter: Callable[[Any],
                                                                                 str]) -> None:
        pickle_store = store.ObjectStore(file_path, serializer=PickleSerializer())
        with pickle_store.locked():
            pickle_store.write_obj(data)

    def _read(self, file_path: Path) -> HostsData:
        return store.ObjectStore(file_path, serializer=PickleSerializer()).read_obj(default={})


class RawHostsStorage(ABCHostsStorage):
    def __init__(self):
        super().__init__(StorageFormat.RAW)

    def _write(self, file_path: Path, data: HostsData, value_formatter: Callable[[Any],
                                                                                 str]) -> None:
        store.save_text_to_file(str(file_path), value_formatter(data))

    def _read(self, file_path: Path) -> HostsData:
        return store.load_object_from_file(str(file_path), default={})


def make_experimental_hosts_storage(storage_format: StorageFormat) -> Optional[ABCHostsStorage]:
    if storage_format == store.StorageFormat.RAW:
        return RawHostsStorage()
    if storage_format == store.StorageFormat.PICKLE:
        return PickleHostsStorage()
    return None


def load_hosts_file(file_path_without_extension: Path,
                    storage_format: StorageFormat) -> Optional[HostsData]:
    storage_list: List[ABCHostsStorage] = [StandardHostsStorage()]
    if experimental_storage := make_experimental_hosts_storage(storage_format):
        storage_list.insert(0, experimental_storage)

    file_path = Path(file_path_without_extension)
    for storage in storage_list:
        if storage.exists(file_path):
            return storage.read(file_path)

    return None


def get_storage_format(format_str: str) -> 'store.StorageFormat':
    return store.StorageFormat.from_str(format_str)
