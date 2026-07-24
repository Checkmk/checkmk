#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import abc
import io
import json
import logging
import os
import platform
import re
import shutil
import subprocess
import tarfile
import tempfile
import textwrap
import traceback
import urllib.parse
import uuid
from collections.abc import Callable, Iterable, Mapping, MutableMapping, Sequence
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime
from functools import cache
from pathlib import Path, PurePosixPath
from typing import Any, Final, override

import requests

import cmk.ccc.version as cmk_version
import cmk.livestatus_client as livestatus
import cmk.utils.paths
from cmk.automations.results import CreateDiagnosticsDumpResult
from cmk.automations.types import AutomationID
from cmk.base.automations.automations import Automation, load_config
from cmk.base.base_app import CheckmkBaseApp
from cmk.base.config import LoadingResult
from cmk.base.configlib.loaded_config import BaseConfig
from cmk.base.modes.modes import Mode, Option
from cmk.ccc import site, store, tty
from cmk.ccc.hostaddress import HostName
from cmk.ccc.i18n import _
from cmk.ccc.site import get_omd_config, omd_site
from cmk.checkengine.plugins import AgentBasedPlugins
from cmk.crash import make_crash_report_base_path
from cmk.diagnostics.engine import (
    CheckmkFileEncryption,
    CheckmkFileInfoByRelFilePathMap,
    CheckmkFilesMap,
    deserialize_cl_parameters,
    deserialize_modes_parameters,
    DiagnosticsCLParameters,
    DiagnosticsElementFilepaths,
    DiagnosticsModesParameters,
    DiagnosticsOptionalParameters,
    FILE_MAP_CONFIG,
    FILE_MAP_CORE,
    FILE_MAP_LICENSING,
    FILE_MAP_LOG,
    FileMapConfig,
    OPT_APACHE_CONFIG,
    OPT_BI_RUNTIME_DATA,
    OPT_CHECKMK_CONFIG_FILES,
    OPT_CHECKMK_CORE_FILES,
    OPT_CHECKMK_CRASH_REPORTS,
    OPT_CHECKMK_LICENSING_FILES,
    OPT_CHECKMK_LOG_FILES,
    OPT_CHECKMK_OVERVIEW,
    OPT_COMP_METRIC_BACKEND,
    OPT_GUI_PROFILES,
    OPT_LOCAL_FILES,
    OPT_OMD_CONFIG,
    OPT_PERFORMANCE_GRAPHS,
    redact_passwords_in_file,
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
from cmk.inventory.structured_data import (
    InventoryStore,
    SDNodeName,
    serialize_tree,
)
from cmk.licensing.usage import deserialize_dump
from cmk.profiling.backend import PROFILE_ID_RE, PROFILE_SUFFIXES
from cmk.utils import log
from cmk.utils.local_secrets import SiteInternalSecret
from cmk.utils.log import console, section

# TODO: why is there localization in this module?


SUFFIX = ".tar.gz"


def clickhouse_query(sql: str) -> list[str]:
    return [
        "clickhouse",
        "client",
        "--config",
        "etc/clickhouse-server/config.xml",
        "--user",
        "checkmk_read_write",
        "--secure",
        "--format",
        "JSONEachRow",
        "--query",
        sql,
    ]


COMPONENT_COMMANDS = [
    ("df", ".out", ["df"]),
    ("df-i", ".out", ["df", "-i"]),
    ("ip-a", ".out", ["ip", "a"]),
    ("ss-tulpen", ".out", ["ss", "-tulpen"]),
    ("w", ".out", ["w"]),
    ("top", ".out", ["top", "-b", "-n", "1", "-H", "-c", "-w", "512", "-o", "-PID", "-1"]),
    # TODO: The command below will result in user-visible errors when there is no ClickHouse (e.g.
    # for the pro edition!) or ClickHouse is there, but not enabled. This is quite bad and
    # irritating from a user POV. Basically the same holds for the other commands: Is e.g. "ss"
    # installed everywhere? Does "top" support the tons of options above? I somehow doubt that this
    # is universally the case.
    (
        "otel-licenses",
        ".json",
        clickhouse_query("""
SELECT count
FROM checkmk.licensing_active_series_count
ORDER BY bucket_start DESC
LIMIT 1;
        """),
    ),
]


METRIC_BACKEND_COMMANDS = [
    (
        "metric-backend-schema",
        ".json",
        clickhouse_query("""
SELECT *
FROM system.tables
WHERE database = 'checkmk';
        """),
    ),
    (
        "metric-backend-revision",
        ".json",
        clickhouse_query("""
SELECT *
FROM checkmk._revision;
        """),
    ),
    (
        "metric-backend-footprint",
        ".json",
        clickhouse_query("""
SELECT table,
       SUM(rows) AS rows,
       SUM(bytes_on_disk) AS bytes_on_disk,
       SUM(data_compressed_bytes) AS data_compressed_bytes,
       SUM(data_uncompressed_bytes) AS data_uncompressed_bytes,
       SUM(primary_key_size) AS primary_key_size,
       SUM(marks_bytes) AS marks_bytes,
       SUM(secondary_indices_compressed_bytes) AS secondary_indices_compressed_bytes,
       SUM(secondary_indices_uncompressed_bytes) AS secondary_indices_uncompressed_bytes,
       SUM(secondary_indices_marks_bytes) AS secondary_indices_marks_bytes,
       MAX(modification_time) AS modification_time,
       MAX(remove_time) AS remove_time,
       any(engine) AS engine,
       any(path) AS path
FROM system.parts
WHERE active
  AND database = 'checkmk'
GROUP BY table;
        """),
    ),
]

COMPONENT_DIRECTORIES = {
    OPT_APACHE_CONFIG: {
        "abs_dirs": [
            "/etc/apache2",
            "/etc/httpd",
            "/opt/omd/apache",
        ],
        "rel_dirs": [
            "etc/apache",
        ],
    },
    OPT_OMD_CONFIG: {
        "abs_dirs": [],
        "rel_dirs": [
            "etc/omd",
        ],
    },
}


def _mode_create_diagnostics_dump(app: CheckmkBaseApp, options: DiagnosticsModesParameters) -> None:
    # NOTE: All the stuff is logged on this level only, which is below the default WARNING level.
    dump = create_diagnostics_dump(
        app=app,
        omd_root=cmk.utils.paths.omd_root,
        diagnostics_dir=cmk.utils.paths.diagnostics_dir,
        parameters=deserialize_modes_parameters(options),
        loading_result=None,
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


# FIXME: This function is out-of-sync with the actual options in cmk.diagostics!
def _get_diagnostics_dump_sub_options(edition: cmk_version.Edition) -> list[Option]:
    sub_options = [
        Option(
            long_option=OPT_LOCAL_FILES,
            short_help=(
                "Pack a list of installed, unpacked, optional files below $OMD_ROOT/local. "
                "This also includes information about installed MKPs."
            ),
        ),
        Option(
            long_option=OPT_OMD_CONFIG,
            short_help="Pack content of 'etc/omd/site.conf'",
        ),
        Option(
            long_option=OPT_CHECKMK_CRASH_REPORTS,
            short_help="Pack the latest crash reports.",
        ),
        Option(
            long_option=OPT_GUI_PROFILES,
            short_help="Pack stored GUI performance profiles and flamegraphs. Comma-separated profile IDs.",
            argument=True,
            argument_descr="ID,ID...",
        ),
        Option(
            long_option=OPT_CHECKMK_OVERVIEW,
            short_help=(
                "Pack HW/SW Inventory node 'Software > Applications > Checkmk'. "
                "The parameter H is the name of the Checkmk server in Checkmk itself."
            ),
            argument=True,
            argument_descr="H",
        ),
        Option(
            long_option=OPT_CHECKMK_CONFIG_FILES,
            short_help=(
                "Pack configuration files. Use filenames relative to etc/checkmk. Wildcards are "
                "not supported."
            ),
            argument=True,
            argument_descr="FILE,FILE...",
        ),
        Option(
            long_option=OPT_CHECKMK_LOG_FILES,
            short_help=(
                "Pack log files. Use filenames relative to var/log. Wildcards are not supported."
            ),
            argument=True,
            argument_descr="FILE,FILE...",
        ),
        Option(
            long_option=OPT_CHECKMK_CORE_FILES,
            short_help=(
                "Pack core files. Use filenames relative to var/check_mk. Wildcards are not supported."
            ),
            argument=True,
            argument_descr="FILE,FILE...",
        ),
        Option(
            long_option=OPT_CHECKMK_LICENSING_FILES,
            short_help=(
                "Pack licensing files. Use filenames relative to var/check_mk. Wildcards are not supported."
            ),
            argument=True,
            argument_descr="FILE,FILE...",
        ),
    ]

    # NOTE: This condition has to be in sync with
    # cmk.gui.wato.pages.diagnostics.ModeDiagnostics._get_operational_informtion_elements().
    if edition is not cmk_version.Edition.COMMUNITY:
        sub_options.append(
            Option(
                long_option=OPT_PERFORMANCE_GRAPHS,
                short_help=(
                    "Pack performance graphs like CPU load and utilization of Checkmk Server. "
                    "The parameter H is the name of the Checkmk server in Checkmk itself."
                ),
                argument=True,
                argument_descr="H",
            )
        )

    # NOTE: This condition has to be in sync with
    # cmk.gui.wato.pages.diagnostics.ModeDiagnostics._get_component_specific_elements().
    if edition is cmk_version.Edition.ULTIMATE:
        sub_options.append(
            Option(
                long_option=OPT_COMP_METRIC_BACKEND,
                short_help=("Pack Infomation about the database schema, revision, and footprint."),
            )
        )

    return sub_options


mode_create_diagnostics_dump = Mode(
    long_option="create-diagnostics-dump",
    handler_function=_mode_create_diagnostics_dump,
    short_help="Create diagnostics dump",
    long_help=[
        "Create a dump containing information for diagnostic analysis "
        "in the folder var/check_mk/diagnostics."
    ],
    sub_options=_get_diagnostics_dump_sub_options(cmk_version.edition(cmk.utils.paths.omd_root)),
)


def handler(
    app: CheckmkBaseApp,
    args: DiagnosticsCLParameters,
    plugins: AgentBasedPlugins | None,
    loading_result: LoadingResult | None,
) -> CreateDiagnosticsDumpResult:
    buf = io.StringIO()
    with redirect_stdout(buf), redirect_stderr(buf):
        log.setup_console_logging()
        dump = create_diagnostics_dump(
            app=app,
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


def create_diagnostics_dump(
    *,
    app: CheckmkBaseApp,
    omd_root: Path,
    diagnostics_dir: Path,
    parameters: DiagnosticsOptionalParameters,
    loading_result: LoadingResult | None,
) -> DiagnosticsDump:
    """Create a dump from legacy parameters (old automation wire and current CLI)"""
    selected_names, checkmk_server_host = _legacy_selection(parameters or {})
    return _create_dump(
        app=app,
        omd_root=omd_root,
        diagnostics_dir=diagnostics_dir,
        selected_names=selected_names,
        checkmk_server_host=checkmk_server_host,
        all_parameters=parameters or {},
        extra_plugins=_legacy_file_plugins(
            parameters or {}, edition=app.edition, tmp_parent=diagnostics_dir
        ),
        loading_result=loading_result,
    )


def _create_dump(
    *,
    app: CheckmkBaseApp,
    omd_root: Path,
    diagnostics_dir: Path,
    selected_names: set[str],
    checkmk_server_host: str,
    all_parameters: Mapping[str, object],
    extra_plugins: Sequence[DiagnosticsPlugin],
    loading_result: LoadingResult | None,
) -> DiagnosticsDump:
    log.logger.setLevel(logging.INFO)
    loaded_config = (
        load_config(edition=app.edition) if loading_result is None else loading_result
    ).loaded_config
    omd_config = get_omd_config(omd_root)
    logger = ConsoleLogger()

    catalogue = _adapter_plugin_catalogue(
        edition=app.edition,
        loaded_config=loaded_config,
        core_performance_settings=app.core_performance_settings,
        omd_config=omd_config,
        tmp_parent=diagnostics_dir,
    )
    for unknown in sorted(selected_names - set(catalogue)):
        message = f"Plugin '{unknown}' is not available on this site"
        logger.info(message)

    context = CollectContext(
        omd_root=omd_root,
        omd_config=omd_config,
        all_parameters=all_parameters,
        core_performance_settings=app.core_performance_settings(loaded_config),
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


def _make_host_resolver(checkmk_server_host: str) -> Callable[[], str]:
    def resolve() -> str:
        try:
            return str(verify_checkmk_server_host(checkmk_server_host or None))
        except DiagnosticsElementWarning as e:
            raise CollectWarning(str(e)) from e

    return resolve


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


# Transitional topic declarations: they describe the target taxonomy and move
# into the diagnostics plugin family together with the plugins. The
# adapter catalogue below shrinks with every element converted to a
# discoverable plugin.

_TOPIC_GENERAL = Topic("General site information")
_TOPIC_OPERATING_SYSTEM = Topic("Operating system & hardware")
_TOPIC_PERFORMANCE = Topic("Performance & sizing")
_TOPIC_EXTENSIONS = Topic("Local files & extensions")
_TOPIC_CRASH_REPORTS = Topic("Crash reports")
_TOPIC_CONFIGURATION = Topic("Configuration files")
_TOPIC_LOGS = Topic("Log files")
_TOPIC_MONITORING_CORE = Topic("Monitoring core & daemons")
_TOPIC_LICENSING = Topic("Licensing")
_TOPIC_BUSINESS_INTELLIGENCE = Topic("Business Intelligence")


def _adapt(
    elements_factory: Callable[[CollectContext], Sequence[ABCDiagnosticsElement]],
    *,
    tmp_parent: Path,
) -> Callable[[CollectContext], Iterable[DumpItem]]:
    """Wrap legacy element classes as a plugin handler (transitional)

    Runs the elements into a temporary folder and yields the produced files
    as verbatim copies, reproducing the tar layout of the old engine. The
    temporary folder lives until the engine has consumed the generator.
    """

    def handle(context: CollectContext) -> Iterable[DumpItem]:
        with tempfile.TemporaryDirectory(dir=str(tmp_parent)) as tmp:
            tmp_dump_folder = Path(tmp)
            try:
                for element in elements_factory(context):
                    for filepath in element.add_or_get_files(
                        omd_root=context.omd_root, tmp_dump_folder=tmp_dump_folder
                    ):
                        yield DumpItem(
                            PurePosixPath(filepath.relative_to(tmp_dump_folder)),
                            VerbatimCopy(filepath),
                        )
            except DiagnosticsElementInfo as e:
                raise CollectInfo(str(e)) from e
            except DiagnosticsElementWarning as e:
                raise CollectWarning(str(e)) from e
            except DiagnosticsElementError as e:
                raise CollectError(str(e)) from e

    return handle


def _command_element(command_id: str) -> CheckmkCommandDiagnosticsElementTextDump:
    ident, suffix, command = next(c for c in COMPONENT_COMMANDS if c[0] == command_id)
    return CheckmkCommandDiagnosticsElementTextDump(ident, suffix, command)


def _adapter_plugin_catalogue(
    *,
    edition: cmk_version.Edition,
    loaded_config: BaseConfig,
    core_performance_settings: Callable[[BaseConfig], Mapping[str, int]],
    omd_config: site.OMDConfig,
    tmp_parent: Path,
) -> Mapping[str, DiagnosticsPlugin]:
    """All available plugins, keyed by name (transitional adapter catalogue)"""
    plugins = [
        DiagnosticsPlugin(
            name="parameters",
            description=Help("The parameters this diagnostics dump was created with"),
            sensitivity=Sensitivity.LOW,
            topic=_TOPIC_GENERAL,
            always=True,
            handler=_adapt(
                lambda ctx: [ParametersDiagnosticsElement(dict(ctx.all_parameters))],
                tmp_parent=tmp_parent,
            ),
        ),
        DiagnosticsPlugin(
            name="general_info",
            description=Help(
                "OS, Checkmk version and edition, Time, Core, Python version and paths, Architecture"
            ),
            sensitivity=Sensitivity.LOW,
            topic=_TOPIC_GENERAL,
            always=True,
            handler=_adapt(lambda _ctx: [GeneralDiagnosticsElement()], tmp_parent=tmp_parent),
        ),
        DiagnosticsPlugin(
            name="omd_config",
            description=Help(
                "The OMD site configuration ('omd config show') and the files below etc/omd"
            ),
            sensitivity=Sensitivity.LOW,
            topic=_TOPIC_GENERAL,
            handler=_adapt(
                lambda _ctx: [
                    OMDConfigDiagnosticsElement(omd_config),
                    CheckmkDirectoryDiagnosticsElement("etc/omd", rel=True),
                ],
                tmp_parent=tmp_parent,
            ),
        ),
        DiagnosticsPlugin(
            name="checkmk_overview",
            topic=_TOPIC_GENERAL,
            description=Help(
                "HW/SW Inventory node 'Software > Applications > Checkmk' of the Checkmk server"
            ),
            sensitivity=Sensitivity.LOW,
            handler=_adapt(
                lambda ctx: [CheckmkOverviewDiagnosticsElement(ctx.resolve_checkmk_server_host())],
                tmp_parent=tmp_parent,
            ),
        ),
        DiagnosticsPlugin(
            name="hw_info",
            topic=_TOPIC_OPERATING_SYSTEM,
            description=Help("Hardware information like memory, CPU load and CPU model"),
            sensitivity=Sensitivity.LOW,
            always=True,
            handler=_adapt(lambda _ctx: [HWDiagnosticsElement()], tmp_parent=tmp_parent),
        ),
        DiagnosticsPlugin(
            name="vendor_info",
            topic=_TOPIC_OPERATING_SYSTEM,
            description=Help("Vendor information from the DMI table of the Checkmk server"),
            sensitivity=Sensitivity.LOW,
            always=True,
            handler=_adapt(lambda _ctx: [VendorDiagnosticsElement()], tmp_parent=tmp_parent),
        ),
        DiagnosticsPlugin(
            name="appliance_info",
            topic=_TOPIC_OPERATING_SYSTEM,
            description=Help("Checkmk appliance hardware and version information"),
            sensitivity=Sensitivity.LOW,
            always=True,
            handler=_adapt(lambda _ctx: [CMAJSONDiagnosticsElement()], tmp_parent=tmp_parent),
        ),
        DiagnosticsPlugin(
            name="selinux",
            topic=_TOPIC_OPERATING_SYSTEM,
            description=Help("The SELinux status of the operating system ('sestatus')"),
            sensitivity=Sensitivity.LOW,
            always=True,
            handler=_adapt(lambda _ctx: [SELinuxJSONDiagnosticsElement()], tmp_parent=tmp_parent),
        ),
        DiagnosticsPlugin(
            name="os_packages",
            topic=_TOPIC_OPERATING_SYSTEM,
            description=Help("The operating system packages installed on the Checkmk server"),
            sensitivity=Sensitivity.LOW,
            always=True,
            handler=_adapt(
                lambda _ctx: [DpkgCSVDiagnosticsElement(), RpmCSVDiagnosticsElement()],
                tmp_parent=tmp_parent,
            ),
        ),
        DiagnosticsPlugin(
            name="python_packages",
            topic=_TOPIC_OPERATING_SYSTEM,
            description=Help("The Python packages installed in the site ('pip freeze')"),
            sensitivity=Sensitivity.LOW,
            always=True,
            handler=_adapt(lambda _ctx: [PipFreezeDiagnosticsElement()], tmp_parent=tmp_parent),
        ),
        DiagnosticsPlugin(
            name="disk_usage",
            topic=_TOPIC_OPERATING_SYSTEM,
            description=Help("File system usage of the Checkmk server ('df')"),
            sensitivity=Sensitivity.LOW,
            always=True,
            handler=_adapt(
                lambda _ctx: [_command_element("df"), _command_element("df-i")],
                tmp_parent=tmp_parent,
            ),
        ),
        DiagnosticsPlugin(
            name="file_sizes",
            topic=_TOPIC_OPERATING_SYSTEM,
            description=Help("Size, owner and permissions of the files below the site directory"),
            sensitivity=Sensitivity.LOW,
            always=True,
            handler=_adapt(lambda _ctx: [FilesSizeCSVDiagnosticsElement()], tmp_parent=tmp_parent),
        ),
        DiagnosticsPlugin(
            name="network_state",
            topic=_TOPIC_OPERATING_SYSTEM,
            description=Help(
                "Network interfaces, addresses and sockets of the Checkmk server ('ip a', 'ss')"
            ),
            sensitivity=Sensitivity.MEDIUM,
            handler=_adapt(
                lambda _ctx: [_command_element("ip-a"), _command_element("ss-tulpen")],
                tmp_parent=tmp_parent,
            ),
        ),
        DiagnosticsPlugin(
            name="processes_and_logins",
            topic=_TOPIC_OPERATING_SYSTEM,
            description=Help(
                "Running processes and logged in users of the Checkmk server ('top', 'w')"
            ),
            sensitivity=Sensitivity.MEDIUM,
            handler=_adapt(
                lambda _ctx: [_command_element("w"), _command_element("top")],
                tmp_parent=tmp_parent,
            ),
        ),
        DiagnosticsPlugin(
            name="environment_variables",
            topic=_TOPIC_OPERATING_SYSTEM,
            description=Help("The environment variables of the site user"),
            sensitivity=Sensitivity.MEDIUM,
            handler=_adapt(lambda _ctx: [EnvironmentDiagnosticsElement()], tmp_parent=tmp_parent),
        ),
        DiagnosticsPlugin(
            name="core_performance_metrics",
            topic=_TOPIC_PERFORMANCE,
            description=Help("Metrics related to sizing, e.g. number of helpers, hosts, services"),
            sensitivity=Sensitivity.LOW,
            handler=_adapt(
                lambda _ctx: [PerfDataDiagnosticsElement(loaded_config, core_performance_settings)],
                tmp_parent=tmp_parent,
            ),
        ),
        DiagnosticsPlugin(
            name="metric_backend_state",
            topic=_TOPIC_PERFORMANCE,
            description=Help("Schema, revision and footprint of the metric backend database"),
            sensitivity=Sensitivity.LOW,
            handler=_adapt(
                lambda _ctx: [
                    CheckmkCommandDiagnosticsElementTextDump(ident, suffix, command)
                    for ident, suffix, command in METRIC_BACKEND_COMMANDS
                ],
                tmp_parent=tmp_parent,
            ),
        ),
        DiagnosticsPlugin(
            name="mkp_inventory",
            topic=_TOPIC_EXTENSIONS,
            description=Help(
                "Information about installed MKPs and unpackaged files below the site's"
                " local hierarchy"
            ),
            sensitivity=Sensitivity.LOW,
            handler=_adapt(
                lambda _ctx: [
                    MKPFindTextDiagnosticsElement(),
                    MKPShowTextDiagnosticsElement(),
                    MKPListTextDiagnosticsElement(),
                ],
                tmp_parent=tmp_parent,
            ),
        ),
        DiagnosticsPlugin(
            name="latest_crash_reports",
            topic=_TOPIC_CRASH_REPORTS,
            description=Help(
                "The latest crash dumps of each type as found in var/check_mk/crashes"
            ),
            sensitivity=Sensitivity.MEDIUM,
            handler=_adapt(lambda _ctx: [CrashDumpsDiagnosticsElement()], tmp_parent=tmp_parent),
        ),
        DiagnosticsPlugin(
            name="apache_config",
            topic=_TOPIC_CONFIGURATION,
            description=Help("The Apache configuration of the operating system and the site"),
            sensitivity=Sensitivity.MEDIUM,
            handler=_adapt(
                lambda _ctx: [
                    *(
                        CheckmkDirectoryDiagnosticsElement(directory, rel=False)
                        for directory in COMPONENT_DIRECTORIES[OPT_APACHE_CONFIG]["abs_dirs"]
                    ),
                    *(
                        CheckmkDirectoryDiagnosticsElement(directory, rel=True)
                        for directory in COMPONENT_DIRECTORIES[OPT_APACHE_CONFIG]["rel_dirs"]
                    ),
                ],
                tmp_parent=tmp_parent,
            ),
        ),
        DiagnosticsPlugin(
            name="bi_runtime_data",
            topic=_TOPIC_BUSINESS_INTELLIGENCE,
            description=Help("Cached data of Business Intelligence aggregations"),
            sensitivity=Sensitivity.MEDIUM,
            handler=_adapt(
                lambda _ctx: [
                    CheckmkDirectoryDiagnosticsElement("tmp/check_mk/bi_cache", rel=True)
                ],
                tmp_parent=tmp_parent,
            ),
        ),
        DiagnosticsPlugin(
            name="otel_license_counts",
            topic=_TOPIC_LICENSING,
            description=Help("The latest licensed active time series count of the metric backend"),
            sensitivity=Sensitivity.LOW,
            always=True,
            handler=_adapt(lambda _ctx: [_command_element("otel-licenses")], tmp_parent=tmp_parent),
        ),
    ]

    if edition is not cmk_version.Edition.COMMUNITY:
        plugins.extend(
            [
                DiagnosticsPlugin(
                    name="dcd_state",
                    topic=_TOPIC_MONITORING_CORE,
                    description=Help(
                        "Returns the current state of DCD cycles and batches. "
                        "Executes the commands cmk-dcd -Bv and cmk-dcd -Cv."
                    ),
                    sensitivity=Sensitivity.LOW,
                    always=True,
                    handler=_adapt(lambda _ctx: [DCDDiagnosticsElement()], tmp_parent=tmp_parent),
                ),
                DiagnosticsPlugin(
                    name="performance_graphs",
                    topic=_TOPIC_PERFORMANCE,
                    description=Help(
                        "CPU load and utilization, number of threads, Kernel performance, OMD,"
                        " file system, Apache status, TCP connections of the time ranges"
                        " 25 hours and 35 days"
                    ),
                    sensitivity=Sensitivity.LOW,
                    handler=_adapt(
                        lambda ctx: [
                            PerformanceGraphsDiagnosticsElement(
                                ctx.resolve_checkmk_server_host(), omd_config
                            )
                        ],
                        tmp_parent=tmp_parent,
                    ),
                ),
            ]
        )

    return {plugin.name: plugin for plugin in plugins}


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


def _legacy_file_plugins(
    parameters: DiagnosticsOptionalParameters,
    *,
    edition: cmk_version.Edition,
    tmp_parent: Path,
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
                handler=_adapt(
                    lambda _ctx: [CheckmkConfigFilesDiagnosticsElement(rel_checkmk_config_files)],
                    tmp_parent=tmp_parent,
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
                handler=_adapt(
                    lambda _ctx: [CheckmkLogFilesDiagnosticsElement(rel_checkmk_log_files)],
                    tmp_parent=tmp_parent,
                ),
            )
        )

    if edition is not cmk_version.Edition.COMMUNITY:
        if rel_checkmk_core_files := parameters.get(OPT_CHECKMK_CORE_FILES):
            plugins.append(
                DiagnosticsPlugin(
                    name="core_files",
                    description=Help("Checkmk core files and cmcdump output"),
                    sensitivity=Sensitivity.HIGH,
                    topic=_TOPIC_MONITORING_CORE,
                    handler=_adapt(
                        lambda _ctx: [
                            CheckmkCoreFilesDiagnosticsElement(rel_checkmk_core_files),
                            CMCDumpDiagnosticsElement(),
                        ],
                        tmp_parent=tmp_parent,
                    ),
                )
            )

        if rel_checkmk_licensing_files := parameters.get(OPT_CHECKMK_LICENSING_FILES):
            plugins.append(
                DiagnosticsPlugin(
                    name="licensing_files",
                    description=Help("Checkmk licensing files"),
                    sensitivity=Sensitivity.HIGH,
                    topic=_TOPIC_LICENSING,
                    handler=_adapt(
                        lambda _ctx: [
                            CheckmkLicensingFilesDiagnosticsElement(rel_checkmk_licensing_files)
                        ],
                        tmp_parent=tmp_parent,
                    ),
                )
            )

    if gui_profile_ids := parameters.get("gui-profiles"):
        plugins.append(
            DiagnosticsPlugin(
                name="gui_profiles",
                description=Help("Stored GUI performance profiles and flamegraphs"),
                sensitivity=Sensitivity.MEDIUM,
                topic=_TOPIC_PERFORMANCE,
                handler=_adapt(
                    lambda _ctx: [GUIProfilesDiagnosticsElement(gui_profile_ids)],
                    tmp_parent=tmp_parent,
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


# .
#   .--collectors----------------------------------------------------------.
#   |                        _ _           _                               |
#   |               ___ ___ | | | ___  ___| |_ ___  _ __ ___               |
#   |              / __/ _ \| | |/ _ \/ __| __/ _ \| '__/ __|              |
#   |             | (_| (_) | | |  __/ (__| || (_) | |  \__ \              |
#   |              \___\___/|_|_|\___|\___|\__\___/|_|  |___/              |
#   |                                                                      |
#   '----------------------------------------------------------------------


# @cache
# def get_omd_config() -> site.OMDConfig:
#    # Useless function, useless cache.  See comment
#    # in cmk.ccc.site
#    return site.get_omd_config(cmk.utils.paths.omd_root)


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
        raise DiagnosticsElementWarning("No Checkmk server found")


# .
#   .--elements------------------------------------------------------------.
#   |                   _                           _                      |
#   |               ___| | ___ _ __ ___   ___ _ __ | |_ ___                |
#   |              / _ \ |/ _ \ '_ ` _ \ / _ \ '_ \| __/ __|               |
#   |             |  __/ |  __/ | | | | |  __/ | | | |_\__ \               |
#   |              \___|_|\___|_| |_| |_|\___|_| |_|\__|___/               |
#   |                                                                      |
#   '----------------------------------------------------------------------'


class DiagnosticsElementError(Exception):
    pass


class DiagnosticsElementWarning(Exception):
    pass


class DiagnosticsElementInfo(Exception):
    pass


class ABCDiagnosticsElement(abc.ABC):
    @property
    @abc.abstractmethod
    def title(self) -> str:
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def description(self) -> str:
        raise NotImplementedError

    @abc.abstractmethod
    def add_or_get_files(
        self, *, omd_root: Path, tmp_dump_folder: Path
    ) -> DiagnosticsElementFilepaths:
        # Please note the case if there are more than one filepath results. A Python generator
        # is executed until the first raise. Then it will be stopped and all generator states
        # are gone. Correctly calculated filepaths till then are yielded.
        # (Example: CheckmkConfigFilesDiagnosticsElement: collect errors and raise at the end)
        raise NotImplementedError


class ABCDiagnosticsElementTextDump(ABCDiagnosticsElement):
    @override
    def add_or_get_files(
        self, *, omd_root: Path, tmp_dump_folder: Path
    ) -> DiagnosticsElementFilepaths:
        if not (infos := self.contents(omd_root)):
            raise DiagnosticsElementInfo("No data")
        filepath = tmp_dump_folder / self.filename
        filepath.write_text(infos)
        yield filepath

    @property
    @abc.abstractmethod
    def filename(self) -> str:
        raise NotImplementedError

    @abc.abstractmethod
    def contents(self, omd_root: Path) -> str:
        raise NotImplementedError


#   ---text dumps-----------------------------------------------------------


class ParametersDiagnosticsElement(ABCDiagnosticsElementTextDump):
    def __init__(self, parameters: DiagnosticsOptionalParameters | None) -> None:
        self.parameters = parameters

    @override
    @property
    def title(self) -> str:
        return _("Parameters")

    @override
    @property
    def description(self) -> str:
        return _("The parameters that were provided to create the diagnostics dump.")

    @override
    @property
    def filename(self) -> str:
        return "parameters_%s" % str(datetime.now().timestamp())

    @override
    def contents(self, omd_root: Path) -> str:
        return str(self.parameters)


#   ---csv dumps-----------------------------------------------------------


class FilesSizeCSVDiagnosticsElement(ABCDiagnosticsElementTextDump):
    @override
    @property
    def title(self) -> str:
        return _("File size")

    @override
    @property
    def description(self) -> str:
        return _("List of all files in the site including their size")

    @override
    @property
    def filename(self) -> str:
        return "file_size.csv"

    @override
    def contents(self, omd_root: Path) -> str:
        csv_data = []
        csv_data.append("size;path;owner;group;mode;changed")
        tmp_file_regex = re.compile(r"^\..*\.new.*")
        for dirpath, _dirnames, filenames in os.walk(omd_root):
            for file in filenames:
                f = Path(dirpath, file)
                if f.is_symlink():
                    continue
                if re.match(tmp_file_regex, f.name):
                    continue
                csv_data.append(
                    ";".join(
                        [
                            str(f.stat().st_size),
                            str(f),
                            f.owner(),
                            f.group(),
                            str(oct(f.stat().st_mode)),
                            datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
                        ]
                    )
                )

        return "\n".join(csv_data)


class DpkgCSVDiagnosticsElement(ABCDiagnosticsElementTextDump):
    @override
    @property
    def title(self) -> str:
        return _("Dpkg packages information")

    @override
    @property
    def description(self) -> str:
        return _("Output of `dpkg -l`. See the corresponding command line help for more details.")

    @override
    @property
    def filename(self) -> str:
        return "dpkg_packages.csv"

    @override
    def contents(self, omd_root: Path) -> str:
        if not (dpkg_binary := shutil.which("dpkg")):
            return ""

        dpkg_output = subprocess.check_output([dpkg_binary, "-l"], text=True)
        return "\n".join(
            [";".join(l.split(maxsplit=4)) for l in dpkg_output.split("\n") if len(l.split()) > 4]
        )


class RpmCSVDiagnosticsElement(ABCDiagnosticsElementTextDump):
    @override
    @property
    def title(self) -> str:
        return _("Rpm packages information")

    @override
    @property
    def description(self) -> str:
        return _("Output of `rpm -qa`. See the corresponding command line help for more details.")

    @override
    @property
    def filename(self) -> str:
        return "rpm_packages.csv"

    @override
    def contents(self, omd_root: Path) -> str:
        if not (rpm_binary := shutil.which("rpm")):
            return ""

        try:
            output = subprocess.check_output(
                [
                    rpm_binary,
                    "-qa",
                    "--queryformat",
                    r"%{NAME};%{VERSION};%{RELEASE};%{ARCH}\n",
                ],
                text=True,
                stderr=subprocess.STDOUT,
            )

        except subprocess.CalledProcessError:
            return ""

        return "\n".join(sorted(output.split("\n")))


#   ---json dumps-----------------------------------------------------------


class GeneralDiagnosticsElement(ABCDiagnosticsElementTextDump):
    @override
    @property
    def title(self) -> str:
        return _("General")

    @override
    @property
    def description(self) -> str:
        return _(
            "OS, Checkmk version and edition, Time, Core, Python version and paths, Architecture"
        )

    @override
    @property
    def filename(self) -> str:
        return "general.json"

    @override
    def contents(self, omd_root: Path) -> str:
        version_infos = cmk_version.get_general_version_infos(omd_root)
        time_obj = datetime.fromtimestamp(version_infos.get("time", 0.0))
        return json.dumps(
            {
                "arch": platform.machine(),
                "time_human_readable": time_obj.isoformat(sep=" "),
                "time": version_infos["time"],
                "os": version_infos["os"],
                "version": version_infos["version"],
                "edition": version_infos["edition"],
                "core": version_infos["core"],
                "python_version": version_infos["python_version"],
                "python_paths": list(version_infos["python_paths"]),
            },
            sort_keys=True,
            indent=4,
        )


class PerfDataDiagnosticsElement(ABCDiagnosticsElementTextDump):
    def __init__(
        self,
        loaded_config: BaseConfig,
        core_performance_settings: Callable[[BaseConfig], Mapping[str, int]],
    ) -> None:
        self._loaded_config: Final = loaded_config
        self._core_performance_settings: Final = core_performance_settings

    @override
    @property
    def title(self) -> str:
        return _("Metrics")

    @override
    @property
    def description(self) -> str:
        return _("Metrics related to sizing, e.g. number of helpers, hosts, services")

    @override
    @property
    def filename(self) -> str:
        return "perfdata.json"

    @override
    def contents(self, omd_root: Path) -> str:
        result = livestatus.LocalConnection().query("GET status\nColumnHeaders: on")
        performance_data = {
            key: result[1][i]
            for i in range(len(result[0]))
            if (key := result[0][i]) not in ["license_usage_history"]
        }
        performance_data.update(self._core_performance_settings(self._loaded_config))
        return json.dumps(performance_data, sort_keys=True, indent=4)


class HWDiagnosticsElement(ABCDiagnosticsElementTextDump):
    def __init__(self, proc_path: Path = Path("/proc")) -> None:
        self._proc_path = proc_path

    @override
    @property
    def title(self) -> str:
        return _("HW information")

    @override
    @property
    def description(self) -> str:
        return _("Hardware information of the Checkmk server")

    @override
    @property
    def filename(self) -> str:
        return "hwinfo.json"

    @override
    def contents(self, omd_root: Path) -> str:
        hw_info: dict[str, dict[str, str]] = {}
        for procfile, parser in [
            ("meminfo", _meminfo_proc_parser),
            ("loadavg", _load_avg_proc_parser),
            ("cpuinfo", _cpuinfo_proc_parser),
        ]:
            if content := _try_to_read(self._proc_path / procfile):
                hw_info[procfile] = parser(content)
        return json.dumps(hw_info, sort_keys=True, indent=4)


def _meminfo_proc_parser(content: list[str]) -> dict[str, str]:
    info: dict[str, str] = {}

    for line in content:
        if line == "":
            continue

        key, value = (w.strip() for w in line.split(":", 1))
        info[key.replace(" ", "_")] = value

    return info


def _cpuinfo_proc_parser(content: list[str]) -> dict[str, str]:
    cpu_info: dict[str, Any] = {}
    physical_ids: list[str] = []
    num_processors = 0

    # Example lines from /proc/cpuinfo output:
    # >>> pprint.pprint(content)
    # ['processor\t: 0',
    #  'cpu family\t: 6',
    #  'cpu MHz\t\t: 2837.021',
    #  'core id\t\t: 0',
    #  'power management:',
    # ...
    #  '',
    #  'processor\t: 1',
    #  'cpu family\t: 6',
    #  'cpu MHz\t\t: 2100.000',
    #  'core id\t\t: 1',
    #  'power management:',
    #  '',
    # ...

    # Keys that have different values for each processor
    _KEYS_TO_IGNORE = [
        "apicid",
        "core_id",
        "cpu_MHz",
        "initial_apicid",
        "processor",
    ]

    # Remove empty keys, empty values and ignore some keys
    for line in content:
        if line == "":
            continue

        key, value = (w.strip() for w in line.split(":", 1))
        key = key.replace(" ", "_")

        if key not in _KEYS_TO_IGNORE:
            cpu_info[key] = value

        if key == "processor":
            num_processors += 1

        if key == "physical_id" and value not in physical_ids:
            physical_ids.append(value)

    cpu_info["num_logical_processors"] = str(num_processors)
    cpu_info["cpus"] = len(physical_ids)

    return cpu_info


def _load_avg_proc_parser(content: list[str]) -> dict[str, str]:
    return dict(zip(["loadavg_1", "loadavg_5", "loadavg_15"], content[0].split()))


class VendorDiagnosticsElement(ABCDiagnosticsElementTextDump):
    def __init__(self, dmi_id_path: Path = Path("/sys/class/dmi/id")) -> None:
        self._dmi_id_path = dmi_id_path

    @override
    @property
    def title(self) -> str:
        return _("Vendor Information")

    @override
    @property
    def description(self) -> str:
        return _("HW vendor information of the Checkmk server")

    @override
    @property
    def filename(self) -> str:
        return "vendorinfo.json"

    @override
    def contents(self, omd_root: Path) -> str:
        _SYS_FILES = [
            "bios_vendor",
            "bios_version",
            "sys_vendor",
            "product_name",
            "chassis_asset_tag",
        ]
        _AZURE_TAG = "7783-7084-3265-9085-8269-3286-77"
        vendor_info = {}
        for sys_file in _SYS_FILES:
            file_content = (self._dmi_id_path / sys_file).read_text().replace("\n", "")
            vendor_info[sys_file] = (
                ("Azure" if file_content == _AZURE_TAG else "Other")
                if sys_file == "chassis_asset_tag"
                else file_content
            )
        return json.dumps(vendor_info, sort_keys=True, indent=4)


class EnvironmentDiagnosticsElement(ABCDiagnosticsElementTextDump):
    @override
    @property
    def title(self) -> str:
        return _("Environment variables")

    @override
    @property
    def description(self) -> str:
        return _("Variables set in the site user's environment")

    @override
    @property
    def filename(self) -> str:
        return "environment.json"

    @override
    def contents(self, omd_root: Path) -> str:
        return json.dumps(dict(os.environ), sort_keys=True, indent=4)


class PipFreezeDiagnosticsElement(ABCDiagnosticsElementTextDump):
    @override
    @property
    def title(self) -> str:
        return _("pip freeze output")

    @override
    @property
    def description(self) -> str:
        return _("The installed Python modules and their versions")

    @override
    @property
    def filename(self) -> str:
        return "pip_freeze.json"

    @override
    def contents(self, omd_root: Path) -> str:
        return json.dumps(
            {
                l.split("==")[0]: l.split("==")[1]
                for l in subprocess.check_output(["pip3", "freeze", "--all"], text=True).split("\n")
                if "==" in l
            },
            sort_keys=True,
            indent=4,
        )


class MKPFindTextDiagnosticsElement(ABCDiagnosticsElementTextDump):
    @override
    @property
    def title(self) -> str:
        return _("Extension package files")

    @override
    @property
    def description(self) -> str:
        return _(
            "Output of `mkp find --all --json`. "
            "See the corresponding command line help for more details."
        )

    @override
    @property
    def filename(self) -> str:
        return "mkp_find_all.json"

    @override
    def contents(self, omd_root: Path) -> str:
        try:
            return subprocess.check_output(["mkp", "find", "--all", "--json"], text=True)
        except subprocess.CalledProcessError as e:
            ConsoleLogger().error(str(e.stderr))
            return "{}"


class MKPShowTextDiagnosticsElement(ABCDiagnosticsElementTextDump):
    @override
    @property
    def title(self) -> str:
        return _("Extension package files")

    @override
    @property
    def description(self) -> str:
        return _(
            "Output of `mkp show-all --json`. "
            "See the corresponding command line help for more details."
        )

    @override
    @property
    def filename(self) -> str:
        return "mkp_show_all.json"

    @override
    def contents(self, omd_root: Path) -> str:
        try:
            return subprocess.check_output(["mkp", "show-all", "--json"], text=True)
        except subprocess.CalledProcessError as e:
            ConsoleLogger().error(str(e.stderr))
            return "{}"


class MKPListTextDiagnosticsElement(ABCDiagnosticsElementTextDump):
    @override
    @property
    def title(self) -> str:
        return _("Extension package files")

    @override
    @property
    def description(self) -> str:
        return _(
            "Output of `mkp list --json`. See the corresponding command line help for more details."
        )

    @override
    @property
    def filename(self) -> str:
        return "mkp_list.json"

    @override
    def contents(self, omd_root: Path) -> str:
        try:
            return subprocess.check_output(["mkp", "list", "--json"], text=True)
        except subprocess.CalledProcessError as e:
            ConsoleLogger().error(str(e.stderr))
            return "{}"


class SELinuxJSONDiagnosticsElement(ABCDiagnosticsElementTextDump):
    @override
    @property
    def title(self) -> str:
        return _("SELinux information")

    @override
    @property
    def description(self) -> str:
        return _("Output of `sestatus`. See the corresponding command line help for more details.")

    @override
    @property
    def filename(self) -> str:
        return "selinux.json"

    @override
    def contents(self, omd_root: Path) -> str:
        return json.dumps(
            {
                line.split(":")[0]: line.split(":")[1].lstrip()
                for line in subprocess.check_output(selinux_binary, text=True).split("\n")
                if ":" in line
            }
            if (selinux_binary := shutil.which("sestatus"))
            else {},
            sort_keys=True,
            indent=4,
        )


def _try_to_read(filename: str | Path) -> list[str]:
    try:
        with open(filename) as f:
            return [l.rstrip() for l in f.readlines()]
    except (PermissionError, FileNotFoundError):
        return []


class CMAJSONDiagnosticsElement(ABCDiagnosticsElementTextDump):
    @override
    @property
    def title(self) -> str:
        return _("Checkmk Appliance information")

    @override
    @property
    def description(self) -> str:
        return _("Information about the appliance hardware and firmware version.")

    @override
    @property
    def filename(self) -> str:
        return "appliance.json"

    @override
    def contents(self, omd_root: Path) -> str:
        cma_infos: dict[str, str | dict[str, str]] = {}
        if hw_content := _try_to_read("/etc/cma/hw"):
            cma_infos["hw"] = dict([l.replace("'", "").split("=") for l in hw_content if "=" in l])
        if fw_content := _try_to_read("/ro/usr/share/cma/version"):
            cma_infos["fw"] = fw_content[0]
        return json.dumps(cma_infos, sort_keys=True, indent=4)


class OMDConfigDiagnosticsElement(ABCDiagnosticsElementTextDump):
    def __init__(self, omd_config: site.OMDConfig) -> None:
        self._omd_config = omd_config

    @override
    @property
    def title(self) -> str:
        return _("OMD Config")

    @override
    @property
    def description(self) -> str:
        return _(
            "Apache mode and TCP address and port, core, Liveproxy daemon and Livestatus TCP mode, event daemon config, graphical user interface (GUI) authorization, NSCA mode, TMP file system mode"
        )

    @override
    @property
    def filename(self) -> str:
        return "omd_config.json"

    @override
    def contents(self, omd_root: Path) -> str:
        return json.dumps(self._omd_config, sort_keys=True, indent=4)


class CheckmkOverviewDiagnosticsElement(ABCDiagnosticsElementTextDump):
    def __init__(self, checkmk_server_host: str) -> None:
        self.checkmk_server_host = checkmk_server_host

    @override
    @property
    def title(self) -> str:
        return _("Checkmk overview of Checkmk server")

    @override
    @property
    def description(self) -> str:
        return _(
            "Checkmk Agent, Number, version and edition of sites, cluster host; "
            "number of hosts, services, CMK Helper, Live Helper, "
            "Helper usage; state of daemons: Apache, Core, Crontab, "
            "DCD, Liveproxyd, MKEventd, MKNotifyd, RRDCached "
            "(Agent plug-in mk_inventory needs to be installed)"
        )

    @override
    @property
    def filename(self) -> str:
        return "checkmk_overview"

    @override
    def contents(self, omd_root: Path) -> str:
        return _get_checkmk_overview_content(InventoryStore(omd_root), self.checkmk_server_host)


# TODO: some of this should go to the inventory component
def _get_checkmk_overview_content(inventory_store: InventoryStore, checkmk_server_host: str) -> str:
    checkmk_server_host = verify_checkmk_server_host(checkmk_server_host)
    try:
        tree = inventory_store.load_inventory_tree(host_name=checkmk_server_host)
    except FileNotFoundError:
        raise DiagnosticsElementError("No HW/SW Inventory tree of '%s' found" % checkmk_server_host)

    if not (
        node := tree.get_tree(
            (
                SDNodeName("software"),
                SDNodeName("applications"),
                SDNodeName("check_mk"),
            )
        )
    ):
        raise DiagnosticsElementWarning(
            "No HW/SW Inventory node 'Software > Applications > Checkmk'"
        )
    return json.dumps(serialize_tree(node), sort_keys=True, indent=4)


#   ---collect exiting files------------------------------------------------


class ABCCheckmkFilesDiagnosticsElement(ABCDiagnosticsElement):
    def __init__(self, rel_checkmk_files: list[str]) -> None:
        self.rel_checkmk_files = rel_checkmk_files
        self.file_map_config = self._file_map_config

    def _checkmk_files_map(self, omd_root: Path) -> CheckmkFilesMap:
        return self.file_map_config.map_generator(
            omd_root / self.file_map_config.rel_base_folder,
            lambda base_folder: list(os.walk(base_folder)),
        )

    @property
    @abc.abstractmethod
    def _file_map_config(self) -> FileMapConfig:
        raise NotImplementedError

    def _copy_and_decrypt(
        self,
        *,
        checkmk_files_map: CheckmkFilesMap,
        omd_root: Path,
        rel_filepath: Path,
        tmp_dump_folder: Path,
    ) -> Path | None:
        filepath = checkmk_files_map.get(str(rel_filepath))
        if filepath is None or not filepath.exists():
            return None

        # Respect file path (2), otherwise the paths of same named files are forgotten (1).
        # We want to pack a folder hierarchy.

        subfolder = filepath.relative_to(omd_root).parent
        # Create relative path in tmp tree
        tmp_folder = tmp_dump_folder / subfolder
        tmp_folder.mkdir(parents=True, exist_ok=True)

        # Decrypt if file is encrypted, else only copy
        encryption = CheckmkFileEncryption.none

        tmp_filepath = tmp_folder / filepath.name
        file_info = CheckmkFileInfoByRelFilePathMap.get(str(rel_filepath))

        if file_info is not None:
            encryption = file_info.encryption

        if encryption == CheckmkFileEncryption.rot47:
            tmp_filepath.write_text(
                json.dumps(deserialize_dump(filepath.read_bytes()), sort_keys=True, indent=4)
            )
        # We 'encrypt' only license thingies at the moment, so there is currently no need to
        # sanitize encrypted files
        elif rel_filepath == Path("multisite.d/sites.mk"):
            store.save_to_mk_file(
                tmp_filepath,
                key="sites",
                value={
                    siteid: livestatus.sanitize_site_configuration(config)
                    for siteid, config in store.load_from_mk_file(
                        filepath,
                        key="sites",
                        default=livestatus.SiteConfigurations({}),
                        lock=False,
                    ).items()
                },
            )
        else:
            shutil.copy(filepath, tmp_filepath)

        passwords_redacted = redact_passwords_in_file(tmp_filepath, rel_filepath)

        if passwords_redacted:
            ConsoleLogger().info(f"Redacted {passwords_redacted} passwords in file {rel_filepath}")

        return tmp_filepath

    @override
    def add_or_get_files(
        self, *, omd_root: Path, tmp_dump_folder: Path
    ) -> DiagnosticsElementFilepaths:
        unknown_files = []
        checkmk_files_map = self._checkmk_files_map(omd_root)

        for rel_filepath in self.rel_checkmk_files:
            tmp_filepath = self._copy_and_decrypt(
                checkmk_files_map=checkmk_files_map,
                omd_root=omd_root,
                rel_filepath=Path(rel_filepath),
                tmp_dump_folder=tmp_dump_folder,
            )

            if tmp_filepath is None:
                unknown_files.append(str(rel_filepath))
                continue

            yield tmp_filepath

        if unknown_files:
            raise DiagnosticsElementError("No such files: %s" % ", ".join(unknown_files))


class CheckmkConfigFilesDiagnosticsElement(ABCCheckmkFilesDiagnosticsElement):
    @override
    @property
    def title(self) -> str:
        return _("Checkmk configuration files")

    @override
    @property
    def description(self) -> str:
        return _("Configuration files ('*.mk' or '*.conf') from etc/checkmk: %(files)s") % {
            "files": ", ".join(self.rel_checkmk_files)
        }

    @override
    @property
    def _file_map_config(self) -> FileMapConfig:
        return FILE_MAP_CONFIG


class CheckmkLogFilesDiagnosticsElement(ABCCheckmkFilesDiagnosticsElement):
    @override
    @property
    def title(self) -> str:
        return _("Checkmk log files")

    @override
    @property
    def description(self) -> str:
        return _("Log files ('*.log' or '*.state') from var/log: %(files)s") % {
            "files": ", ".join(self.rel_checkmk_files)
        }

    @override
    @property
    def _file_map_config(self) -> FileMapConfig:
        return FILE_MAP_LOG


#   ---directory dumps------------------------------------------------------------


class CheckmkDirectoryDiagnosticsElement(ABCDiagnosticsElement):
    def __init__(self, directory: str | Path, rel: bool = False) -> None:
        if isinstance(directory, str):
            self.directory = Path(directory)
        else:
            self.directory = directory
        self.rel = rel

    @override
    @property
    def title(self) -> str:
        return _("Files in %(directory)s") % {"directory": self.directory}

    @override
    @property
    def description(self) -> str:
        return _("Configuration files from %(directory)s") % {"directory": str(self.directory)}

    @override
    def add_or_get_files(
        self, *, omd_root: Path, tmp_dump_folder: Path
    ) -> DiagnosticsElementFilepaths:
        abs_path = (omd_root if self.rel else Path("")) / self.directory
        for path, _dirs, files in abs_path.walk():
            tmp_target_folder = tmp_dump_folder / (
                path.relative_to(omd_root) if self.rel else "os_root" / path.relative_to("/")
            )
            for file in files:
                tmp_file = tmp_target_folder / file
                tmp_target_folder.mkdir(parents=True, exist_ok=True)
                if not tmp_file.exists():
                    shutil.copy(path / file, tmp_file)
                yield tmp_file


#   ---command calls--------------------------------------------------------------


class CheckmkCommandDiagnosticsElementTextDump(ABCDiagnosticsElementTextDump):
    def __init__(self, command_id: str, suffix: str, command: list[str]) -> None:
        self._command_id = command_id
        self._suffix = suffix
        self._command = command

    @override
    @property
    def title(self) -> str:
        return _("Command %(command_id)s") % {"command_id": self._command_id}

    @override
    @property
    def description(self) -> str:
        return _("Output of %(command)s") % {"command": " ".join(self._command)}

    @override
    @property
    def filename(self) -> str:
        return f"command_{self._command_id}{self._suffix}"

    @override
    def contents(self, omd_root: Path) -> str:
        try:
            return subprocess.check_output(
                self._command,
                text=True,
                stderr=subprocess.STDOUT,
                cwd=omd_root,
            )

        except subprocess.CalledProcessError:
            raise DiagnosticsElementError(
                "Command %s returned an unexpected error." % " ".join(self._command)
            )

        except FileNotFoundError:
            raise DiagnosticsElementInfo(
                "Command %s not available on this system." % " ".join(self._command)
            )


#   ---cee dumps------------------------------------------------------------


class CheckmkCoreFilesDiagnosticsElement(ABCCheckmkFilesDiagnosticsElement):
    @override
    @property
    def title(self) -> str:
        return _("Checkmk core files")

    @override
    @property
    def description(self) -> str:
        return _("Core files (config, state and history) from var/check_mk/core: %(files)s") % {
            "files": ", ".join(self.rel_checkmk_files)
        }

    @override
    @property
    def _file_map_config(self) -> FileMapConfig:
        return FILE_MAP_CORE


class CheckmkLicensingFilesDiagnosticsElement(ABCCheckmkFilesDiagnosticsElement):
    @override
    @property
    def title(self) -> str:
        return _("Checkmk licensing files")

    @override
    @property
    def description(self) -> str:
        return _(
            "Licensing files (data, config and logs) from var/check_mk/licensing, etc/check_mk/multisite.d and var/log: %(files)s"
        ) % {"files": ", ".join(self.rel_checkmk_files)}

    @override
    @property
    def _file_map_config(self) -> FileMapConfig:
        return FILE_MAP_LICENSING


class PerformanceGraphsDiagnosticsElement(ABCDiagnosticsElement):
    def __init__(self, checkmk_server_host: str, omd_config: site.OMDConfig) -> None:
        self.checkmk_server_host = checkmk_server_host
        self.omd_config = omd_config

    @override
    @property
    def title(self) -> str:
        return _("Time series graphs of Checkmk server")

    @override
    @property
    def description(self) -> str:
        return _(
            "CPU load and utilization, number of threads, Kernel performance, OMD, file system, Apache status, TCP connections of the time ranges 25 hours and 35 days"
        )

    @override
    def add_or_get_files(
        self, *, omd_root: Path, tmp_dump_folder: Path
    ) -> DiagnosticsElementFilepaths:
        checkmk_server_host = verify_checkmk_server_host(self.checkmk_server_host)
        response = self._get_response(checkmk_server_host)

        if response.status_code != 200:
            raise DiagnosticsElementError(
                "HTTP error - %d (%s)" % (response.status_code, response.text)
            )

        if "<html>" in response.text.lower():
            raise DiagnosticsElementError("Login failed - Invalid automation user or secret")
        # Verify if it's a PDF document: The header must begin with
        # "%PDF-" (hex: "25 50 44 46 2d")
        if response.content[:5].hex() != "255044462d":
            raise DiagnosticsElementError("Verification of PDF document header failed")

        filepath = tmp_dump_folder / "performance_graphs.pdf"
        filepath.write_bytes(response.content)
        yield filepath

    def _get_response(self, checkmk_server_host: str) -> requests.Response:
        internal_secret = "InternalToken %s" % (SiteInternalSecret().secret.b64_str)
        url = "http://{}:{}/{}/check_mk/report.py?".format(
            self.omd_config["CONFIG_APACHE_TCP_ADDR"],
            self.omd_config["CONFIG_APACHE_TCP_PORT"],
            omd_site(),
        ) + urllib.parse.urlencode(
            [
                ("host", checkmk_server_host),
                ("name", "host_performance_graphs"),
            ]
        )

        return requests.post(
            url,
            headers={
                "Authorization": internal_secret,
            },
            timeout=900,
        )


class CrashDumpsDiagnosticsElement(ABCDiagnosticsElement):
    @override
    @property
    def title(self) -> str:
        return _("The latest crash dumps of each type")

    @override
    @property
    def description(self) -> str:
        return _("Returns the latest crash dumps of each type as found in var/checkmk/crashes")

    @override
    def add_or_get_files(
        self, *, omd_root: Path, tmp_dump_folder: Path
    ) -> DiagnosticsElementFilepaths:
        for category in make_crash_report_base_path(omd_root).glob("*"):
            tmpdir = tmp_dump_folder / "var/check_mk/crashes" / category.name
            tmpdir.mkdir(parents=True, exist_ok=True)

            sorted_dumps = sorted(
                (p for p in category.glob("*") if p.is_dir()),
                key=lambda path: int(path.stat().st_mtime),
            )

            if sorted_dumps:
                # Determine the latest file of that category
                dumpfile_path = sorted_dumps[-1]

                # Pack the dump into a .tar.gz, so it can easily be uploaded
                # to https://crash.checkmk.com/
                tarfile_path = (tmpdir / dumpfile_path.name).with_suffix(".tar.gz")

                with tarfile.open(name=tarfile_path, mode="w:gz") as tar:
                    for file in dumpfile_path.iterdir():
                        tar.add(file, arcname=file.relative_to(dumpfile_path))

                yield tarfile_path


class GUIProfilesDiagnosticsElement(ABCDiagnosticsElement):
    def __init__(self, profile_ids: Iterable[str]) -> None:
        self._profile_ids = list(profile_ids)

    @override
    @property
    def title(self) -> str:
        return _("Performance profiles and flamegraphs")

    @override
    @property
    def description(self) -> str:
        return _("Stored performance profiles (.profile) and metadata from var/check_mk/profiles")

    @override
    def add_or_get_files(
        self, *, omd_root: Path, tmp_dump_folder: Path
    ) -> DiagnosticsElementFilepaths:
        profiles_dir = omd_root / "var/check_mk/profiles"
        if not profiles_dir.is_dir():
            raise DiagnosticsElementInfo("No profiles found")

        tmpdir = tmp_dump_folder / "var/check_mk/profiles"
        tmpdir.mkdir(parents=True, exist_ok=True)

        found_any = False
        for profile_id in self._profile_ids:
            if not PROFILE_ID_RE.match(profile_id):
                continue
            for suffix in PROFILE_SUFFIXES:
                src_file = profiles_dir / f"{profile_id}{suffix}"
                if src_file.is_file():
                    dst = tmpdir / src_file.name
                    shutil.copy2(src_file, dst)
                    found_any = True
                    yield dst

        if not found_any:
            raise DiagnosticsElementInfo("No profiles found")


class CMCDumpDiagnosticsElement(ABCDiagnosticsElement):
    @override
    @property
    def title(self) -> str:
        return _("Config and state dumps of the CMC")

    @override
    @property
    def description(self) -> str:
        return _(
            "Configuration, status, and status history data of the CMC (Checkmk Micro Core); "
            "cmcdump output of the status and config."
        )

    @override
    def add_or_get_files(
        self, *, omd_root: Path, tmp_dump_folder: Path
    ) -> DiagnosticsElementFilepaths:
        command = [str(omd_root / "bin/cmcdump")]

        for dump_args in (None, "--config"):
            tmpdir = tmp_dump_folder / "var/check_mk/core"
            tmpdir.mkdir(parents=True, exist_ok=True)
            suffix = ""

            if dump_args is not None:
                command.append(dump_args)
                suffix = "%s" % dump_args

            try:
                output = subprocess.check_output(
                    command, stderr=subprocess.STDOUT, timeout=15, encoding="utf-8"
                )
            except subprocess.CalledProcessError as e:
                ConsoleLogger().error(str(e))
                continue

            filepath = tmpdir / f"cmcdump{suffix}"
            filepath.write_text(output)
            yield filepath


class DCDDiagnosticsElement(ABCDiagnosticsElementTextDump):
    @property
    def title(self) -> str:
        return _("DCD cycles and batches.")

    @property
    def description(self) -> str:
        return _(
            "Returns the current state of DCD cycles and batches. "
            "Executes the commands cmk-dcd -Bv and cmk-dcd -Cv."
        )

    @property
    def filename(self) -> str:
        return "dcd"

    @override
    def contents(self, omd_root: Path) -> str:
        if not (cmk_dcd_binary := shutil.which("cmk-dcd")):
            return ""

        parameters = {
            "Batches": "-Bv",
            "Cycles": "-Cv",
        }

        output = []

        for what, parameter in parameters.items():
            try:
                output.append("[%s]" % what)
                output.append(
                    subprocess.check_output(
                        [cmk_dcd_binary, parameter],
                        text=True,
                        stderr=subprocess.STDOUT,
                    )
                )
            except subprocess.CalledProcessError:
                output.append("Unable to determine %s" % what)

        return "\n".join(output)
