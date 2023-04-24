#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
from collections.abc import Iterator, Mapping, Sequence
from enum import Enum
from pathlib import Path
from typing import Any, Literal, NamedTuple, TypedDict, Union

from livestatus import SiteId

import cmk.utils.paths

# This is an awful type, but just putting `Any` and hoping for the best is no solution.
_JSONSerializable = Union[
    str,
    list[str],
    list[tuple[str, bool]],
    Mapping[str, str],
    Mapping[str, list[str]],
]

DiagnosticsCLParameters = list[str]
DiagnosticsModesParameters = dict[str, Any]
DiagnosticsOptionalParameters = dict[str, Any]
CheckmkFilesMap = dict[str, Path]
DiagnosticsElementJSONResult = Mapping[str, _JSONSerializable]
DiagnosticsElementCSVResult = str
DiagnosticsElementFilepaths = Iterator[Path]


class DiagnosticsParameters(TypedDict):
    site: SiteId
    general: Literal[True]
    opt_info: DiagnosticsOptionalParameters | None
    comp_specific: DiagnosticsOptionalParameters | None


OPT_LOCAL_FILES = "local-files"
OPT_OMD_CONFIG = "omd-config"
OPT_CHECKMK_OVERVIEW = "checkmk-overview"
OPT_CHECKMK_CONFIG_FILES = "checkmk-config-files"
OPT_CHECKMK_CORE_FILES = "checkmk-core-files"
OPT_CHECKMK_LICENSING_FILES = "checkmk-licensing-files"
OPT_CHECKMK_LOG_FILES = "checkmk-log-files"

# CEE specific options
OPT_PERFORMANCE_GRAPHS = "performance-graphs"

# GUI, component specific options
OPT_COMP_GLOBAL_SETTINGS = "global-settings"
OPT_COMP_HOSTS_AND_FOLDERS = "hosts-and-folders"
OPT_COMP_NOTIFICATIONS = "notifications"
OPT_COMP_BUSINESS_INTELLIGENCE = "business-intelligence"
OPT_COMP_CMC = "cmc"
OPT_COMP_LICENSING = "licensing"

_BOOLEAN_CONFIG_OPTS = [
    OPT_LOCAL_FILES,
    OPT_OMD_CONFIG,
    OPT_PERFORMANCE_GRAPHS,
    OPT_CHECKMK_OVERVIEW,
]

_FILES_OPTS = [
    OPT_CHECKMK_CONFIG_FILES,
    OPT_CHECKMK_CORE_FILES,
    OPT_CHECKMK_LICENSING_FILES,
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


def serialize_wato_parameters(  # pylint: disable=too-many-branches
    wato_parameters: DiagnosticsParameters,
) -> list[DiagnosticsCLParameters]:
    # TODO: reduce the number of branches and do the whole procedure in a more generic/elegant way

    parameters = {}

    opt_info_parameters = wato_parameters.get("opt_info")
    if opt_info_parameters is not None:
        parameters.update(opt_info_parameters)

    comp_specific_parameters = wato_parameters.get("comp_specific")
    if comp_specific_parameters is not None:
        parameters.update(comp_specific_parameters)

    boolean_opts: list[str] = [
        k for k in sorted(parameters.keys()) if k in _BOOLEAN_CONFIG_OPTS and parameters[k]
    ]

    config_files: set[str] = set()
    core_files: set[str] = set()
    licensing_files: set[str] = set()
    log_files: set[str] = set()

    for key, value in sorted(parameters.items()):
        if key == OPT_CHECKMK_CONFIG_FILES:
            config_files |= _extract_list_of_files(value)

        elif key == OPT_CHECKMK_CORE_FILES:
            core_files |= _extract_list_of_files(value)

        elif key == OPT_CHECKMK_LICENSING_FILES:
            licensing_files |= _extract_list_of_files(value)

        elif key == OPT_CHECKMK_LOG_FILES:
            log_files |= _extract_list_of_files(value)

        elif key in [
            OPT_COMP_GLOBAL_SETTINGS,
            OPT_COMP_HOSTS_AND_FOLDERS,
            OPT_COMP_NOTIFICATIONS,
            OPT_COMP_BUSINESS_INTELLIGENCE,
            OPT_COMP_CMC,
            OPT_COMP_LICENSING,
        ]:
            config_files |= _extract_list_of_files(value.get("config_files"))
            core_files |= _extract_list_of_files(value.get("core_files"))
            licensing_files |= _extract_list_of_files(value.get("licensing_files"))
            log_files |= _extract_list_of_files(value.get("log_files"))

    chunks: list[list[str]] = []
    if boolean_opts:
        chunks.append(boolean_opts)

    max_args: int = _get_max_args() - 1  # OPT will be appended in for loop
    for config_args in [
        sorted(config_files)[i : i + max_args]
        for i in range(0, len(sorted(config_files)), max_args)
    ]:
        chunks.append([OPT_CHECKMK_CONFIG_FILES, ",".join(config_args)])

    for core_args in [
        sorted(core_files)[i : i + max_args] for i in range(0, len(sorted(core_files)), max_args)
    ]:
        chunks.append([OPT_CHECKMK_CORE_FILES, ",".join(core_args)])

    for licensing_args in [
        sorted(licensing_files)[i : i + max_args]
        for i in range(0, len(sorted(licensing_files)), max_args)
    ]:
        chunks.append([OPT_CHECKMK_LICENSING_FILES, ",".join(licensing_args)])

    for log_args in [
        sorted(log_files)[i : i + max_args] for i in range(0, len(sorted(log_files)), max_args)
    ]:
        chunks.append([OPT_CHECKMK_LOG_FILES, ",".join(log_args)])

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


def _extract_list_of_files(value: tuple[str, list[str]] | None) -> set[str]:
    if value is None:
        return set()
    return set(value[1])


def deserialize_cl_parameters(
    cl_parameters: DiagnosticsCLParameters,
) -> DiagnosticsOptionalParameters:
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
    modes_parameters: DiagnosticsModesParameters,
) -> DiagnosticsOptionalParameters:
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


def get_checkmk_core_files_map() -> CheckmkFilesMap:
    files_map: CheckmkFilesMap = {}
    for root, _dirs, files in os.walk(cmk.utils.paths.var_dir + "/core"):
        for file_name in files:
            filepath = Path(root).joinpath(file_name)
            if filepath.stem in ("state", "history", "config"):
                rel_filepath = str(filepath.relative_to(cmk.utils.paths.var_dir))
                files_map.setdefault(rel_filepath, filepath)
    return files_map


def get_checkmk_licensing_files_map() -> CheckmkFilesMap:
    files_map: CheckmkFilesMap = {}
    for root, _dirs, files in os.walk(cmk.utils.paths.var_dir + "/licensing"):
        for file_name in files:
            filepath = Path(root).joinpath(file_name)
            rel_filepath = str(filepath.relative_to(cmk.utils.paths.var_dir))
            files_map.setdefault(rel_filepath, filepath)
    return files_map


def get_checkmk_log_files_map() -> CheckmkFilesMap:
    files_map: CheckmkFilesMap = {}
    for root, _dirs, files in os.walk(cmk.utils.paths.log_dir):
        for file_name in files:
            filepath = Path(root).joinpath(file_name)
            if filepath.suffix in (".log", ".state") or filepath.name in (
                "access_log",
                "error_log",
                "stats",
            ):
                rel_filepath = str(filepath.relative_to(cmk.utils.paths.log_dir))
                files_map.setdefault(rel_filepath, filepath)
    return files_map


class CheckmkFileSensitivity(Enum):
    insensitive = 0
    sensitive = 1
    high_sensitive = 2
    unknown = 3


class CheckmkFileInfo(NamedTuple):
    components: list[str]
    sensitivity: CheckmkFileSensitivity
    description: str


def get_checkmk_file_sensitivity_for_humans(rel_filepath: str, file_info: CheckmkFileInfo) -> str:
    sensitivity = file_info.sensitivity
    if sensitivity == CheckmkFileSensitivity.high_sensitive:
        return "%s (H)" % rel_filepath
    if sensitivity == CheckmkFileSensitivity.sensitive:
        return "%s (M)" % rel_filepath
    # insensitive
    return "%s (L)" % rel_filepath


def get_checkmk_file_description(rel_filepath: str | None = None) -> Sequence[tuple[str, str]]:
    cmk_file_info = {**CheckmkFileInfoByNameMap, **CheckmkFileInfoByRelFilePathMap}
    if rel_filepath is not None:
        return [(rel_filepath, cmk_file_info[rel_filepath].description)]

    return [(f, d.description) for f, d in cmk_file_info.items()]


def get_checkmk_file_info(rel_filepath: str, component: str | None = None) -> CheckmkFileInfo:
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

    return CheckmkFileInfo(components=[], sensitivity=CheckmkFileSensitivity(3), description="")


# Feel free to extend the maps:
# - config file entries are relative to "etc/check_mk".
# - log file entries are relative to "var/log".
CheckmkFileInfoByNameMap: dict[str, CheckmkFileInfo] = {
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

CheckmkFileInfoByRelFilePathMap: dict[str, CheckmkFileInfo] = {
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
    "licensing.d/notification_settings.mk": CheckmkFileInfo(
        components=[
            OPT_COMP_LICENSING,
        ],
        sensitivity=CheckmkFileSensitivity(1),
        description="Contains set of users to be notified on licensing situations.",
    ),
    "main.mk": CheckmkFileInfo(
        components=[
            OPT_COMP_NOTIFICATIONS,
        ],
        sensitivity=CheckmkFileSensitivity(0),
        description="The main config file, which is used if you don't use the Setup features of the GUI.",
    ),
    "mknotifyd.d/wato/global.mk": CheckmkFileInfo(
        components=[
            OPT_COMP_NOTIFICATIONS,
        ],
        sensitivity=CheckmkFileSensitivity(1),
        description="Contains the notification spooler's global settings.",
    ),
    "multisite.d/licensing_settings.mk": CheckmkFileInfo(
        components=[
            OPT_COMP_LICENSING,
        ],
        sensitivity=CheckmkFileSensitivity(1),
        description="Contains licensing related settings for mode of connection, e.g. online verification, credentials, etc.",
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
    # Core files
    "core/config.pb": CheckmkFileInfo(
        components=[
            OPT_COMP_CMC,
        ],
        sensitivity=CheckmkFileSensitivity(1),
        description="Contains the current configuration of the core in the protobuff format.",
    ),
    "core/state": CheckmkFileInfo(
        components=[
            OPT_COMP_CMC,
        ],
        sensitivity=CheckmkFileSensitivity(1),
        description="Contains the current status of the core.",
    ),
    "core/state.pb": CheckmkFileInfo(
        components=[
            OPT_COMP_CMC,
            OPT_COMP_LICENSING,
        ],
        sensitivity=CheckmkFileSensitivity(1),
        description="Contains the current status of the core in the protobuff format.",
    ),
    "core/history": CheckmkFileInfo(
        components=[
            OPT_COMP_CMC,
        ],
        sensitivity=CheckmkFileSensitivity(1),
        description="Contains the latest state history of all hosts and services.",
    ),
    # Licensing files
    "licensing/extensions.json": CheckmkFileInfo(
        components=[
            OPT_COMP_LICENSING,
        ],
        sensitivity=CheckmkFileSensitivity(0),
        description="Extends the information in history.json.",
    ),
    "licensing/history.json": CheckmkFileInfo(
        components=[
            OPT_COMP_LICENSING,
        ],
        sensitivity=CheckmkFileSensitivity(0),
        description="Contains information about the licensing samples.",
    ),
    "licensing/next_online_verification": CheckmkFileInfo(
        components=[
            OPT_COMP_LICENSING,
        ],
        sensitivity=CheckmkFileSensitivity(0),
        description="Contains timing information about the licensing samples.",
    ),
    "licensing/verification_request_id": CheckmkFileInfo(
        components=[
            OPT_COMP_LICENSING,
        ],
        sensitivity=CheckmkFileSensitivity(0),
        description="Stores the request id of each verification request against the license server.",
    ),
    "licensing/verification_response": CheckmkFileInfo(
        components=[
            OPT_COMP_LICENSING,
        ],
        sensitivity=CheckmkFileSensitivity(0),
        description="Contains the raw response from license server.",
    ),
    "licensing/verification_result.json": CheckmkFileInfo(
        components=[
            OPT_COMP_LICENSING,
        ],
        sensitivity=CheckmkFileSensitivity(0),
        description="Contains the last licensing verification result.",
    ),
    # Log files
    "cmc.log": CheckmkFileInfo(
        components=[
            OPT_COMP_NOTIFICATIONS,
            OPT_COMP_CMC,
        ],
        sensitivity=CheckmkFileSensitivity(1),
        description="In this file messages from starting and stopping the CMC can be found, as well as general warnings and error messages related to the core and the check helpers.",
    ),
    "web.log": CheckmkFileInfo(
        components=[
            OPT_COMP_NOTIFICATIONS,
            OPT_COMP_LICENSING,
        ],
        sensitivity=CheckmkFileSensitivity(1),
        description="The log file of the checkmk weg gui. Here you can find all kind of automations call, ldap sync and some failing GUI extensions.",
    ),
    "liveproxyd.log": CheckmkFileInfo(
        components=[
            OPT_COMP_CMC,
        ],
        sensitivity=CheckmkFileSensitivity(1),
        description="Log file for the Livestatus proxies.",
    ),
    "liveproxyd.state": CheckmkFileInfo(
        components=[
            OPT_COMP_CMC,
        ],
        sensitivity=CheckmkFileSensitivity(1),
        description="The current state of the Livestatus proxies in a readable form. This file is updated every 5 seconds.",
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
        description="The current status of the notification spooler. This is primarily relevant for notifications in distributed environments.",
    ),
    "notify.log": CheckmkFileInfo(
        components=[
            OPT_COMP_NOTIFICATIONS,
        ],
        sensitivity=CheckmkFileSensitivity(1),
        description="The notification module’s log file. This will show you the rule based processing of the notifications.",
    ),
    "apache/access_log": CheckmkFileInfo(
        components=[],
        sensitivity=CheckmkFileSensitivity(2),
        description="This log file contains all requests that are sent to the site's apache server.",
    ),
    "apache/error_log": CheckmkFileInfo(
        components=[
            OPT_COMP_LICENSING,
        ],
        sensitivity=CheckmkFileSensitivity(1),
        description="this log file contains all errors that occur when requests are sent to the site's apache server.",
    ),
    "dcd.log": CheckmkFileInfo(
        components=[],
        sensitivity=CheckmkFileSensitivity(1),
        description="The log file for the Dynamic Configuration Daemon (DCD).",
    ),
    "alerts.log": CheckmkFileInfo(
        components=[],
        sensitivity=CheckmkFileSensitivity(1),
        description="Log file with all events relevant to the alert handler (logged by the alert helper).",
    ),
    "diskspace.log": CheckmkFileInfo(
        components=[],
        sensitivity=CheckmkFileSensitivity(0),
        description="The log file of the automatic disk space cleanup.",
    ),
    "mkeventd.log": CheckmkFileInfo(
        components=[],
        sensitivity=CheckmkFileSensitivity(1),
        description="The event console log file. This will show you the processing of the incoming messages, matching of the rule packs and the processing of the matched mibs.",
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
    "licensing.log": CheckmkFileInfo(
        components=[
            OPT_COMP_LICENSING,
        ],
        sensitivity=CheckmkFileSensitivity(1),
        description="",
    ),
}
