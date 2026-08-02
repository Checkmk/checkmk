#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import io
import logging
import sys
import tarfile
import textwrap
import traceback
import uuid
from collections.abc import Callable, Iterable, Mapping, MutableMapping, Sequence
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import fields
from datetime import datetime
from functools import cache
from pathlib import Path, PurePosixPath
from typing import Any, Final

import cmk.livestatus_client as livestatus
import cmk.utils.paths
from cmk.automations.results import CreateDiagnosticsDumpResult, CreateDiagnosticsDumpV2Result
from cmk.automations.types import AutomationID
from cmk.base.automations.automations import Automation, load_config
from cmk.base.config import LoadingResult
from cmk.base.modes.modes import Mode, Option
from cmk.ccc import tty
from cmk.ccc.exceptions import MKGeneralException
from cmk.ccc.hostaddress import HostName
from cmk.ccc.i18n import _
from cmk.ccc.site import get_omd_config, omd_site
from cmk.diagnostics.engine import (
    DumpSelection,
    load_diagnostics_plugins,
    resolve_selection,
)
from cmk.diagnostics.internal import (
    CollectContext,
    CollectError,
    CollectInfo,
    CollectWarning,
    DiagnosticsPlugin,
    DumpItem,
    GeneratedContent,
    Help,
    Sensitivity,
    Topic,
    VerbatimCopy,
)
from cmk.utils import log
from cmk.utils.local_secrets import SiteInternalSecret
from cmk.utils.log import console, section

# TODO(3.1): delete together with the legacy wire sections below.
DiagnosticsCLParameters = Sequence[str]
DiagnosticsModesParameters = dict[str, Any]  # type: ignore[explicit-any]
DiagnosticsOptionalParameters = dict[str, Any]  # type: ignore[explicit-any]

SUFFIX = ".tar.gz"

_CLI_THRESHOLDS: Final[Mapping[str, Sensitivity | None]] = {
    "off": None,
    "low": Sensitivity.LOW,
    "medium": Sensitivity.MEDIUM,
    "high": Sensitivity.HIGH,
}


def _parse_cli_threshold(raw: str) -> Sensitivity | None:
    try:
        return _CLI_THRESHOLDS[raw]
    except KeyError:
        raise MKGeneralException(
            "Invalid sensitivity threshold {!r} (allowed: {})".format(
                raw, ", ".join(_CLI_THRESHOLDS)
            )
        ) from None


def _resolve_cli_selection(
    catalogue: Mapping[str, DiagnosticsPlugin], options: DiagnosticsModesParameters
) -> DumpSelection:
    default_threshold = (
        _parse_cli_threshold(options["all-topics"]) if "all-topics" in options else None
    )
    thresholds: dict[Topic, Sensitivity | None] = dict.fromkeys(
        (plugin.topic for plugin in catalogue.values()), default_threshold
    )

    selected = set(resolve_selection(catalogue.values(), thresholds))
    for name in options.get("plugins", "").split(",") if "plugins" in options else []:
        if name not in catalogue:
            raise MKGeneralException("Unknown plugin %r (see --list for available plugins)" % name)
        selected.add(name)

    return DumpSelection(
        plugins=sorted(selected),
        checkmk_server_host=options.get("checkmk-server-host", ""),
    )


def _print_available_plugins(catalogue: Mapping[str, DiagnosticsPlugin]) -> None:
    by_topic: dict[Topic, list[DiagnosticsPlugin]] = {}
    for plugin in catalogue.values():
        by_topic.setdefault(plugin.topic, []).append(plugin)
    for topic in sorted(by_topic, key=lambda t: t.localize(str)):
        plugins = by_topic[topic]
        sys.stdout.write(f"{topic.localize(_)}\n")
        for plugin in sorted(plugins, key=lambda p: p.name):
            flags = [plugin.sensitivity.name.lower()]
            if plugin.always:
                flags.append("always")
            sys.stdout.write(
                f"  {plugin.name} ({', '.join(flags)}): {plugin.description.localize(_)}\n"
            )


def _mode_create_diagnostics_dump(_app: object, options: DiagnosticsModesParameters) -> None:
    # NOTE: All the stuff is logged on this level only, which is below the default WARNING level.
    loading_result = load_config()
    catalogue = _load_plugin_catalogue(logger=ConsoleLogger())

    if "list" in options:
        _print_available_plugins(catalogue)
        return

    dump = create_diagnostics_dump_v2(
        omd_root=cmk.utils.paths.omd_root,
        diagnostics_dir=cmk.utils.paths.diagnostics_dir,
        selection=_resolve_cli_selection(catalogue, options),
        loading_result=loading_result,
    )
    logger = ConsoleLogger()
    logger.section_step("Creating diagnostics dump", verbose=False)
    if dump.tarfile_created:
        logger.filepath(
            dump.tarfile_path.relative_to(cmk.utils.paths.omd_root),
            verbose=False,
        )
    else:
        logger.message("No dump")


mode_create_diagnostics_dump = Mode(
    long_option="create-diagnostics-dump",
    handler_function=_mode_create_diagnostics_dump,
    short_help="Create diagnostics dump",
    long_help=[
        (
            "Create a dump containing information for diagnostic analysis "
            "in the folder var/check_mk/diagnostics. The dump content is "
            "provided by discoverable plugins grouped into topics; use --list "
            "to see what is available on this site. Without any option only "
            "the always collected plugins are packed."
        )
    ],
    sub_options=[
        Option(
            long_option="list",
            short_help="List the available topics and plugins and exit",
        ),
        Option(
            long_option="all-topics",
            short_help=(
                "Select all plugins of all topics up to the given sensitivity threshold "
                "(off, low, medium or high)"
            ),
            argument=True,
            argument_descr="THRESHOLD",
        ),
        Option(
            long_option="plugins",
            short_help="Additionally select the given plugins, regardless of topic thresholds",
            argument=True,
            argument_descr="NAME,NAME...",
        ),
        Option(
            long_option="checkmk-server-host",
            short_help=(
                "The name of the host monitoring the Checkmk server; needed by some plugins"
            ),
            argument=True,
            argument_descr="HOST",
        ),
    ],
)


def handler(
    _app: object,
    args: DiagnosticsCLParameters,
    plugins: object,
    loading_result: LoadingResult | None,
) -> CreateDiagnosticsDumpResult:
    buf = io.StringIO()
    with redirect_stdout(buf), redirect_stderr(buf):
        log.setup_console_logging()
        dump = create_diagnostics_dump(
            omd_root=cmk.utils.paths.omd_root,
            diagnostics_dir=cmk.utils.paths.diagnostics_dir,
            parameters=deserialize_cl_parameters(args),
            loading_result=loading_result,
        )
        return CreateDiagnosticsDumpResult(
            output=buf.getvalue(),
            tarfile_path=str(dump.tarfile_path),
            tarfile_created=dump.tarfile_created,
        )


automation_create_diagnostics_dump = Automation(
    name=AutomationID("create-diagnostics-dump"),
    handler=handler,
    result=CreateDiagnosticsDumpResult,
)


def handler_v2(
    _app: object,
    args: Sequence[str],
    plugins: object,
    loading_result: LoadingResult | None,
) -> CreateDiagnosticsDumpV2Result:
    buf = io.StringIO()
    with redirect_stdout(buf), redirect_stderr(buf):
        log.setup_console_logging()
        dump = create_diagnostics_dump_v2(
            omd_root=cmk.utils.paths.omd_root,
            diagnostics_dir=cmk.utils.paths.diagnostics_dir,
            selection=(DumpSelection.deserialize(args[0]) if args else DumpSelection(plugins=())),
            loading_result=loading_result,
        )
        return CreateDiagnosticsDumpV2Result(
            output=buf.getvalue(),
            tarfile_path=str(dump.tarfile_path),
            tarfile_created=dump.tarfile_created,
        )


automation_create_diagnostics_dump_v2 = Automation(
    name=AutomationID("create-diagnostics-dump-v2"),
    handler=handler_v2,
    result=CreateDiagnosticsDumpV2Result,
)


def create_diagnostics_dump(
    *,
    omd_root: Path,
    diagnostics_dir: Path,
    parameters: DiagnosticsOptionalParameters,
    loading_result: LoadingResult | None,
) -> DiagnosticsDump:
    """Create a dump from legacy parameters (old automation wire and current CLI)"""
    selected_names, checkmk_server_host = _legacy_selection(parameters or {})
    return _create_dump(
        omd_root=omd_root,
        diagnostics_dir=diagnostics_dir,
        selected_names=selected_names,
        checkmk_server_host=checkmk_server_host,
        all_parameters=parameters or {},
        legacy_file_parameters=parameters or {},
        loading_result=loading_result,
    )


def create_diagnostics_dump_v2(
    *,
    omd_root: Path,
    diagnostics_dir: Path,
    selection: DumpSelection,
    loading_result: LoadingResult | None,
) -> DiagnosticsDump:
    return _create_dump(
        omd_root=omd_root,
        diagnostics_dir=diagnostics_dir,
        selected_names=set(selection.plugins),
        checkmk_server_host=selection.checkmk_server_host,
        all_parameters={
            "plugins": sorted(selection.plugins),
            "checkmk_server_host": selection.checkmk_server_host,
        },
        legacy_file_parameters=None,
        loading_result=loading_result,
    )


def _create_dump(
    *,
    omd_root: Path,
    diagnostics_dir: Path,
    selected_names: set[str],
    checkmk_server_host: str,
    all_parameters: Mapping[str, object],
    legacy_file_parameters: DiagnosticsOptionalParameters | None,
    loading_result: LoadingResult | None,
) -> DiagnosticsDump:
    log.logger.setLevel(logging.INFO)
    loaded_config = (load_config() if loading_result is None else loading_result).loaded_config
    omd_config = get_omd_config(omd_root)
    logger = ConsoleLogger()

    catalogue = _load_plugin_catalogue(logger=logger)
    for unknown in sorted(selected_names - set(catalogue)):
        message = f"Plugin '{unknown}' is not available on this site"
        logger.info(message)

    extra_plugins = (
        _legacy_file_plugins(legacy_file_parameters, catalogue=catalogue)
        if legacy_file_parameters is not None
        else ()
    )

    context = CollectContext(
        omd_root=omd_root,
        omd_config=omd_config,
        site_id=omd_site(),
        all_parameters=all_parameters,
        base_config={f.name: getattr(loaded_config, f.name) for f in fields(loaded_config)},
        resolve_checkmk_server_host=_make_host_resolver(checkmk_server_host),
        site_internal_auth_header=lambda: (
            "InternalToken %s" % (SiteInternalSecret().secret.b64_str)
        ),
        log=logger,
    )
    return DiagnosticsDump(
        plugins=[
            *(p for p in catalogue.values() if p.always or p.name in selected_names),
            *extra_plugins,
        ],
        context=context,
        logger=logger,
        diagnostics_dir=diagnostics_dir,
        omd_root=omd_root,
    )


def _load_plugin_catalogue(*, logger: ConsoleLogger) -> Mapping[str, DiagnosticsPlugin]:
    """All available plugins by name, as discovered on this site"""
    discovered = load_diagnostics_plugins(raise_errors=False)
    for error in discovered.errors:
        logger.error(str(error))
    return {plugin.name: plugin for plugin in discovered.plugins.values()}


def _make_host_resolver(checkmk_server_host: str) -> Callable[[], str]:
    return lambda: str(verify_checkmk_server_host(checkmk_server_host or None))


#   .--format helper-------------------------------------------------------.
#   |   __                            _     _          _                   |
#   |  / _| ___  _ __ _ __ ___   __ _| |_  | |__   ___| |_ __   ___ _ __   |
#   | | |_ / _ \| '__| '_ ` _ \ / _` | __| | '_ \ / _ \ | '_ \ / _ \ '__|  |
#   | |  _| (_) | |  | | | | | | (_| | |_  | | | |  __/ | |_) |  __/ |     |
#   | |_|  \___/|_|  |_| |_| |_|\__,_|\__| |_| |_|\___|_| .__/ \___|_|     |
#   |                                                   |_|                |
#   '----------------------------------------------------------------------'


class ConsoleLogger:
    _GAP: Final = 4 * " "

    def __init__(self) -> None:
        self._log = list[str]()

    def _info(self, message: str) -> None:
        console.info(message)
        self._log.append(message)

    def _verbose(self, message: str) -> None:
        console.verbose(message)
        self._log.append(message)

    def content(self) -> str:
        return "\n".join(self._log)

    def section_step(self, message: str, *, add_info: str = "", verbose: bool = True) -> None:
        section.section_step(message, add_info=add_info, verbose=verbose)
        self._log.append("+ " + message.upper())

    def message(self, message: str) -> None:
        self._info(f"{self._GAP}{message}")

    def filepath(self, filepath: Path, *, verbose: bool = True) -> None:
        (self._verbose if verbose else self._info)(f"{self._GAP}{filepath}")

    def title(self, title: str) -> None:
        self._info(f"{self._GAP}{tty.green}{title}{tty.normal}:")

    def description(self, description: str) -> None:
        self._info(
            textwrap.fill(
                description,
                width=52,
                initial_indent=2 * self._GAP,
                subsequent_indent=2 * self._GAP,
            )
        )

    def info(self, info: str) -> None:
        self._info(f"{2 * self._GAP}{tty.blue}{tty.bold}INFO{tty.normal} - {info}")

    def warning(self, warning: str) -> None:
        self._info(f"{2 * self._GAP}{tty.warn} - {warning}")

    def error(self, error: str) -> None:
        self._info(f"{2 * self._GAP}{tty.error} - {error}")


# .
#   .--dump----------------------------------------------------------------.
#   |                         _                                            |
#   |                      __| |_   _ _ __ ___  _ __                       |
#   |                     / _` | | | | '_ ` _ \| '_ \                      |
#   |                    | (_| | |_| | | | | | | |_) |                     |
#   |                     \__,_|\__,_|_| |_| |_| .__/                      |
#   |                                          |_|                         |
#   '----------------------------------------------------------------------'


# TODO(3.1): delete — the whole section below down to _legacy_file_plugins
# serves the old automation wire for older central sites (and the legacy
# parameters of the v1 automation). The topic declarations mirror the ones of
# the diagnostics plugin family; they only tag the synthetic legacy
# plugins.

# The option names of the old wire.
OPT_APACHE_CONFIG = "apache-config"
OPT_BI_RUNTIME_DATA = "bi-runtime-data"
OPT_CHECKMK_CONFIG_FILES = "checkmk-config-files"
OPT_CHECKMK_CORE_FILES = "checkmk-core-files"
OPT_CHECKMK_CRASH_REPORTS = "checkmk-crashes"
OPT_CHECKMK_LICENSING_FILES = "checkmk-licensing-files"
OPT_CHECKMK_LOG_FILES = "checkmk-log-files"
OPT_CHECKMK_OVERVIEW = "checkmk-overview"
OPT_LOCAL_FILES = "local-files"
OPT_OMD_CONFIG = "omd-config"
OPT_PERFORMANCE_GRAPHS = "performance-graphs"
OPT_COMP_METRIC_BACKEND = "metric-backend"

_OPTS_WITH_HOST = [
    OPT_PERFORMANCE_GRAPHS,
    OPT_CHECKMK_OVERVIEW,
]

_BOOLEAN_CONFIG_OPTS = [
    OPT_APACHE_CONFIG,
    OPT_BI_RUNTIME_DATA,
    OPT_CHECKMK_CRASH_REPORTS,
    OPT_COMP_METRIC_BACKEND,
    OPT_LOCAL_FILES,
    OPT_OMD_CONFIG,
]

_FILES_OPTS = [
    "gui-profiles",
    OPT_CHECKMK_CONFIG_FILES,
    OPT_CHECKMK_CORE_FILES,
    OPT_CHECKMK_LICENSING_FILES,
    OPT_CHECKMK_LOG_FILES,
]


# Used for the Automation "create-diagnostics-dump"
def deserialize_cl_parameters(
    cl_parameters: DiagnosticsCLParameters,
) -> DiagnosticsOptionalParameters:
    deserialized_parameters = DiagnosticsOptionalParameters()
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


_TOPIC_CONFIGURATION = Topic("Configuration files")
_TOPIC_LOGS = Topic("Log files")
_TOPIC_MONITORING_CORE = Topic("Monitoring core & daemons")
_TOPIC_LICENSING = Topic("Licensing")


# Legacy boolean options and the plugin name they select (old wire / current CLI)
_LEGACY_BOOLEAN_OPT_TO_PLUGIN: Final = {
    OPT_LOCAL_FILES: "mkp_inventory",
    OPT_OMD_CONFIG: "omd_config",
    OPT_APACHE_CONFIG: "apache_config",
    OPT_CHECKMK_CRASH_REPORTS: "latest_crash_reports",
    OPT_BI_RUNTIME_DATA: "bi_runtime_data",
    OPT_COMP_METRIC_BACKEND: "metric_backend_state",
}

# Legacy options carrying the Checkmk server host and the plugin name they select
_LEGACY_HOST_OPT_TO_PLUGIN: Final = {
    OPT_CHECKMK_OVERVIEW: "checkmk_overview",
    OPT_PERFORMANCE_GRAPHS: "performance_graphs",
}

# Plugins the old engine collected unconditionally which are selectable now
_LEGACY_IMPLICITLY_SELECTED: Final = (
    "core_performance_metrics",
    "environment_variables",
    "network_state",
    "processes_and_logins",
)


def _legacy_selection(parameters: DiagnosticsOptionalParameters) -> tuple[set[str], str]:
    """Map legacy parameters onto plugin names + the Checkmk server host"""
    selected = set(_LEGACY_IMPLICITLY_SELECTED)
    for opt, name in _LEGACY_BOOLEAN_OPT_TO_PLUGIN.items():
        if parameters.get(opt):
            selected.add(name)

    # The old wire had no global host field; these options carried the host as their value
    checkmk_server_host = ""
    for opt, name in _LEGACY_HOST_OPT_TO_PLUGIN.items():
        if opt in parameters:
            selected.add(name)
            checkmk_server_host = parameters.get(opt) or checkmk_server_host

    return selected, checkmk_server_host


def _filter_by_arcname(
    handlers: Sequence[Callable[[CollectContext], Iterable[DumpItem]]],
    base: PurePosixPath,
    requested: Sequence[str],
) -> Callable[[CollectContext], Iterable[DumpItem]]:
    """Serve an explicit file list of the old wire from the native file plugins"""

    def handler(context: CollectContext) -> Iterable[DumpItem]:
        remaining = set(requested)
        for native_handler in handlers:
            for item in native_handler(context):
                if not item.path.is_relative_to(base):
                    continue
                rel = str(item.path.relative_to(base))
                if rel in remaining:
                    remaining.discard(rel)
                    yield item
        if remaining:
            raise CollectError("No such files: %s" % ", ".join(sorted(remaining)))

    return handler


def _chain_handlers(
    *handlers: Callable[[CollectContext], Iterable[DumpItem]],
) -> Callable[[CollectContext], Iterable[DumpItem]]:
    def handler(context: CollectContext) -> Iterable[DumpItem]:
        for single_handler in handlers:
            yield from single_handler(context)

    return handler


_OPT_GUI_PROFILES = "gui-profiles"
_TOPIC_LEGACY_GUI_PROFILES = Topic("Performance & sizing")


def _filter_gui_profiles(
    native_handler: Callable[[CollectContext], Iterable[DumpItem]],
    requested_ids: set[str],
) -> Callable[[CollectContext], Iterable[DumpItem]]:
    """Serve the old wire's explicit profile id list from the native plugin"""

    def handler(context: CollectContext) -> Iterable[DumpItem]:
        packed = False
        for item in native_handler(context):
            if item.path.name.split(".", 1)[0] in requested_ids:
                packed = True
                yield item
        if not packed:
            raise CollectInfo("No profiles found")

    return handler


def _legacy_file_plugins(
    parameters: DiagnosticsOptionalParameters,
    *,
    catalogue: Mapping[str, DiagnosticsPlugin],
) -> Sequence[DiagnosticsPlugin]:
    """Plugins for the explicit file lists of the old wire (transitional)"""
    plugins = []
    if rel_checkmk_config_files := parameters.get(OPT_CHECKMK_CONFIG_FILES):
        plugins.append(
            DiagnosticsPlugin(
                name="config_files",
                description=Help("Checkmk configuration files"),
                sensitivity=Sensitivity.HIGH,
                topic=_TOPIC_CONFIGURATION,
                handler=_filter_by_arcname(
                    [
                        catalogue[name].handler
                        for name in (
                            "config_files_low",
                            "config_files_medium",
                            "config_files_high",
                        )
                    ],
                    PurePosixPath("etc/check_mk"),
                    rel_checkmk_config_files,
                ),
            )
        )

    if rel_checkmk_log_files := parameters.get(OPT_CHECKMK_LOG_FILES):
        plugins.append(
            DiagnosticsPlugin(
                name="log_files",
                description=Help("Checkmk log files"),
                sensitivity=Sensitivity.HIGH,
                topic=_TOPIC_LOGS,
                handler=_filter_by_arcname(
                    [
                        catalogue[name].handler
                        for name in ("log_files_low", "log_files_medium", "log_files_high")
                    ],
                    PurePosixPath("var/log"),
                    rel_checkmk_log_files,
                ),
            )
        )

    # The CEE file plugins are gated by presence: on editions without them
    # (community) the options below remain silently unavailable, matching the
    # old edition gate.
    if (rel_checkmk_core_files := parameters.get(OPT_CHECKMK_CORE_FILES)) and {
        "cmc_history",
        "cmc_core_files",
        "cmc_dump",
    } <= set(catalogue):
        plugins.append(
            DiagnosticsPlugin(
                name="core_files",
                description=Help("Checkmk core files and cmcdump output"),
                sensitivity=Sensitivity.HIGH,
                topic=_TOPIC_MONITORING_CORE,
                handler=_chain_handlers(
                    # The old engine always ran cmcdump when core files were selected.
                    catalogue["cmc_dump"].handler,
                    _filter_by_arcname(
                        [catalogue[name].handler for name in ("cmc_history", "cmc_core_files")],
                        PurePosixPath("var/check_mk"),
                        rel_checkmk_core_files,
                    ),
                ),
            )
        )

    if (
        rel_checkmk_licensing_files := parameters.get(OPT_CHECKMK_LICENSING_FILES)
    ) and "licensing_files" in catalogue:
        plugins.append(
            DiagnosticsPlugin(
                name="licensing_files",
                description=Help("Checkmk licensing files"),
                sensitivity=Sensitivity.HIGH,
                topic=_TOPIC_LICENSING,
                handler=_filter_by_arcname(
                    [catalogue["licensing_files"].handler],
                    PurePosixPath("var/check_mk"),
                    rel_checkmk_licensing_files,
                ),
            )
        )

    if gui_profile_ids := parameters.get(_OPT_GUI_PROFILES):
        plugins.append(
            DiagnosticsPlugin(
                name="gui_profiles",
                description=Help("Stored GUI performance profiles and flamegraphs"),
                sensitivity=Sensitivity.MEDIUM,
                topic=_TOPIC_LEGACY_GUI_PROFILES,
                handler=_filter_gui_profiles(
                    catalogue["gui_profiles"].handler, set(gui_profile_ids)
                ),
            )
        )

    return plugins


def _normalized_arcname(arcname: PurePosixPath) -> PurePosixPath | None:
    if arcname.is_absolute() or ".." in arcname.parts or not arcname.parts:
        return None
    return arcname


# Not really a class...
class DiagnosticsDump:
    """Caring about the persistance of diagnostics dumps in the local site"""

    _keep_num_dumps = 10

    def __init__(
        self,
        *,
        plugins: Sequence[DiagnosticsPlugin],
        context: CollectContext,
        logger: ConsoleLogger,
        diagnostics_dir: Path,
        omd_root: Path,
    ) -> None:
        self._logger = logger
        self.dump_folder = diagnostics_dir
        self.tarfile_path = (diagnostics_dir / f"sddump_{uuid.uuid4()}").with_suffix(SUFFIX)
        self.tarfile_created = False
        self._create_dump_folder()
        self._create_tarfile(plugins, context)
        self._cleanup_dump_folder(omd_root)

    def _create_dump_folder(self) -> None:
        self._logger.section_step("Create dump folder")
        self.dump_folder.mkdir(parents=True, exist_ok=True)

    def _create_tarfile(
        self, plugins: Sequence[DiagnosticsPlugin], context: CollectContext
    ) -> None:
        self._logger.section_step("Collect diagnostics information", verbose=False)
        collected: dict[PurePosixPath, str] = {}
        with tarfile.open(name=self.tarfile_path, mode="w:gz") as tar:
            for plugin in plugins:
                self._logger.title(plugin.name)
                self._logger.description(plugin.description.localize(_))
                self._collect_plugin(tar, plugin, context, collected)

            content = self._logger.content().encode()
            info = tarfile.TarInfo(f"console_{datetime.now().timestamp()}.log")
            info.size = len(content)
            info.mtime = int(datetime.now().timestamp())
            tar.addfile(info, io.BytesIO(content))
            # The console log alone does not count as a created dump.

    def _collect_plugin(
        self,
        tar: tarfile.TarFile,
        plugin: DiagnosticsPlugin,
        context: CollectContext,
        collected: MutableMapping[PurePosixPath, str],
    ) -> None:
        try:
            for item in plugin.handler(context):
                normalized = _normalized_arcname(item.path)
                if normalized is None:
                    message = f"{plugin.name}: invalid file path '{item.path}'"
                    self._logger.warning(message)
                    continue
                if (owner := collected.get(normalized)) is not None:
                    message = f"{plugin.name}: '{normalized}' already collected by '{owner}'"
                    self._logger.warning(message)
                    continue
                self._add_item(tar, normalized, item.content)
                collected[normalized] = plugin.name
                self.tarfile_created = True
        except CollectInfo as e:
            self._logger.info(str(e))
        except CollectWarning as e:
            self._logger.warning(str(e))
        except CollectError as e:
            # ConsoleLogger has no .exception(); keep .error() (mirrors the Info/Warning
            # handlers above and logs the plugin message at its level).
            self._logger.error(str(e))  # noqa: TRY400
        except Exception:
            # ConsoleLogger has no .exception(); format_exc() gives it the traceback.
            self._logger.error(traceback.format_exc())  # noqa: TRY400

    @staticmethod
    def _add_item(
        tar: tarfile.TarFile, arcname: PurePosixPath, item: GeneratedContent | VerbatimCopy
    ) -> None:
        match item:
            case GeneratedContent(data):
                info = tarfile.TarInfo(str(arcname))
                info.size = len(data)
                info.mtime = int(datetime.now().timestamp())
                tar.addfile(info, io.BytesIO(data))
            case VerbatimCopy(source):
                # Streams the file from disk in blocks; never loads it into memory.
                tar.add(source, arcname=str(arcname), recursive=False)

    def _cleanup_dump_folder(self, omd_root: Path) -> None:
        if not self.tarfile_created:
            # Remove empty tarfile path
            self.tarfile_path.unlink(missing_ok=True)

        dumps = sorted(
            ((dump.stat().st_mtime, dump) for dump in self.dump_folder.glob(f"*{SUFFIX}")),
            key=lambda t: t[0],
        )[: -self._keep_num_dumps]

        self._logger.section_step(
            "Cleanup dump folder", add_info=f"keep last {self._keep_num_dumps} dumps"
        )
        for _mtime, filepath in dumps:
            self._logger.filepath(filepath.relative_to(omd_root))
            filepath.unlink(missing_ok=True)


@cache
def verify_checkmk_server_host(checkmk_server_host: str | None) -> HostName:
    if checkmk_server_host:
        return HostName(checkmk_server_host)

    result = livestatus.LocalConnection().query(
        f"GET services\nColumns: host_name\nFilter: service_description ~ OMD {omd_site()} performance\n"
    )
    try:
        return HostName(result[0][0])
    except IndexError:
        raise CollectWarning("No Checkmk server found")
