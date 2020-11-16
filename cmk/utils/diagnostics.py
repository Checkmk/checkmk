#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
from pathlib import Path
from typing import Dict, List, Optional, Any, NamedTuple, Set, Tuple
#TODO included in typing since Python >= 3.8
from typing_extensions import TypedDict
from enum import Enum

import cmk.utils.paths

DiagnosticsCLParameters = List[str]
DiagnosticsModesParameters = Dict[str, Any]
DiagnosticsOptionalParameters = Dict[str, Any]
DiagnosticsParameters = TypedDict(
    "DiagnosticsParameters", {
        "site": str,
        "general": None,
        "opt_info": Optional[DiagnosticsOptionalParameters],
        "comp_specific": Optional[DiagnosticsOptionalParameters],
    })
CheckmkFilesMap = Dict[str, Path]

OPT_LOCAL_FILES = "local-files"
OPT_OMD_CONFIG = "omd-config"
OPT_CHECKMK_OVERVIEW = "checkmk-overview"
OPT_CHECKMK_CONFIG_FILES = "checkmk-config-files"
OPT_CHECKMK_LOG_FILES = "checkmk-log-files"

# CEE specific options
OPT_PERFORMANCE_GRAPHS = "performance-graphs"

# GUI, component specific options
OPT_COMP_GLOBAL_SETTINGS = "global-settings"
OPT_COMP_HOSTS_AND_FOLDERS = "hosts-and-folders"
OPT_COMP_NOTIFICATIONS = "notifications"

_BOOLEAN_CONFIG_OPTS = [
    OPT_LOCAL_FILES,
    OPT_OMD_CONFIG,
    OPT_PERFORMANCE_GRAPHS,
    OPT_CHECKMK_OVERVIEW,
]

_FILES_OPTS = [
    OPT_CHECKMK_CONFIG_FILES,
    OPT_CHECKMK_LOG_FILES,
]


def serialize_wato_parameters(wato_parameters: DiagnosticsParameters) -> DiagnosticsCLParameters:
    parameters = {}

    opt_info_parameters = wato_parameters.get("opt_info")
    if opt_info_parameters is not None:
        parameters.update(opt_info_parameters)

    comp_specific_parameters = wato_parameters.get("comp_specific")
    if comp_specific_parameters is not None:
        parameters.update(dict(comp_specific_parameters))

    config_files: Set[str] = set()
    log_files: Set[str] = set()
    serialized_parameters = []
    for key, value in sorted(parameters.items()):
        if key in _BOOLEAN_CONFIG_OPTS and value:
            serialized_parameters.append(key)

        elif key == OPT_CHECKMK_CONFIG_FILES:
            config_files |= _extract_list_of_files(value)

        elif key == OPT_CHECKMK_LOG_FILES:
            log_files |= _extract_list_of_files(value)

        elif key in [
                OPT_COMP_GLOBAL_SETTINGS,
                OPT_COMP_HOSTS_AND_FOLDERS,
                OPT_COMP_NOTIFICATIONS,
        ]:
            config_files |= _extract_list_of_files(value.get("config_files"))
            log_files |= _extract_list_of_files(value.get("log_files"))

    if config_files:
        serialized_parameters.extend([
            OPT_CHECKMK_CONFIG_FILES,
            ",".join(sorted(config_files)),
        ])

    if log_files:
        serialized_parameters.extend([
            OPT_CHECKMK_LOG_FILES,
            ",".join(sorted(log_files)),
        ])
    return serialized_parameters


def _extract_list_of_files(value: Optional[Tuple[str, List[str]]]) -> Set[str]:
    if value is None:
        return set()
    return set(value[1])


def deserialize_cl_parameters(
        cl_parameters: DiagnosticsCLParameters) -> DiagnosticsOptionalParameters:
    if cl_parameters is None:
        return {}

    deserialized_parameters: DiagnosticsOptionalParameters = {}
    parameters = iter(cl_parameters)
    while True:
        try:
            parameter = next(parameters)
            if parameter in _BOOLEAN_CONFIG_OPTS:
                deserialized_parameters[parameter] = True

            elif parameter in _FILES_OPTS:
                deserialized_parameters[parameter] = next(parameters).split(",")

        except StopIteration:
            break

    return deserialized_parameters


def deserialize_modes_parameters(
        modes_parameters: DiagnosticsModesParameters) -> DiagnosticsOptionalParameters:
    deserialized_parameters = {}
    for key, value in modes_parameters.items():
        if key in _BOOLEAN_CONFIG_OPTS:
            deserialized_parameters[key] = value

        elif key in _FILES_OPTS:
            deserialized_parameters[key] = value.split(",")

    return deserialized_parameters


def get_checkmk_config_files_map() -> CheckmkFilesMap:
    files_map: CheckmkFilesMap = {}
    for root, _dirs, files in os.walk(cmk.utils.paths.default_config_dir):
        for file_name in files:
            if file_name == "ca-certificates.mk":
                continue
            filepath = Path(root).joinpath(file_name)
            if filepath.suffix in (".mk", ".conf") or filepath.name == ".wato":
                rel_filepath = str(filepath.relative_to(cmk.utils.paths.default_config_dir))
                files_map.setdefault(rel_filepath, filepath)
    return files_map


def get_checkmk_log_files_map() -> CheckmkFilesMap:
    files_map: CheckmkFilesMap = {}
    for root, _dirs, files in os.walk(cmk.utils.paths.log_dir):
        for file_name in files:
            filepath = Path(root).joinpath(file_name)
            if filepath.suffix in (".log", ".state") or filepath.name == "stats":
                rel_filepath = str(filepath.relative_to(cmk.utils.paths.log_dir))
                files_map.setdefault(rel_filepath, filepath)
    return files_map


class CheckmkFileSensitivity(Enum):
    insensitive = 0
    sensitive = 1
    high_sensitive = 2
    unknown = 3


CheckmkFileInfo = NamedTuple("CheckmkFileInfo", [
    ("components", List[str]),
    ("sensitivity", CheckmkFileSensitivity),
])


def get_checkmk_file_sensitivity_for_humans(rel_filepath: str, file_info: CheckmkFileInfo) -> str:
    sensitivity = file_info.sensitivity
    if sensitivity == CheckmkFileSensitivity.high_sensitive:
        return "%s (!)" % rel_filepath
    if sensitivity == CheckmkFileSensitivity.sensitive:
        return "%s (?)" % rel_filepath
    if sensitivity == CheckmkFileSensitivity.unknown:
        return "%s (-)" % rel_filepath
    # insensitive
    return rel_filepath


def get_checkmk_file_info(rel_filepath: str, component: Optional[str] = None) -> CheckmkFileInfo:
    # Some files like hosts.mk or rules.mk may be located in folder hierarchies.
    # Thus we have to find them via name. The presedence is as following:
    # 1. CheckmkFileInfoByNameMap
    # 2. CheckmkFileInfoByRelFilePathMap

    # Note:
    # A combination FILE + COMPONENT may be only in ONE of these two maps. Otherwise
    # a component collects too many files.
    # Example:
    # - 'Global settings' collects
    #       all 'global.mk'
    #   => ONE entry in CheckmkFileInfoByNameMap
    #
    # - 'Notifications' collects
    #       conf.d/wato/global.mk
    #       mknotify.d/wato/global.mk
    #       multisite.d/wato/global.mk
    #   => MULTIPLE entries in CheckmkFileInfoByRelFilePathMap
    #      (Otherwise all other 'global.mk' would be associated with 'Notifications')

    file_info_by_name = CheckmkFileInfoByNameMap.get(Path(rel_filepath).name)
    if file_info_by_name is not None:
        if component is None or component in file_info_by_name.components:
            return file_info_by_name

    file_info_by_rel_filepath = CheckmkFileInfoByRelFilePathMap.get(rel_filepath)
    if file_info_by_rel_filepath is not None:
        if component is None or component in file_info_by_rel_filepath.components:
            return file_info_by_rel_filepath

    return CheckmkFileInfo(
        components=[],
        sensitivity=CheckmkFileSensitivity(3),
    )


# Feel free to extend the maps:
# - config file entries are relative to "etc/check_mk".
# - log file entries are relative to "var/log".
CheckmkFileInfoByNameMap: Dict[str, CheckmkFileInfo] = {
    # config files
    "sites.mk": CheckmkFileInfo(
        components=[
            OPT_COMP_GLOBAL_SETTINGS,
        ],
        sensitivity=CheckmkFileSensitivity(0),
    ),
    "global.mk": CheckmkFileInfo(
        components=[
            OPT_COMP_GLOBAL_SETTINGS,
        ],
        sensitivity=CheckmkFileSensitivity(1),
    ),
    "hosts.mk": CheckmkFileInfo(
        components=[
            OPT_COMP_HOSTS_AND_FOLDERS,
            OPT_COMP_NOTIFICATIONS,
        ],
        sensitivity=CheckmkFileSensitivity(2),
    ),
    "rules.mk": CheckmkFileInfo(
        components=[
            OPT_COMP_HOSTS_AND_FOLDERS,
            OPT_COMP_NOTIFICATIONS,
        ],
        sensitivity=CheckmkFileSensitivity(2),
    ),
    "tags.mk": CheckmkFileInfo(
        components=[
            OPT_COMP_HOSTS_AND_FOLDERS,
            OPT_COMP_NOTIFICATIONS,
        ],
        sensitivity=CheckmkFileSensitivity(1),
    ),
    ".wato": CheckmkFileInfo(
        components=[
            OPT_COMP_NOTIFICATIONS,
            OPT_COMP_HOSTS_AND_FOLDERS,
        ],
        sensitivity=CheckmkFileSensitivity(0),
    ),
}

CheckmkFileInfoByRelFilePathMap: Dict[str, CheckmkFileInfo] = {
    # config files
    "conf.d/wato/alert_handlers.mk": CheckmkFileInfo(
        components=[
            OPT_COMP_NOTIFICATIONS,
        ],
        sensitivity=CheckmkFileSensitivity(2),
    ),
    "conf.d/wato/contacts.mk": CheckmkFileInfo(
        components=[
            OPT_COMP_NOTIFICATIONS,
        ],
        sensitivity=CheckmkFileSensitivity(2),
    ),
    "conf.d/wato/global.mk": CheckmkFileInfo(
        components=[
            OPT_COMP_NOTIFICATIONS,
        ],
        sensitivity=CheckmkFileSensitivity(1),
    ),
    "conf.d/wato/groups.mk": CheckmkFileInfo(
        components=[
            OPT_COMP_NOTIFICATIONS,
        ],
        sensitivity=CheckmkFileSensitivity(0),
    ),
    "conf.d/wato/notifications.mk": CheckmkFileInfo(
        components=[
            OPT_COMP_NOTIFICATIONS,
        ],
        sensitivity=CheckmkFileSensitivity(2),
    ),
    "main.mk": CheckmkFileInfo(
        components=[
            OPT_COMP_NOTIFICATIONS,
        ],
        sensitivity=CheckmkFileSensitivity(0),
    ),
    "mknotifyd.d/wato/global.mk": CheckmkFileInfo(
        components=[
            OPT_COMP_NOTIFICATIONS,
        ],
        sensitivity=CheckmkFileSensitivity(1),
    ),
    "multisite.d/wato/global.mk": CheckmkFileInfo(
        components=[
            OPT_COMP_NOTIFICATIONS,
        ],
        sensitivity=CheckmkFileSensitivity(1),
    ),
    "multisite.d/wato/groups.mk": CheckmkFileInfo(
        components=[
            OPT_COMP_NOTIFICATIONS,
        ],
        sensitivity=CheckmkFileSensitivity(0),
    ),
    "multisite.d/wato/users.mk": CheckmkFileInfo(
        components=[
            OPT_COMP_NOTIFICATIONS,
        ],
        sensitivity=CheckmkFileSensitivity(2),
    ),
    # Log files
    "cmc.log": CheckmkFileInfo(
        components=[
            OPT_COMP_NOTIFICATIONS,
        ],
        sensitivity=CheckmkFileSensitivity(1),
    ),
    "mknotifyd.log": CheckmkFileInfo(
        components=[
            OPT_COMP_NOTIFICATIONS,
        ],
        sensitivity=CheckmkFileSensitivity(1),
    ),
    "mknotifyd.state": CheckmkFileInfo(
        components=[
            OPT_COMP_NOTIFICATIONS,
        ],
        sensitivity=CheckmkFileSensitivity(1),
    ),
    "notify.log": CheckmkFileInfo(
        components=[
            OPT_COMP_NOTIFICATIONS,
        ],
        sensitivity=CheckmkFileSensitivity(1),
    ),
}
