#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
import re
from collections.abc import Iterator, Mapping, Sequence
from enum import auto, Enum
from pathlib import Path
from typing import Any, Literal, NamedTuple, TypedDict

from cmk.ccc.site import SiteId

import cmk.utils.paths
from cmk.utils.structured_data import SDRawTree

# This is an awful type, but just putting `Any` and hoping for the best is no solution.
_JSONSerializable = (
    str | float | list[str] | list[tuple[str, bool]] | Mapping[str, str] | Mapping[str, list[str]]
)

DiagnosticsCLParameters = list[str]
DiagnosticsModesParameters = dict[str, Any]
DiagnosticsOptionalParameters = dict[str, Any]
CheckmkFilesMap = dict[str, Path]
DiagnosticsElementJSONResult = Mapping[str, _JSONSerializable] | SDRawTree
DiagnosticsElementCSVResult = str
DiagnosticsElementFilepaths = Iterator[Path]


class DiagnosticsParameters(TypedDict):
    site: SiteId
    general: Literal[True]
    timeout: int
    opt_info: DiagnosticsOptionalParameters | None
    comp_specific: DiagnosticsOptionalParameters | None
    checkmk_server_host: str


OPT_BI_RUNTIME_DATA = "bi-runtime-data"
OPT_LOCAL_FILES = "local-files"
OPT_OMD_CONFIG = "omd-config"
OPT_CHECKMK_OVERVIEW = "checkmk-overview"
OPT_CHECKMK_CRASH_REPORTS = "checkmk-crashes"
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

_OPTS_WITH_HOST = [
    OPT_PERFORMANCE_GRAPHS,
    OPT_CHECKMK_OVERVIEW,
]

_BOOLEAN_CONFIG_OPTS = [
    OPT_BI_RUNTIME_DATA,
    OPT_LOCAL_FILES,
    OPT_OMD_CONFIG,
    OPT_CHECKMK_CRASH_REPORTS,
]

_FILES_OPTS = [
    OPT_CHECKMK_CONFIG_FILES,
    OPT_CHECKMK_CORE_FILES,
    OPT_CHECKMK_LICENSING_FILES,
    OPT_CHECKMK_LOG_FILES,
]


def serialize_wato_parameters(  # pylint: disable=R0912
    wato_parameters: DiagnosticsParameters,
) -> list[DiagnosticsCLParameters]:
    # TODO: reduce the number of branches and do the whole procedure in a more generic/elegant way

    parameters: dict[str, Any] = {}

    opt_info_parameters = wato_parameters.get("opt_info")
    if opt_info_parameters is not None:
        parameters |= opt_info_parameters

    boolean_opts: list[str] = [
        k for k in sorted(parameters.keys()) if k in _BOOLEAN_CONFIG_OPTS and parameters[k]
    ]

    comp_specific_parameters = wato_parameters.get("comp_specific")
    if comp_specific_parameters is not None:
        parameters.update(comp_specific_parameters)

        if comp_specific_parameters.get(OPT_COMP_BUSINESS_INTELLIGENCE, {}).pop(
            OPT_BI_RUNTIME_DATA, None
        ):
            boolean_opts.append(OPT_BI_RUNTIME_DATA)

    opt_checkmk_server_host = wato_parameters.get("checkmk_server_host", "")

    opts_with_host: list[list[str]] = [
        [k, opt_checkmk_server_host] for k in _OPTS_WITH_HOST if k in parameters
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

    for opt in opts_with_host:
        chunks.append(opt)

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
    return set() if value is None else set(value[1])


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

            elif parameter in _OPTS_WITH_HOST:
                deserialized_parameters[parameter] = next(parameters)

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
        if key in _BOOLEAN_CONFIG_OPTS or key in _OPTS_WITH_HOST:
            deserialized_parameters[key] = value

        elif key in _FILES_OPTS:
            deserialized_parameters[key] = value.split(",")

    return deserialized_parameters


def get_checkmk_config_files_map() -> CheckmkFilesMap:
    files_map: CheckmkFilesMap = {}
    for root, _dirs, files in os.walk(str(cmk.utils.paths.default_config_dir)):
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
    for root, _dirs, files in os.walk(str(cmk.utils.paths.var_dir / "core")):
        for file_name in files:
            filepath = Path(root).joinpath(file_name)
            if filepath.stem in ("state", "history", "config"):
                rel_filepath = str(filepath.relative_to(cmk.utils.paths.var_dir))
                files_map.setdefault(rel_filepath, filepath)
    return files_map


def get_checkmk_licensing_files_map() -> CheckmkFilesMap:
    files_map: CheckmkFilesMap = {}
    for root, _dirs, files in os.walk(str(cmk.utils.paths.var_dir / "licensing")):
        for file_name in files:
            filepath = Path(root).joinpath(file_name)
            rel_filepath = str(filepath.relative_to(cmk.utils.paths.var_dir))
            files_map.setdefault(rel_filepath, filepath)
    return files_map


def get_checkmk_log_files_map() -> CheckmkFilesMap:
    files_map: CheckmkFilesMap = {}
    for root, _dirs, files in os.walk(str(cmk.utils.paths.log_dir)):
        for file_name in files:
            filepath = Path(root) / file_name
            if (
                filepath.suffix in (".log", ".1", ".state")
                or filepath.name
                in (
                    "access_log",
                    "error_log",
                    "stats",
                )
                or filepath.name.startswith("update.log")
            ):
                rel_filepath = str(filepath.relative_to(cmk.utils.paths.log_dir))
                files_map.setdefault(rel_filepath, filepath)
    return files_map


class CheckmkFileEncryption(Enum):
    none = auto()
    rot47 = auto()


class CheckmkFileSensitivity(Enum):
    insensitive = auto()
    sensitive = auto()
    high_sensitive = auto()
    unknown = auto()


class CheckmkFileInfo(NamedTuple):
    components: list[str]
    sensitivity: CheckmkFileSensitivity
    description: str
    encryption: CheckmkFileEncryption


def get_checkmk_file_sensitivity_for_humans(rel_filepath: str, file_info: CheckmkFileInfo) -> str:
    sensitivity = file_info.sensitivity
    return f"{rel_filepath} {_get_sensitivity_suffix(sensitivity)}"


def _get_sensitivity_suffix(sensitivity: CheckmkFileSensitivity) -> str:
    match sensitivity:
        case CheckmkFileSensitivity.high_sensitive:
            return "(H)"
        case CheckmkFileSensitivity.sensitive:
            return "(M)"
        case _:  # insensitive
            return "(L)"


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
    #
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

    # update.log.2.gz -> update.log
    rel_filepath = re.sub(r"\.[0-9]+(\.gz)?", "", rel_filepath)

    file_info_by_name = CheckmkFileInfoByNameMap.get(Path(rel_filepath).name)
    if file_info_by_name is not None and (
        component is None or component in file_info_by_name.components
    ):
        return file_info_by_name

    file_info_by_rel_filepath = CheckmkFileInfoByRelFilePathMap.get(rel_filepath)
    if file_info_by_rel_filepath is not None and (
        component is None or component in file_info_by_rel_filepath.components
    ):
        return file_info_by_rel_filepath

    return CheckmkFileInfo(
        components=[],
        sensitivity=CheckmkFileSensitivity.unknown,
        description="",
        encryption=CheckmkFileEncryption.none,
    )


# Feel free to extend the maps:
# - config file entries are relative to "etc/check_mk".
# - log file entries are relative to "var/log".
CheckmkFileInfoByNameMap: dict[str, CheckmkFileInfo] = {
    # config files
    "sites.mk": CheckmkFileInfo(
        components=[
            OPT_COMP_GLOBAL_SETTINGS,
        ],
        sensitivity=CheckmkFileSensitivity.insensitive,
        encryption=CheckmkFileEncryption.none,
        description="Configuration for the distributed monitoring.",
    ),
    "global.mk": CheckmkFileInfo(
        components=[
            OPT_COMP_GLOBAL_SETTINGS,
        ],
        sensitivity=CheckmkFileSensitivity.sensitive,
        description="",
        encryption=CheckmkFileEncryption.none,
    ),
    "hosts.mk": CheckmkFileInfo(
        components=[
            OPT_COMP_HOSTS_AND_FOLDERS,
            OPT_COMP_NOTIFICATIONS,
        ],
        sensitivity=CheckmkFileSensitivity.high_sensitive,
        description="Contains all hosts of a particular folder, including their attributes.",
        encryption=CheckmkFileEncryption.none,
    ),
    "rules.mk": CheckmkFileInfo(
        components=[
            OPT_COMP_HOSTS_AND_FOLDERS,
            OPT_COMP_NOTIFICATIONS,
        ],
        sensitivity=CheckmkFileSensitivity.high_sensitive,
        description="Contains all rules assigned to a particular folder.",
        encryption=CheckmkFileEncryption.none,
    ),
    "tags.mk": CheckmkFileInfo(
        components=[
            OPT_COMP_HOSTS_AND_FOLDERS,
            OPT_COMP_NOTIFICATIONS,
        ],
        sensitivity=CheckmkFileSensitivity.sensitive,
        description="Contains tag groups and auxiliary tags.",
        encryption=CheckmkFileEncryption.none,
    ),
    ".wato": CheckmkFileInfo(
        components=[
            OPT_COMP_NOTIFICATIONS,
            OPT_COMP_HOSTS_AND_FOLDERS,
        ],
        sensitivity=CheckmkFileSensitivity.insensitive,
        description="Contains the folder properties of a particular folder.",
        encryption=CheckmkFileEncryption.none,
    ),
}

CheckmkFileInfoByRelFilePathMap: dict[str, CheckmkFileInfo] = {
    # config files
    "conf.d/wato/alert_handlers.mk": CheckmkFileInfo(
        components=[
            OPT_COMP_NOTIFICATIONS,
        ],
        sensitivity=CheckmkFileSensitivity.high_sensitive,
        description="Alert handler configuration",
        encryption=CheckmkFileEncryption.none,
    ),
    "conf.d/wato/contacts.mk": CheckmkFileInfo(
        components=[
            OPT_COMP_NOTIFICATIONS,
        ],
        sensitivity=CheckmkFileSensitivity.high_sensitive,
        description="Contains users and their properties.",
        encryption=CheckmkFileEncryption.none,
    ),
    "conf.d/wato/global.mk": CheckmkFileInfo(
        components=[
            OPT_COMP_NOTIFICATIONS,
        ],
        sensitivity=CheckmkFileSensitivity.sensitive,
        description="Contains the global settings of a site.",
        encryption=CheckmkFileEncryption.none,
    ),
    "conf.d/wato/groups.mk": CheckmkFileInfo(
        components=[
            OPT_COMP_NOTIFICATIONS,
        ],
        sensitivity=CheckmkFileSensitivity.insensitive,
        description="Contains the contact groups.",
        encryption=CheckmkFileEncryption.none,
    ),
    "conf.d/wato/notifications.mk": CheckmkFileInfo(
        components=[
            OPT_COMP_NOTIFICATIONS,
        ],
        sensitivity=CheckmkFileSensitivity.high_sensitive,
        description="Contains the notification rules.",
        encryption=CheckmkFileEncryption.none,
    ),
    "licensing.d/notification_settings.mk": CheckmkFileInfo(
        components=[
            OPT_COMP_LICENSING,
        ],
        sensitivity=CheckmkFileSensitivity.sensitive,
        description="Contains set of users to be notified on licensing situations.",
        encryption=CheckmkFileEncryption.none,
    ),
    "main.mk": CheckmkFileInfo(
        components=[
            OPT_COMP_NOTIFICATIONS,
        ],
        sensitivity=CheckmkFileSensitivity.insensitive,
        description="The main config file, which is used if you don't use the Setup features of the GUI.",
        encryption=CheckmkFileEncryption.none,
    ),
    "mknotifyd.d/wato/global.mk": CheckmkFileInfo(
        components=[
            OPT_COMP_NOTIFICATIONS,
        ],
        sensitivity=CheckmkFileSensitivity.sensitive,
        description="Contains the notification spooler's global settings.",
        encryption=CheckmkFileEncryption.none,
    ),
    "multisite.d/licensing_settings.mk": CheckmkFileInfo(
        components=[
            OPT_COMP_LICENSING,
        ],
        sensitivity=CheckmkFileSensitivity.sensitive,
        description="Contains licensing related settings for mode of connection, e.g. online verification, credentials, etc.",
        encryption=CheckmkFileEncryption.none,
    ),
    "multisite.d/wato/bi_config.bi": CheckmkFileInfo(
        components=[
            OPT_COMP_BUSINESS_INTELLIGENCE,
        ],
        sensitivity=CheckmkFileSensitivity.sensitive,
        description="Contains the Business Intelligence rules and aggregations.",
        encryption=CheckmkFileEncryption.none,
    ),
    "multisite.d/wato/global.mk": CheckmkFileInfo(
        components=[
            OPT_COMP_NOTIFICATIONS,
        ],
        sensitivity=CheckmkFileSensitivity.sensitive,
        description="Contains GUI related global settings.",
        encryption=CheckmkFileEncryption.none,
    ),
    "multisite.d/wato/groups.mk": CheckmkFileInfo(
        components=[
            OPT_COMP_NOTIFICATIONS,
        ],
        sensitivity=CheckmkFileSensitivity.insensitive,
        description="Contains GUI related contact group properties.",
        encryption=CheckmkFileEncryption.none,
    ),
    "multisite.d/wato/users.mk": CheckmkFileInfo(
        components=[
            OPT_COMP_NOTIFICATIONS,
        ],
        sensitivity=CheckmkFileSensitivity.high_sensitive,
        description="Contains GUI related user properties.",
        encryption=CheckmkFileEncryption.none,
    ),
    "multisite.d/wato/user_connections.mk": CheckmkFileInfo(
        components=[],
        sensitivity=CheckmkFileSensitivity.high_sensitive,
        description="Contains GUI related user properties.",
        encryption=CheckmkFileEncryption.none,
    ),
    # Core files
    "core/config.pb": CheckmkFileInfo(
        components=[
            OPT_COMP_CMC,
        ],
        sensitivity=CheckmkFileSensitivity.sensitive,
        description="Contains the current configuration of the core in the protobuff format.",
        encryption=CheckmkFileEncryption.none,
    ),
    "core/state": CheckmkFileInfo(
        components=[
            OPT_COMP_CMC,
        ],
        sensitivity=CheckmkFileSensitivity.sensitive,
        description="Contains the current status of the core.",
        encryption=CheckmkFileEncryption.none,
    ),
    "core/state.pb": CheckmkFileInfo(
        components=[
            OPT_COMP_CMC,
            OPT_COMP_LICENSING,
        ],
        sensitivity=CheckmkFileSensitivity.sensitive,
        description="Contains the current status of the core in the protobuff format.",
        encryption=CheckmkFileEncryption.none,
    ),
    "core/history": CheckmkFileInfo(
        components=[
            OPT_COMP_CMC,
        ],
        sensitivity=CheckmkFileSensitivity.sensitive,
        description="Contains the latest state history of all hosts and services.",
        encryption=CheckmkFileEncryption.none,
    ),
    # Licensing files
    "licensing/extensions.json": CheckmkFileInfo(
        components=[
            OPT_COMP_LICENSING,
        ],
        sensitivity=CheckmkFileSensitivity.insensitive,
        description="Extends the information in history.json.",
        encryption=CheckmkFileEncryption.rot47,
    ),
    "licensing/history.json": CheckmkFileInfo(
        components=[
            OPT_COMP_LICENSING,
        ],
        sensitivity=CheckmkFileSensitivity.insensitive,
        description="Contains information about the licensing samples.",
        encryption=CheckmkFileEncryption.rot47,
    ),
    "licensing/next_online_verification": CheckmkFileInfo(
        components=[
            OPT_COMP_LICENSING,
        ],
        sensitivity=CheckmkFileSensitivity.insensitive,
        description="Contains timing information about the licensing samples.",
        encryption=CheckmkFileEncryption.none,
    ),
    "licensing/verification_request_id": CheckmkFileInfo(
        components=[
            OPT_COMP_LICENSING,
        ],
        sensitivity=CheckmkFileSensitivity.insensitive,
        description="Stores the request id of each verification request against the license server.",
        encryption=CheckmkFileEncryption.none,
    ),
    "licensing/verification_response": CheckmkFileInfo(
        components=[
            OPT_COMP_LICENSING,
        ],
        sensitivity=CheckmkFileSensitivity.insensitive,
        description="Contains the raw response from license server.",
        encryption=CheckmkFileEncryption.none,
    ),
    "licensing/verification_result.json": CheckmkFileInfo(
        components=[
            OPT_COMP_LICENSING,
        ],
        sensitivity=CheckmkFileSensitivity.insensitive,
        description="Contains the last licensing verification result.",
        encryption=CheckmkFileEncryption.none,
    ),
    "licensing/state_file_created": CheckmkFileInfo(
        components=[
            OPT_COMP_LICENSING,
        ],
        sensitivity=CheckmkFileSensitivity.insensitive,
        description="Contains the trial start date.",
        encryption=CheckmkFileEncryption.none,
    ),
    "licensing/licensed_state": CheckmkFileInfo(
        components=[
            OPT_COMP_LICENSING,
        ],
        sensitivity=CheckmkFileSensitivity.insensitive,
        description="Contains the licensed state for CMC/NEB.",
        encryption=CheckmkFileEncryption.none,
    ),
    # Log files
    "cmc.log": CheckmkFileInfo(
        components=[
            OPT_COMP_NOTIFICATIONS,
            OPT_COMP_CMC,
        ],
        sensitivity=CheckmkFileSensitivity.sensitive,
        description="In this file messages from starting and stopping the CMC can be found, as well as general warnings and error messages related to the core and the check helpers.",
        encryption=CheckmkFileEncryption.none,
    ),
    "web.log": CheckmkFileInfo(
        components=[
            OPT_COMP_NOTIFICATIONS,
            OPT_COMP_LICENSING,
        ],
        sensitivity=CheckmkFileSensitivity.sensitive,
        description="The log file of the checkmk weg gui. Here you can find all kind of automations call, ldap sync and some failing GUI extensions.",
        encryption=CheckmkFileEncryption.none,
    ),
    "liveproxyd.log": CheckmkFileInfo(
        components=[
            OPT_COMP_CMC,
        ],
        sensitivity=CheckmkFileSensitivity.sensitive,
        description="Log file for the Livestatus proxies.",
        encryption=CheckmkFileEncryption.none,
    ),
    "liveproxyd.state": CheckmkFileInfo(
        components=[
            OPT_COMP_CMC,
        ],
        sensitivity=CheckmkFileSensitivity.sensitive,
        description="The current state of the Livestatus proxies in a readable form. This file is updated every 5 seconds.",
        encryption=CheckmkFileEncryption.none,
    ),
    "mknotifyd.log": CheckmkFileInfo(
        components=[
            OPT_COMP_NOTIFICATIONS,
        ],
        sensitivity=CheckmkFileSensitivity.sensitive,
        description="The notification spooler’s log file.",
        encryption=CheckmkFileEncryption.none,
    ),
    "mknotifyd.state": CheckmkFileInfo(
        components=[
            OPT_COMP_NOTIFICATIONS,
        ],
        sensitivity=CheckmkFileSensitivity.sensitive,
        description="The current status of the notification spooler. This is primarily relevant for notifications in distributed environments.",
        encryption=CheckmkFileEncryption.none,
    ),
    "notify.log": CheckmkFileInfo(
        components=[
            OPT_COMP_NOTIFICATIONS,
        ],
        sensitivity=CheckmkFileSensitivity.sensitive,
        description="The notification module’s log file. This will show you the rule based processing of the notifications.",
        encryption=CheckmkFileEncryption.none,
    ),
    "apache/access_log": CheckmkFileInfo(
        components=[],
        sensitivity=CheckmkFileSensitivity.high_sensitive,
        description="This log file contains all requests that are sent to the site's apache server.",
        encryption=CheckmkFileEncryption.none,
    ),
    "apache/error_log": CheckmkFileInfo(
        components=[
            OPT_COMP_LICENSING,
        ],
        sensitivity=CheckmkFileSensitivity.sensitive,
        description="this log file contains all errors that occur when requests are sent to the site's apache server.",
        encryption=CheckmkFileEncryption.none,
    ),
    "dcd.log": CheckmkFileInfo(
        components=[],
        sensitivity=CheckmkFileSensitivity.sensitive,
        description="The log file for the Dynamic Configuration Daemon (DCD).",
        encryption=CheckmkFileEncryption.none,
    ),
    "alerts.log": CheckmkFileInfo(
        components=[],
        sensitivity=CheckmkFileSensitivity.sensitive,
        description="Log file with all events relevant to the alert handler (logged by the alert helper).",
        encryption=CheckmkFileEncryption.none,
    ),
    "diskspace.log": CheckmkFileInfo(
        components=[],
        sensitivity=CheckmkFileSensitivity.insensitive,
        description="The log file of the automatic disk space cleanup.",
        encryption=CheckmkFileEncryption.none,
    ),
    "mkeventd.log": CheckmkFileInfo(
        components=[],
        sensitivity=CheckmkFileSensitivity.sensitive,
        description="The event console log file. This will show you the processing of the incoming messages, matching of the rule packs and the processing of the matched mibs.",
        encryption=CheckmkFileEncryption.none,
    ),
    "rrdcached.log": CheckmkFileInfo(
        components=[],
        sensitivity=CheckmkFileSensitivity.sensitive,
        description="The log file of the rrd cache daemon.",
        encryption=CheckmkFileEncryption.none,
    ),
    "redis-server.log": CheckmkFileInfo(
        components=[],
        sensitivity=CheckmkFileSensitivity.sensitive,
        description="The log file of the redis-server of the Checkmk site.",
        encryption=CheckmkFileEncryption.none,
    ),
    "agent-receiver/access.log": CheckmkFileInfo(
        components=[],
        sensitivity=CheckmkFileSensitivity.sensitive,
        description="",
        encryption=CheckmkFileEncryption.none,
    ),
    "agent-receiver/agent-receiver.log": CheckmkFileInfo(
        components=[],
        sensitivity=CheckmkFileSensitivity.sensitive,
        description="",
        encryption=CheckmkFileEncryption.none,
    ),
    "agent-receiver/error.log": CheckmkFileInfo(
        components=[],
        sensitivity=CheckmkFileSensitivity.sensitive,
        description="",
        encryption=CheckmkFileEncryption.none,
    ),
    "agent-registration.log": CheckmkFileInfo(
        components=[],
        sensitivity=CheckmkFileSensitivity.sensitive,
        description="",
        encryption=CheckmkFileEncryption.none,
    ),
    "licensing.log": CheckmkFileInfo(
        components=[
            OPT_COMP_LICENSING,
        ],
        sensitivity=CheckmkFileSensitivity.sensitive,
        description="",
        encryption=CheckmkFileEncryption.none,
    ),
    "automation-helper/access.log": CheckmkFileInfo(
        components=[],
        sensitivity=CheckmkFileSensitivity.sensitive,
        description="This log file contains all requests that are sent to the automation helper server.",
        encryption=CheckmkFileEncryption.none,
    ),
    "automation-helper/automation-helper.log": CheckmkFileInfo(
        components=[],
        sensitivity=CheckmkFileSensitivity.sensitive,
        description="This log file contains all activity inside the automation helper application.",
        encryption=CheckmkFileEncryption.none,
    ),
    "automation-helper/error.log": CheckmkFileInfo(
        components=[],
        sensitivity=CheckmkFileSensitivity.sensitive,
        description="This log file contains all errors that occur when requests are sent to the automation helper server.",
        encryption=CheckmkFileEncryption.none,
    ),
}
