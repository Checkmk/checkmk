#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="type-arg"

import contextlib
import copy
import sys
from collections.abc import Iterable, Mapping
from pathlib import Path
from types import ModuleType
from typing import override

import cmk.ccc.debug
import cmk.utils.paths
from cmk.base import default_config
from cmk.ccc.hostaddress import HostName
from cmk.utils.host_storage import (
    apply_hosts_file_to_object,
    get_host_storage_loaders,
    StorageFormat,
)
from cmk.utils.log import console
from cmk.utils.misc import key_config_paths


def get_default_config() -> dict[str, object]:
    """Provides a dictionary containing the Check_MK default configuration"""
    # Note: variable_defaults contains a lot of additional values not part of
    # BaseConfig:
    # Type definitions that are leaked by the '*' import, but also deprecated actual
    # config values.
    return {
        key: copy.deepcopy(value) if isinstance(value, dict | list) else value
        for key, value in default_config.__dict__.items()
        # we don't want default_configs submodules here:
        if key[0] != "_" and not isinstance(value, ModuleType)
    }


def strip_tag(tagged_hostname: str) -> HostName:
    return HostName(tagged_hostname.split("|", 1)[0])


def strip_tags(tagged_hostlist: Iterable[str]) -> tuple[HostName, ...]:
    return tuple(strip_tag(h) for h in tagged_hostlist)


class SetFolderPathAbstract:
    def __init__(self, the_object: Iterable) -> None:
        # TODO: Cleanup this somehow to work nicer with mypy
        super().__init__(the_object)  # type: ignore[call-arg]
        self._current_path: str | None = None
        self._collected_host_paths: dict[HostName, str] = {}

    def set_current_path(self, current_path: str | None) -> None:
        self._current_path = current_path

    @property
    def collected_host_paths(self) -> Mapping[HostName, str]:
        return self._collected_host_paths

    def _set_folder_paths(self, new_hosts: Iterable[str]) -> None:
        if self._current_path is None:
            return
        for hostname in map(strip_tag, new_hosts):
            self._collected_host_paths[hostname] = self._current_path


class SetFolderPathList(SetFolderPathAbstract, list):
    @override
    def __iadd__(self, new_hosts: Iterable[str]) -> SetFolderPathList:  # type: ignore[override]
        assert isinstance(new_hosts, list)
        self._set_folder_paths(new_hosts)
        super().__iadd__(new_hosts)
        return self

    @override
    def extend(self, new_hosts: Iterable[str]) -> None:
        self._set_folder_paths(new_hosts)
        super().extend(new_hosts)

    # Probably unused
    @override
    def __add__(self, new_hosts: Iterable[str]) -> SetFolderPathList:  # type: ignore[override]
        assert isinstance(new_hosts, list)
        self._set_folder_paths(new_hosts)
        return SetFolderPathList(super().__add__(new_hosts))

    # Probably unused
    @override
    def append(self, new_host: str) -> None:
        self._set_folder_paths([new_host])
        super().append(new_host)


# TODO: This whole class must die!
class SetFolderPathDict(SetFolderPathAbstract, dict):
    # TODO: How to annotate this?
    @override
    def update(self, new_hosts: Mapping[str, object]) -> None:  # type: ignore[override]
        self._set_folder_paths(new_hosts)
        return super().update(new_hosts)

    # Probably unused+
    @override
    def __setitem__(self, cluster_name: str, value: object) -> None:
        self._set_folder_paths([cluster_name])
        return super().__setitem__(cluster_name, value)


def _load_config_file(file_to_load: Path, into_dict: dict[str, object]) -> None:
    exec(compile(file_to_load.read_text(), file_to_load, "exec"), into_dict, into_dict)  # nosec B102 # BNS:aee528


def load_raw_config(
    *,
    with_conf_d: bool,
) -> Mapping[str, object]:
    target_context = get_default_config()
    helper_vars = {
        "FOLDER_PATH": None,
    }

    raw_all_hosts = target_context["all_hosts"]
    raw_clusters = target_context["clusters"]
    if not isinstance(raw_all_hosts, Iterable):
        raise TypeError("Load config error: The all_hosts parameter is not a list")
    if not isinstance(raw_clusters, dict):
        raise TypeError("Load config error: The clusters parameter is not a dict")

    target_context["all_hosts"] = (all_hosts_h := SetFolderPathList(raw_all_hosts))
    target_context["clusters"] = (clusters_h := SetFolderPathDict(raw_clusters))

    target_context |= helper_vars

    host_storage_loaders = get_host_storage_loaders(StorageFormat.PICKLE)
    for path in get_config_file_paths(with_conf_d):
        try:
            # Make the config path available as a global variable to be used
            # within the configuration file. The FOLDER_PATH is only used by
            # rules.mk files these days, but may also be used in some legacy
            # config files or files generated by 3rd party mechanisms.
            current_path: str | None = None
            folder_path: str | None = None
            with contextlib.suppress(ValueError):
                relative_path = path.relative_to(cmk.utils.paths.check_mk_config_dir)
                current_path = f"/{relative_path}"
                folder_path = str(relative_path.parent)
            target_context["FOLDER_PATH"] = folder_path

            all_hosts_h.set_current_path(current_path)
            clusters_h.set_current_path(current_path)

            if path.name == "hosts.mk":
                apply_hosts_file_to_object(
                    path.with_suffix(""), host_storage_loaders, target_context
                )
            else:
                _load_config_file(path, target_context)

            host_paths = target_context["host_paths"]
            if not isinstance(host_paths, dict):
                raise TypeError("Load config error: The host_paths parameter is not a dict")

            if not isinstance(target_context["all_hosts"], SetFolderPathList):
                raise TypeError(
                    "Load config error: The all_hosts parameter was modified through an other method than: x+=a or x=x+a"
                )
            host_paths.update(target_context["all_hosts"].collected_host_paths)

            if not isinstance(target_context["clusters"], SetFolderPathDict):
                raise TypeError(
                    "Load config error: The clusters parameter was modified through an other method than: x['a']=b or x.update({'a': b})"
                )
            host_paths.update(target_context["clusters"].collected_host_paths)

        except Exception as e:
            if cmk.ccc.debug.enabled():
                raise
            if sys.stderr.isatty():
                console.error(f"Cannot read in configuration file {path}: {e}", file=sys.stderr)
            sys.exit(1)

    # Cleanup helper vars
    for helper_var in helper_vars:
        del target_context[helper_var]

    # Revert specialised SetFolderPath classes back to normal, because it improves
    # the lookup performance and the helper_vars are no longer available anyway..
    target_context["all_hosts"] = list(all_hosts_h)
    target_context["clusters"] = dict(clusters_h)
    return target_context


# Create list of all files to be included during configuration loading
def get_config_file_paths(with_conf_d: bool) -> list[Path]:
    list_of_files = [cmk.utils.paths.main_config_file]
    if with_conf_d:
        all_files = cmk.utils.paths.check_mk_config_dir.rglob("*")
        list_of_files += sorted([p for p in all_files if p.suffix in {".mk"}], key=key_config_paths)
    for path in [cmk.utils.paths.final_config_file, cmk.utils.paths.local_config_file]:
        if path.exists():
            list_of_files.append(path)
    return list_of_files
