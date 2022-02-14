#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Iterator, List, NamedTuple, Optional, Sequence, Set, Tuple

#TODO included in typing since Python >= 3.8
from typing_extensions import TypedDict

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
DiagnosticsElementJSONResult = Dict[str, Any]
DiagnosticsElementCSVResult = str
DiagnosticsElementFilepaths = Iterator[Path]

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
OPT_COMP_BUSINESS_INTELLIGENCE = "business-intelligence"

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

_MODULE_TO_PATH = {
    "agent_based": "lib/check_mk/base/plugins/agent_based",
    "agents": "share/check_mk/agents",
    "alert_handlers": "share/check_mk/alert_handlers",
    "bin": "bin",
    "checkman": "share/check_mk/checkman",
    "checks": "share/check_mk/checks",
    "doc": "share/doc/check_mk",
    "ec_rule_packs": "EC_RULE",
    "inventory": "share/check_mk/inventory",
    "lib": "lib",
    "locales": "share/check_mk/locale",
    "mibs": "share/snmp/mibs",
    "notifications": "share/check_mk/notifications",
    "pnp-templates": "share/check_mk/pnp-templates",
    "web": "share/check_mk/web",
}

_CSV_COLUMNS = [
    "path",
    "exists",
    "package",
    "author",
    "description",
    "download_url",
    "name",
    "title",
    "version",
    "version.min_required",
    "version.packaged",
    "version.usable_until",
    "permissions",
    "installed",
    "optional_packages",
    "unpackaged",
]


def serialize_wato_parameters(
        wato_parameters: DiagnosticsParameters) -> List[DiagnosticsCLParameters]:
    parameters = {}

    opt_info_parameters = wato_parameters.get("opt_info")
    if opt_info_parameters is not None:
        parameters.update(opt_info_parameters)

    comp_specific_parameters = wato_parameters.get("comp_specific")
    if comp_specific_parameters is not None:
        parameters.update(comp_specific_parameters)

    config_files: Set[str] = set()
    log_files: Set[str] = set()
    boolean_opts: List[str] = []
    for key, value in sorted(parameters.items()):
        if key in _BOOLEAN_CONFIG_OPTS and value:
            boolean_opts.append(key)

        elif key == OPT_CHECKMK_CONFIG_FILES:
            config_files |= _extract_list_of_files(value)

        elif key == OPT_CHECKMK_LOG_FILES:
            log_files |= _extract_list_of_files(value)

        elif key in [
                OPT_COMP_GLOBAL_SETTINGS,
                OPT_COMP_HOSTS_AND_FOLDERS,
                OPT_COMP_NOTIFICATIONS,
                OPT_COMP_BUSINESS_INTELLIGENCE,
        ]:
            config_files |= _extract_list_of_files(value.get("config_files"))
            log_files |= _extract_list_of_files(value.get("log_files"))

    chunks: List[List[str]] = []
    if boolean_opts:
        chunks.append(boolean_opts)

    max_args: int = _get_max_args() - 1  # OPT will be appended in for loop
    for config_args in [
            sorted(config_files)[i:i + max_args]
            for i in range(0, len(sorted(config_files)), max_args)
    ]:
        chunks.append([OPT_CHECKMK_CONFIG_FILES, ','.join(config_args)])

    for log_args in [
            sorted(log_files)[i:i + max_args] for i in range(0, len(sorted(log_files)), max_args)
    ]:
        chunks.append([OPT_CHECKMK_LOG_FILES, ','.join(log_args)])

    if not chunks:
        chunks.append([])

    return chunks


def _get_max_args() -> int:
    try:
        # maybe there is a better way, but this seems a reliable source
        # and a manageable result
        max_args = int(os.sysconf("SC_PAGESIZES"))
    except ValueError:
        max_args = 4096

    return max_args


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
            if filepath.suffix in (".mk", ".conf", ".bi") or filepath.name == ".wato":
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


def _parse_mkp_file_parts(contents: Dict[str, Any]) -> Dict[str, Dict[str, Dict]]:
    file_list: Dict[str, Any] = {}
    for idx, file in enumerate(contents["files"]):
        path = "%s/%s" % (contents["path"], file)
        file_list[path] = {"path": path, "permissions": str(contents["permissions"][idx])}
    return file_list


def _parse_mkp_files(items: List[str], module: str, contents: Dict[str, Any], state: str,
                     package: str) -> Dict[str, Dict[str, Dict]]:
    file_list: Dict[str, Dict[str, Any]] = {}
    for file in items:
        path = "%s/local/%s/%s" % (cmk.utils.paths.omd_root, _MODULE_TO_PATH[module], file)
        file_list[path] = {
            **{col: str(contents.get(col, "N/A")) for col in _CSV_COLUMNS},
            "package": package,
            state: "YES",
            "path": path,
        }

    return file_list


def _deep_update(d1: Dict[str, Dict[str, Any]],
                 d2: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    for key in set(list(d1.keys()) + list(d2.keys())):
        if key not in d1:
            d1[key] = d2[key]
        elif key in d2:
            d1[key].update(d2[key])
    return d1


def _get_path_type(path: Path) -> str:
    if path.is_file():
        return "file"
    if path.is_dir():
        return "directory"
    if path.exists():
        return "unknown"
    return "missing"


def _filelist_to_csv_lines(dictlist: Dict[str, Dict[str, Any]]) -> Sequence[str]:
    lines = ["'%s'" % "';'".join(_CSV_COLUMNS)]
    for file_definition in dictlist.values():
        lines.append("'%s'" % "';'".join([file_definition.get(col, "N/A") for col in _CSV_COLUMNS]))
    return lines


def get_local_files_csv(infos: DiagnosticsElementJSONResult) -> DiagnosticsElementCSVResult:
    files: Dict[str, Dict[str, Any]] = {}

    # Parse different secions of the packaging output
    for (module, items) in infos["unpackaged"].items():
        files = _deep_update(files, _parse_mkp_files(items, module, {}, "unpackaged", "N/A"))
    for state in ["installed", "optional_packages"]:
        for (package, contents) in infos[state].items():
            for (module, items) in contents["files"].items():
                files = _deep_update(files, _parse_mkp_files(items, module, contents, state,
                                                             package))
    for (module, contents) in infos["parts"].items():
        files = _deep_update(files, _parse_mkp_file_parts(contents))

    # Check which files exist
    for path in files:
        files[path]["exists"] = _get_path_type(Path(path))

    return "\n".join(_filelist_to_csv_lines(files))


class CheckmkFileSensitivity(Enum):
    insensitive = 0
    sensitive = 1
    high_sensitive = 2
    unknown = 3


CheckmkFileInfo = NamedTuple("CheckmkFileInfo", [
    ("components", List[str]),
    ("sensitivity", CheckmkFileSensitivity),
    ("description", str),
])


def get_checkmk_file_sensitivity_for_humans(rel_filepath: str, file_info: CheckmkFileInfo) -> str:
    sensitivity = file_info.sensitivity
    if sensitivity == CheckmkFileSensitivity.high_sensitive:
        return "%s (H)" % rel_filepath
    if sensitivity == CheckmkFileSensitivity.sensitive:
        return "%s (M)" % rel_filepath
    # insensitive
    return "%s (L)" % rel_filepath


def get_checkmk_file_description(rel_filepath: Optional[str] = None) -> Sequence[Tuple[str, str]]:
    cmk_file_info = {**CheckmkFileInfoByNameMap, **CheckmkFileInfoByRelFilePathMap}
    if rel_filepath is not None:
        return [(rel_filepath, cmk_file_info[rel_filepath].description)]

    return [(f, d.description) for f, d in cmk_file_info.items()]


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
        description="",
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
        description="Configuration for the distributed monitoring.",
    ),
    "global.mk": CheckmkFileInfo(
        components=[
            OPT_COMP_GLOBAL_SETTINGS,
        ],
        sensitivity=CheckmkFileSensitivity(1),
        description="",
    ),
    "hosts.mk": CheckmkFileInfo(
        components=[
            OPT_COMP_HOSTS_AND_FOLDERS,
            OPT_COMP_NOTIFICATIONS,
        ],
        sensitivity=CheckmkFileSensitivity(2),
        description="Contains all hosts of a particular folder, including their attributes.",
    ),
    "rules.mk": CheckmkFileInfo(
        components=[
            OPT_COMP_HOSTS_AND_FOLDERS,
            OPT_COMP_NOTIFICATIONS,
        ],
        sensitivity=CheckmkFileSensitivity(2),
        description="Contains all rules assigned to a particular folder.",
    ),
    "tags.mk": CheckmkFileInfo(
        components=[
            OPT_COMP_HOSTS_AND_FOLDERS,
            OPT_COMP_NOTIFICATIONS,
        ],
        sensitivity=CheckmkFileSensitivity(1),
        description="Contains tag groups and auxiliary tags.",
    ),
    ".wato": CheckmkFileInfo(
        components=[
            OPT_COMP_NOTIFICATIONS,
            OPT_COMP_HOSTS_AND_FOLDERS,
        ],
        sensitivity=CheckmkFileSensitivity(0),
        description="Contains the folder properties of a particular folder.",
    ),
}

CheckmkFileInfoByRelFilePathMap: Dict[str, CheckmkFileInfo] = {
    # config files
    "conf.d/wato/alert_handlers.mk": CheckmkFileInfo(
        components=[
            OPT_COMP_NOTIFICATIONS,
        ],
        sensitivity=CheckmkFileSensitivity(2),
        description="Alert handler configuration",
    ),
    "conf.d/wato/contacts.mk": CheckmkFileInfo(
        components=[
            OPT_COMP_NOTIFICATIONS,
        ],
        sensitivity=CheckmkFileSensitivity(2),
        description="Contains users and their properties.",
    ),
    "conf.d/wato/global.mk": CheckmkFileInfo(
        components=[
            OPT_COMP_NOTIFICATIONS,
        ],
        sensitivity=CheckmkFileSensitivity(1),
        description="Contains the global settings of a site.",
    ),
    "conf.d/wato/groups.mk": CheckmkFileInfo(
        components=[
            OPT_COMP_NOTIFICATIONS,
        ],
        sensitivity=CheckmkFileSensitivity(0),
        description="Contains the contact groups.",
    ),
    "conf.d/wato/notifications.mk": CheckmkFileInfo(
        components=[
            OPT_COMP_NOTIFICATIONS,
        ],
        sensitivity=CheckmkFileSensitivity(2),
        description="Contains the notification rules.",
    ),
    "main.mk": CheckmkFileInfo(
        components=[
            OPT_COMP_NOTIFICATIONS,
        ],
        sensitivity=CheckmkFileSensitivity(0),
        description=
        "The main config file, which is used if you don't use the Setup features of the GUI.",
    ),
    "mknotifyd.d/wato/global.mk": CheckmkFileInfo(
        components=[
            OPT_COMP_NOTIFICATIONS,
        ],
        sensitivity=CheckmkFileSensitivity(1),
        description="Contains the notification spooler's global settings.",
    ),
    "multisite.d/wato/bi_config.bi": CheckmkFileInfo(
        components=[
            OPT_COMP_BUSINESS_INTELLIGENCE,
        ],
        sensitivity=CheckmkFileSensitivity(1),
        description="Contains the Business Intelligence rules and aggregations.",
    ),
    "multisite.d/wato/global.mk": CheckmkFileInfo(
        components=[
            OPT_COMP_NOTIFICATIONS,
        ],
        sensitivity=CheckmkFileSensitivity(1),
        description="Contains GUI related global settings.",
    ),
    "multisite.d/wato/groups.mk": CheckmkFileInfo(
        components=[
            OPT_COMP_NOTIFICATIONS,
        ],
        sensitivity=CheckmkFileSensitivity(0),
        description="Contains GUI related contact group properties.",
    ),
    "multisite.d/wato/users.mk": CheckmkFileInfo(
        components=[
            OPT_COMP_NOTIFICATIONS,
        ],
        sensitivity=CheckmkFileSensitivity(2),
        description="Contains GUI related user properties.",
    ),
    # Log files
    "cmc.log": CheckmkFileInfo(
        components=[
            OPT_COMP_NOTIFICATIONS,
        ],
        sensitivity=CheckmkFileSensitivity(1),
        description=
        "In this file messages from starting and stopping the CMC can be found, as well as general warnings and error messages related to the core and the check helpers.",
    ),
    "web.log": CheckmkFileInfo(
        components=[
            OPT_COMP_NOTIFICATIONS,
        ],
        sensitivity=CheckmkFileSensitivity(1),
        description=
        "The log file of the checkmk weg gui. Here you can find all kind of automations call, ldap sync and some failing GUI extensions.",
    ),
    "liveproxyd.log": CheckmkFileInfo(
        components=[],
        sensitivity=CheckmkFileSensitivity(1),
        description="Log file for the Livestatus proxies.",
    ),
    "liveproxyd.state": CheckmkFileInfo(
        components=[],
        sensitivity=CheckmkFileSensitivity(1),
        description=
        "The current state of the Livestatus proxies in a readable form. This file is updated every 5 seconds.",
    ),
    "mknotifyd.log": CheckmkFileInfo(
        components=[
            OPT_COMP_NOTIFICATIONS,
        ],
        sensitivity=CheckmkFileSensitivity(1),
        description="The notification spooler’s log file.",
    ),
    "mknotifyd.state": CheckmkFileInfo(
        components=[
            OPT_COMP_NOTIFICATIONS,
        ],
        sensitivity=CheckmkFileSensitivity(1),
        description=
        "The current status of the notification spooler. This is primarily relevant for notifications in distributed environments.",
    ),
    "notify.log": CheckmkFileInfo(
        components=[
            OPT_COMP_NOTIFICATIONS,
        ],
        sensitivity=CheckmkFileSensitivity(1),
        description=
        "The notification module’s log file. This will show you the rule based processing of the notifications.",
    ),
    "apache/access_log": CheckmkFileInfo(
        components=[],
        sensitivity=CheckmkFileSensitivity(2),
        description="This log file contains all requests that are sent to the site's apache server.",
    ),
    "apache/error_log": CheckmkFileInfo(
        components=[],
        sensitivity=CheckmkFileSensitivity(1),
        description=
        "this log file contains all errors that occur when requests are sent to the site's apache server.",
    ),
    "dcd.log": CheckmkFileInfo(
        components=[],
        sensitivity=CheckmkFileSensitivity(1),
        description="The log file for the Dynamic Configuration Daemon (DCD).",
    ),
    "alerts.log": CheckmkFileInfo(
        components=[],
        sensitivity=CheckmkFileSensitivity(1),
        description=
        "Log file with all events relevant to the alert handler (logged by the alert helper).",
    ),
    "diskspace.log": CheckmkFileInfo(
        components=[],
        sensitivity=CheckmkFileSensitivity(0),
        description="The log file of the automatic disk space cleanup.",
    ),
    "mkeventd.log": CheckmkFileInfo(
        components=[],
        sensitivity=CheckmkFileSensitivity(1),
        description=
        "The event console log file. This will show you the processing of the incoming messages, matching of the rule packs and the processing of the matched mibs.",
    ),
    "rrdcached.log": CheckmkFileInfo(
        components=[],
        sensitivity=CheckmkFileSensitivity(1),
        description="The log file of the rrd cache daemon.",
    ),
    "redis-server.log": CheckmkFileInfo(
        components=[],
        sensitivity=CheckmkFileSensitivity(1),
        description="The log file of the redis-server of the Checkmk instance.",
    ),
    "agent-receiver/access.log": CheckmkFileInfo(
        components=[],
        sensitivity=CheckmkFileSensitivity(1),
        description="",
    ),
    "agent-receiver/agent-receiver.log": CheckmkFileInfo(
        components=[],
        sensitivity=CheckmkFileSensitivity(1),
        description="",
    ),
    "agent-receiver/error.log": CheckmkFileInfo(
        components=[],
        sensitivity=CheckmkFileSensitivity(1),
        description="",
    ),
    "agent-registration.log": CheckmkFileInfo(
        components=[],
        sensitivity=CheckmkFileSensitivity(1),
        description="",
    ),
}
