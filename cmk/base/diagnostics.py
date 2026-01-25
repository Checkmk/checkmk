#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-any-return"
# mypy: disable-error-code="no-untyped-call"

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
from collections.abc import Callable
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import dataclass
from datetime import datetime
from functools import cache
from pathlib import Path
from typing import Any, Final, override

import requests

import livestatus

import cmk.ccc.version as cmk_version
import cmk.utils.paths
from cmk.automations.results import CreateDiagnosticsDumpResult
from cmk.base.automations.automations import Automation, AutomationContext, load_config
from cmk.base.base_app import CheckmkBaseApp
from cmk.base.config import LoadingResult
from cmk.base.configlib.loaded_config import LoadedConfigFragment
from cmk.base.modes.modes import Mode, Option
from cmk.ccc import site, store, tty
from cmk.ccc.crash_reporting import make_crash_report_base_path
from cmk.ccc.hostaddress import HostName
from cmk.ccc.i18n import _
from cmk.ccc.site import omd_site
from cmk.checkengine.plugins import AgentBasedPlugins
from cmk.inventory.structured_data import (
    InventoryStore,
    SDNodeName,
    serialize_tree,
)
from cmk.utils import log
from cmk.utils.diagnostics import (
    CheckmkFileEncryption,
    CheckmkFileInfoByRelFilePathMap,
    CheckmkFilesMap,
    COMPONENT_DIRECTORIES,
    deserialize_cl_parameters,
    DiagnosticsCLParameters,
    DiagnosticsElementCSVResult,
    DiagnosticsElementFilepaths,
    DiagnosticsElementJSONResult,
    DiagnosticsModesParameters,
    DiagnosticsOptionalParameters,
    FILE_MAP_CONFIG,
    FILE_MAP_CORE,
    FILE_MAP_LICENSING,
    FILE_MAP_LOG,
    FileMapConfig,
    OPT_BI_RUNTIME_DATA,
    OPT_CHECKMK_CONFIG_FILES,
    OPT_CHECKMK_CORE_FILES,
    OPT_CHECKMK_CRASH_REPORTS,
    OPT_CHECKMK_LICENSING_FILES,
    OPT_CHECKMK_LOG_FILES,
    OPT_CHECKMK_OVERVIEW,
    OPT_LOCAL_FILES,
    OPT_OMD_CONFIG,
    OPT_PERFORMANCE_GRAPHS,
)
from cmk.utils.licensing.usage import deserialize_dump
from cmk.utils.local_secrets import SiteInternalSecret
from cmk.utils.log import console, section
from cmk.utils.paths import omd_root

# TODO: why is there localization in this module?


# I think for proper separation, we need to pass these from the outside to this module.
@dataclass(frozen=True, kw_only=True)
class _DiagnosticsElement:
    ident: str
    title: str
    description: str
    content: str
    exception: Exception | None


SUFFIX = ".tar.gz"


def automation_create_diagnostics_dump(
    core_performance_settings: Callable[[LoadedConfigFragment], dict[str, int]],
) -> Automation:
    return Automation(
        ident="create-diagnostics-dump",
        handler=_make_automation_create_diagnostics_dump(core_performance_settings),
    )


def mode_create_diagnostics_dump(
    core_performance_settings: Callable[[LoadedConfigFragment], dict[str, int]],
) -> Mode:
    return Mode(
        long_option="create-diagnostics-dump",
        handler_function=_make_mode_create_diagnostics_dump(core_performance_settings),
        short_help="Create diagnostics dump",
        long_help=[
            "Create a dump containing information for diagnostic analysis "
            "in the folder var/check_mk/diagnostics."
        ],
        sub_options=_get_diagnostics_dump_sub_options(),
    )


def _make_mode_create_diagnostics_dump(
    core_performance_settings: Callable[[LoadedConfigFragment], dict[str, int]],
) -> Callable[[CheckmkBaseApp, DiagnosticsModesParameters], None]:
    def handler(app: CheckmkBaseApp, options: DiagnosticsModesParameters) -> None:
        # NOTE: All the stuff is logged on this level only, which is below the default WARNING level.
        log.logger.setLevel(logging.INFO)

        create_diagnostics_dump(
            load_config(
                discovery_rulesets=(),
                get_builtin_host_labels=app.get_builtin_host_labels,
            ).loaded_config,
            cmk.utils.diagnostics.deserialize_modes_parameters(options),
            core_performance_settings,
        )

    return handler


def _get_diagnostics_dump_sub_options() -> list[Option]:
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
            short_help="Pack configuration files ('*.mk' or '*.conf') from etc/checkmk",
            argument=True,
            argument_descr="FILE,FILE...",
        ),
        Option(
            long_option=OPT_CHECKMK_LOG_FILES,
            short_help="Pack log files ('*.log' or '*.state') from var/log",
            argument=True,
            argument_descr="FILE,FILE...",
        ),
    ]

    if cmk_version.edition(cmk.utils.paths.omd_root) is not cmk_version.Edition.COMMUNITY:
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
    return sub_options


def _make_automation_create_diagnostics_dump(
    core_performance_settings: Callable[[LoadedConfigFragment], dict[str, int]],
) -> Callable[
    [
        AutomationContext,
        DiagnosticsCLParameters,
        AgentBasedPlugins | None,
        LoadingResult | None,
    ],
    CreateDiagnosticsDumpResult,
]:
    def handler(
        ctx: AutomationContext,
        args: DiagnosticsCLParameters,
        plugins: AgentBasedPlugins | None,
        loading_result: LoadingResult | None,
    ) -> CreateDiagnosticsDumpResult:
        if loading_result is None:
            loading_result = load_config(
                discovery_rulesets=(),
                get_builtin_host_labels=ctx.get_builtin_host_labels,
            )
        buf = io.StringIO()
        with redirect_stdout(buf), redirect_stderr(buf):
            log.setup_console_logging()
            # NOTE: All the stuff is logged on this level only, which is below the default WARNING level.
            log.logger.setLevel(logging.INFO)
            dump = DiagnosticsDump(
                loading_result.loaded_config,
                core_performance_settings,
                deserialize_cl_parameters(args),
            )
            dump.create()
            return CreateDiagnosticsDumpResult(
                output=buf.getvalue(),
                tarfile_path=str(dump.tarfile_path),
                tarfile_created=dump.tarfile_created,
            )

    return handler


def create_diagnostics_dump(
    loaded_config: LoadedConfigFragment,
    parameters: DiagnosticsOptionalParameters | None,
    core_performance_settings: Callable[[LoadedConfigFragment], dict[str, int]],
) -> None:
    dump = DiagnosticsDump(loaded_config, core_performance_settings, parameters)
    dump.create()

    section.section_step("Creating diagnostics dump", verbose=False)
    if dump.tarfile_created:
        console.info(f"{_format_filepath(dump.tarfile_path)}")
    else:
        console.info(f"{_GAP}No dump")


#   .--format helper-------------------------------------------------------.
#   |   __                            _     _          _                   |
#   |  / _| ___  _ __ _ __ ___   __ _| |_  | |__   ___| |_ __   ___ _ __   |
#   | | |_ / _ \| '__| '_ ` _ \ / _` | __| | '_ \ / _ \ | '_ \ / _ \ '__|  |
#   | |  _| (_) | |  | | | | | | (_| | |_  | | | |  __/ | |_) |  __/ |     |
#   | |_|  \___/|_|  |_| |_| |_|\__,_|\__| |_| |_|\___|_| .__/ \___|_|     |
#   |                                                   |_|                |
#   '----------------------------------------------------------------------'

_GAP = 4 * " "


def _format_filepath(filepath: Path) -> str:
    return f"{_GAP}{str(filepath.relative_to(cmk.utils.paths.omd_root))}"


def _format_title(title: str) -> str:
    return f"{_GAP}{tty.green}{title}{tty.normal}:"


def _format_description(description: str) -> str:
    return textwrap.fill(
        description,
        width=52,
        initial_indent=2 * _GAP,
        subsequent_indent=2 * _GAP,
    )


def _format_error(error: str) -> str:
    return f"{2 * _GAP}{tty.error} - {error}"


# .
#   .--dump----------------------------------------------------------------.
#   |                         _                                            |
#   |                      __| |_   _ _ __ ___  _ __                       |
#   |                     / _` | | | | '_ ` _ \| '_ \                      |
#   |                    | (_| | |_| | | | | | | |_) |                     |
#   |                     \__,_|\__,_|_| |_| |_| .__/                      |
#   |                                          |_|                         |
#   '----------------------------------------------------------------------'


class DiagnosticsDump:
    """Caring about the persistance of diagnostics dumps in the local site"""

    _keep_num_dumps = 10

    def __init__(
        self,
        loaded_config: LoadedConfigFragment,
        core_performance_settings: Callable[[LoadedConfigFragment], dict[str, int]],
        parameters: DiagnosticsOptionalParameters | None = None,
    ) -> None:
        self.fixed_elements = self._get_fixed_elements(loaded_config, core_performance_settings)
        self.optional_elements = self._get_optional_elements(parameters)
        self.elements = self.fixed_elements + self.optional_elements

        dump_folder = cmk.utils.paths.diagnostics_dir
        self.dump_folder = dump_folder
        _file_name = "sddump_%s" % str(uuid.uuid4())
        self.tarfile_path = dump_folder.joinpath(_file_name).with_suffix(SUFFIX)
        self.tarfile_created = False

    def _get_fixed_elements(
        self,
        loaded_config: LoadedConfigFragment,
        core_performance_settings: Callable[[LoadedConfigFragment], dict[str, int]],
    ) -> list[ABCDiagnosticsElement]:
        fixed_elements = [
            GeneralDiagnosticsElement(),
            PerfDataDiagnosticsElement(loaded_config, core_performance_settings),
            HWDiagnosticsElement(),
            VendorDiagnosticsElement(),
            EnvironmentDiagnosticsElement(),
            FilesSizeCSVDiagnosticsElement(),
            PipFreezeDiagnosticsElement(),
            SELinuxJSONDiagnosticsElement(),
            DpkgCSVDiagnosticsElement(),
            RpmCSVDiagnosticsElement(),
            CMAJSONDiagnosticsElement(),
        ]

        if cmk_version.edition(cmk.utils.paths.omd_root) is not cmk_version.Edition.COMMUNITY:
            fixed_elements.append(DCDDiagnosticsElement())

        return fixed_elements

    def _get_optional_elements(
        self, parameters: DiagnosticsOptionalParameters | None
    ) -> list[ABCDiagnosticsElement]:
        if parameters is None:
            return []

        optional_elements: list[ABCDiagnosticsElement] = []
        if parameters.get(OPT_LOCAL_FILES):
            optional_elements.append(MKPFindTextDiagnosticsElement())
            optional_elements.append(MKPShowTextDiagnosticsElement())
            optional_elements.append(MKPListTextDiagnosticsElement())

        if parameters.get(OPT_OMD_CONFIG):
            optional_elements.append(OMDConfigDiagnosticsElement())

        if OPT_CHECKMK_OVERVIEW in parameters:
            content = ""
            exception_for_later = None
            try:
                content = _get_checkmk_overview_content(
                    InventoryStore(cmk.utils.paths.omd_root),
                    parameters.get(OPT_CHECKMK_OVERVIEW, ""),
                )
            except Exception as e:
                exception_for_later = e

            optional_elements.append(
                _DiagnosticsElementWrapper(
                    _DiagnosticsElement(
                        ident="checkmk_overview.json",
                        title=_("Checkmk overview of Checkmk server"),
                        description=_(
                            "Checkmk agent, number, version and edition of sites, cluster host; "
                            "number of hosts, services, CMK Helper, Live Helper, "
                            "Helper usage; state of daemons: Apache, Core, Crontab, "
                            "DCD, Liveproxyd, MKEventd, MKNotifyd, RRDCached "
                            "(agent plug-in mk_inventory needs to be installed)"
                        ),
                        content=content,
                        exception=exception_for_later,
                    )
                )
            )

        if parameters.get(OPT_CHECKMK_CRASH_REPORTS):
            optional_elements.append(CrashDumpsDiagnosticsElement())

        if parameters.get(OPT_BI_RUNTIME_DATA):
            optional_elements.append(BIDataDiagnosticsElement())

        rel_checkmk_config_files = parameters.get(OPT_CHECKMK_CONFIG_FILES)
        if rel_checkmk_config_files:
            optional_elements.append(CheckmkConfigFilesDiagnosticsElement(rel_checkmk_config_files))

        rel_checkmk_log_files = parameters.get(OPT_CHECKMK_LOG_FILES)
        if rel_checkmk_log_files:
            optional_elements.append(CheckmkLogFilesDiagnosticsElement(rel_checkmk_log_files))

        for dir_comp in COMPONENT_DIRECTORIES:
            if dir_comp in parameters:
                for directory in COMPONENT_DIRECTORIES[dir_comp]["abs_dirs"]:
                    optional_elements.append(
                        CheckmkDirectoryDiagnosticsElement(directory, rel=False)
                    )
                for directory in COMPONENT_DIRECTORIES[dir_comp]["rel_dirs"]:
                    optional_elements.append(
                        CheckmkDirectoryDiagnosticsElement(directory, rel=True)
                    )

        # CEE options
        if cmk_version.edition(cmk.utils.paths.omd_root) is not cmk_version.Edition.COMMUNITY:
            rel_checkmk_core_files = parameters.get(OPT_CHECKMK_CORE_FILES)
            if rel_checkmk_core_files:
                optional_elements.append(CheckmkCoreFilesDiagnosticsElement(rel_checkmk_core_files))
                optional_elements.append(CMCDumpDiagnosticsElement())

            if OPT_PERFORMANCE_GRAPHS in parameters:
                optional_elements.append(
                    PerformanceGraphsDiagnosticsElement(parameters.get(OPT_PERFORMANCE_GRAPHS, ""))
                )

            rel_checkmk_licensing_files = parameters.get(OPT_CHECKMK_LICENSING_FILES)
            if rel_checkmk_licensing_files:
                optional_elements.append(
                    CheckmkLicensingFilesDiagnosticsElement(rel_checkmk_licensing_files)
                )

        return optional_elements

    def create(self) -> None:
        self._create_dump_folder()
        self._create_tarfile()
        self._cleanup_dump_folder()

    def _create_dump_folder(self) -> None:
        section.section_step("Create dump folder")
        console.verbose(f"{_format_filepath(self.dump_folder)}")
        self.dump_folder.mkdir(parents=True, exist_ok=True)

    def _create_tarfile(self) -> None:
        with (
            tarfile.open(name=self.tarfile_path, mode="w:gz") as tar,
            tempfile.TemporaryDirectory(dir=self.dump_folder) as tmp_dump_folder,
        ):
            for filepath in self._get_filepaths(Path(tmp_dump_folder)):
                rel_path = str(filepath).replace(str(tmp_dump_folder), "")
                tar.add(str(filepath), arcname=rel_path)
                self.tarfile_created = True

    def _get_filepaths(self, tmp_dump_folder: Path) -> list[Path]:
        section.section_step("Collect diagnostics information", verbose=False)

        filepaths = []
        for element in self.elements:
            console.info(f"{_format_title(element.title)}")
            console.info(f"{_format_description(element.description)}")

            try:
                for filepath in element.add_or_get_files(tmp_dump_folder):
                    filepaths.append(filepath)

            except DiagnosticsElementError as e:
                console.info(f"{_format_error(str(e))}")
                continue

            except Exception:
                console.info(f"{_format_error(traceback.format_exc())}")
                continue

        return filepaths

    def _cleanup_dump_folder(self) -> None:
        if not self.tarfile_created:
            # Remove empty tarfile path
            self._remove_file(self.tarfile_path)

        dumps = sorted(
            [(dump.stat().st_mtime, dump) for dump in self.dump_folder.glob("*%s" % SUFFIX)],
            key=lambda t: t[0],
        )[: -self._keep_num_dumps]

        section.section_step(
            "Cleanup dump folder", add_info="keep last %d dumps" % self._keep_num_dumps
        )
        for _mtime, filepath in dumps:
            console.verbose(f"{_format_filepath(filepath)}")
            self._remove_file(filepath)

    def _remove_file(self, filepath: Path) -> None:
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


@cache
def get_omd_config() -> site.OMDConfig:
    # Useless function, useless cache.  See comment
    # in cmk.ccc.site
    return site.get_omd_config(cmk.utils.paths.omd_root)


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
        raise DiagnosticsElementError("No Checkmk server found")


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


class ABCDiagnosticsElement(abc.ABC):
    @property
    @abc.abstractmethod
    def ident(self) -> str:
        raise NotImplementedError()

    @property
    @abc.abstractmethod
    def title(self) -> str:
        raise NotImplementedError()

    @property
    @abc.abstractmethod
    def description(self) -> str:
        raise NotImplementedError()

    @abc.abstractmethod
    def add_or_get_files(self, tmp_dump_folder: Path) -> DiagnosticsElementFilepaths:
        # Please note the case if there are more than one filepath results. A Python generator
        # is executed until the first raise. Then it will be stopped and all generator states
        # are gone. Correctly calculated filepaths till then are yielded.
        # (Example: CheckmkConfigFilesDiagnosticsElement: collect errors and raise at the end)
        raise NotImplementedError()


class ABCDiagnosticsElementTextDump(ABCDiagnosticsElement):
    @override
    def add_or_get_files(self, tmp_dump_folder: Path) -> DiagnosticsElementFilepaths:
        filepath = tmp_dump_folder.joinpath(self.ident)
        store.save_text_to_file(filepath, self._collect_infos())
        yield filepath

    @abc.abstractmethod
    def _collect_infos(self) -> str:
        raise NotImplementedError()


class _DiagnosticsElementWrapper(ABCDiagnosticsElementTextDump):
    """Temporary wrapper to prepare for a cleaner diagnostics API (WIP)"""

    def __init__(self, wrapped: _DiagnosticsElement):
        self._wrapped: Final = wrapped

    @override
    @property
    def ident(self) -> str:
        return self._wrapped.ident

    @override
    @property
    def title(self) -> str:
        return self._wrapped.title

    @override
    @property
    def description(self) -> str:
        return self._wrapped.description

    @override
    def _collect_infos(self) -> str:
        if self._wrapped.exception:
            raise self._wrapped.exception
        return self._wrapped.content


class ABCDiagnosticsElementJSONDump(ABCDiagnosticsElement):
    @override
    def add_or_get_files(self, tmp_dump_folder: Path) -> DiagnosticsElementFilepaths:
        infos = self._collect_infos()
        if not infos:
            raise DiagnosticsElementError("No information")

        filepath = tmp_dump_folder.joinpath(self.ident).with_suffix(".json")
        store.save_text_to_file(filepath, json.dumps(infos, sort_keys=True, indent=4))
        yield filepath

    @abc.abstractmethod
    def _collect_infos(self) -> DiagnosticsElementJSONResult:
        raise NotImplementedError()


class ABCDiagnosticsElementCSVDump(ABCDiagnosticsElement):
    @override
    def add_or_get_files(self, tmp_dump_folder: Path) -> DiagnosticsElementFilepaths:
        infos = self._collect_infos()
        if not infos:
            raise DiagnosticsElementError("No information")

        filepath = tmp_dump_folder.joinpath(self.ident).with_suffix(".csv")
        store.save_text_to_file(filepath, infos)
        yield filepath

    @abc.abstractmethod
    def _collect_infos(self) -> DiagnosticsElementCSVResult:
        raise NotImplementedError()


#   ---csv dumps-----------------------------------------------------------


class FilesSizeCSVDiagnosticsElement(ABCDiagnosticsElementCSVDump):
    @override
    @property
    def ident(self) -> str:
        return "file_size"

    @override
    @property
    def title(self) -> str:
        return _("File Size")

    @override
    @property
    def description(self) -> str:
        return _("List of all files in the site including their size")

    def _collect_infos(self) -> DiagnosticsElementCSVResult:
        csv_data = []
        csv_data.append("size;path;owner;group;mode;changed")
        tmp_file_regex = re.compile(r"^\..*\.new.*")
        for dirpath, _dirnames, filenames in os.walk(cmk.utils.paths.omd_root):
            for file in filenames:
                f = Path(dirpath).joinpath(file)
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


class DpkgCSVDiagnosticsElement(ABCDiagnosticsElementCSVDump):
    @override
    @property
    def ident(self) -> str:
        return "dpkg_packages"

    @override
    @property
    def title(self) -> str:
        return _("Dpkg packages information")

    @override
    @property
    def description(self) -> str:
        return _("Output of `dpkg -l`. See the corresponding command line help for more details.")

    def _collect_infos(self) -> DiagnosticsElementCSVResult:
        if not (dpkg_binary := shutil.which("dpkg")):
            return ""

        dpkg_output = subprocess.check_output([dpkg_binary, "-l"], text=True)
        return "\n".join(
            [";".join(l.split(maxsplit=4)) for l in dpkg_output.split("\n") if len(l.split()) > 4]
        )


class RpmCSVDiagnosticsElement(ABCDiagnosticsElementCSVDump):
    @override
    @property
    def ident(self) -> str:
        return "rpm_packages"

    @override
    @property
    def title(self) -> str:
        return _("Rpm packages information")

    @override
    @property
    def description(self) -> str:
        return _("Output of `rpm -qa`. See the corresponding command line help for more details.")

    def _collect_infos(self) -> DiagnosticsElementCSVResult:
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


class GeneralDiagnosticsElement(ABCDiagnosticsElementJSONDump):
    @override
    @property
    def ident(self) -> str:
        return "general"

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

    def _collect_infos(self) -> DiagnosticsElementJSONResult:
        version_infos = cmk_version.get_general_version_infos(omd_root)
        time_obj = datetime.fromtimestamp(version_infos.get("time", 0.0))
        return {
            "arch": platform.machine(),
            "time_human_readable": time_obj.isoformat(sep=" "),
            "time": version_infos["time"],
            "os": version_infos["os"],
            "version": version_infos["version"],
            "edition": version_infos["edition"],
            "core": version_infos["core"],
            "python_version": version_infos["python_version"],
            "python_paths": list(version_infos["python_paths"]),
        }


class PerfDataDiagnosticsElement(ABCDiagnosticsElementJSONDump):
    def __init__(
        self,
        load_config: LoadedConfigFragment,
        core_performance_settings: Callable[[LoadedConfigFragment], dict[str, int]],
    ) -> None:
        self._loaded_config: Final = load_config
        self._core_performance_settings: Final = core_performance_settings

    @override
    @property
    def ident(self) -> str:
        return "perfdata"

    @override
    @property
    def title(self) -> str:
        return _("Metrics")

    @override
    @property
    def description(self) -> str:
        return _("Metrics related to sizing, e.g. number of helpers, hosts, services")

    def _collect_infos(self) -> DiagnosticsElementJSONResult:
        # Get the runtime performance data from livestatus
        query = "GET status\nColumnHeaders: on"
        result = livestatus.LocalConnection().query(query)
        performance_data = {
            key: result[1][i]
            for i in range(0, len(result[0]))
            if (key := result[0][i]) not in ["license_usage_history"]
        }

        performance_data.update(self._core_performance_settings(self._loaded_config))

        return performance_data


def collect_infos_hw(proc_base_path: Path) -> DiagnosticsElementJSONResult:
    # Get the information from the proc files

    hw_info: dict[str, dict[str, str]] = {}

    for procfile, parser in [
        ("meminfo", _meminfo_proc_parser),
        ("loadavg", _load_avg_proc_parser),
        ("cpuinfo", _cpuinfo_proc_parser),
    ]:
        filepath = proc_base_path.joinpath(procfile)
        if content := _try_to_read(filepath):
            hw_info[procfile] = parser(content)

    return hw_info


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


class HWDiagnosticsElement(ABCDiagnosticsElementJSONDump):
    @override
    @property
    def ident(self) -> str:
        return "hwinfo"

    @override
    @property
    def title(self) -> str:
        return _("HW Information")

    @override
    @property
    def description(self) -> str:
        return _("Hardware information of the Checkmk server")

    def _collect_infos(self) -> DiagnosticsElementJSONResult:
        return collect_infos_hw(Path("/proc"))


def collect_infos_vendor(sys_path: Path) -> DiagnosticsElementJSONResult:
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
        file_content = store.load_text_from_file(sys_path.joinpath(sys_file)).replace("\n", "")
        if sys_file == "chassis_asset_tag":
            if file_content == _AZURE_TAG:
                vendor_info[sys_file] = "Azure"
            else:
                vendor_info[sys_file] = "Other"
        else:
            vendor_info[sys_file] = file_content

    return vendor_info


class VendorDiagnosticsElement(ABCDiagnosticsElementJSONDump):
    @override
    @property
    def ident(self) -> str:
        return "vendorinfo"

    @override
    @property
    def title(self) -> str:
        return _("Vendor Information")

    @override
    @property
    def description(self) -> str:
        return _("HW vendor information of the Checkmk server")

    def _collect_infos(self) -> DiagnosticsElementJSONResult:
        return collect_infos_vendor(Path("/sys/class/dmi/id"))


class EnvironmentDiagnosticsElement(ABCDiagnosticsElementJSONDump):
    @override
    @property
    def ident(self) -> str:
        return "environment"

    @override
    @property
    def title(self) -> str:
        return _("Environment Variables")

    @override
    @property
    def description(self) -> str:
        return _("Variables set in the site user's environment")

    def _collect_infos(self) -> DiagnosticsElementJSONResult:
        # Get the environment variables

        return dict(os.environ)


class PipFreezeDiagnosticsElement(ABCDiagnosticsElementJSONDump):
    @override
    @property
    def ident(self) -> str:
        return "pip_freeze"

    @override
    @property
    def title(self) -> str:
        return _("pip freeze output")

    @override
    @property
    def description(self) -> str:
        return _("The installed Python modules and their versions")

    def _collect_infos(self) -> DiagnosticsElementJSONResult:
        # Execute pip freeze and convert to JSON

        lines = subprocess.check_output(["pip3", "freeze", "--all"], text=True).split("\n")
        return {l.split("==")[0]: l.split("==")[1] for l in lines if "==" in l}


class MKPFindTextDiagnosticsElement(ABCDiagnosticsElementJSONDump):
    @override
    @property
    def ident(self) -> str:
        return "mkp_find_all.json"

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

    def _collect_infos(self) -> DiagnosticsElementJSONResult:
        try:
            return json.loads(
                subprocess.check_output(["mkp", "find", "--all", "--json"], text=True)
            )
        except subprocess.CalledProcessError as e:
            console.info(f"{_format_error(str(e.stderr))}\n")
            return {}


class MKPShowTextDiagnosticsElement(ABCDiagnosticsElementJSONDump):
    @override
    @property
    def ident(self) -> str:
        return "mkp_show_all.json"

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

    def _collect_infos(self) -> DiagnosticsElementJSONResult:
        try:
            return json.loads(subprocess.check_output(["mkp", "show-all", "--json"], text=True))
        except subprocess.CalledProcessError as e:
            console.info(f"{_format_error(str(e.stderr))}\n")
            return {}


class MKPListTextDiagnosticsElement(ABCDiagnosticsElementJSONDump):
    @override
    @property
    def ident(self) -> str:
        return "mkp_list.json"

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

    def _collect_infos(self) -> DiagnosticsElementJSONResult:
        try:
            return json.loads(subprocess.check_output(["mkp", "list", "--json"], text=True))
        except subprocess.CalledProcessError as e:
            console.info(f"{_format_error(str(e.stderr))}\n")
            return {}


class SELinuxJSONDiagnosticsElement(ABCDiagnosticsElementJSONDump):
    @override
    @property
    def ident(self) -> str:
        return "selinux"

    @override
    @property
    def title(self) -> str:
        return _("SELinux information")

    @override
    @property
    def description(self) -> str:
        return _("Output of `sestatus`. See the corresponding command line help for more details.")

    def _collect_infos(self) -> DiagnosticsElementJSONResult:
        if not (selinux_binary := shutil.which("sestatus")):
            return {}

        return {
            line.split(":")[0]: line.split(":")[1].lstrip()
            for line in subprocess.check_output(selinux_binary, text=True).split("\n")
            if ":" in line
        }


def _try_to_read(filename: str | Path) -> list[str]:
    try:
        with open(filename) as f:
            content = f.readlines()

    except (PermissionError, FileNotFoundError):
        return []

    return [l.rstrip() for l in content]


class CMAJSONDiagnosticsElement(ABCDiagnosticsElementJSONDump):
    @override
    @property
    def ident(self) -> str:
        return "appliance"

    @override
    @property
    def title(self) -> str:
        return _("Checkmk appliance information")

    @override
    @property
    def description(self) -> str:
        return _("Information about the appliance hardware and firmware version.")

    def _collect_infos(self) -> DiagnosticsElementJSONResult:
        cma_infos: dict[str, str | dict[str, str]] = {}

        if hw_content := _try_to_read("/etc/cma/hw"):
            cma_infos["hw"] = dict([l.replace("'", "").split("=") for l in hw_content if "=" in l])

        if fw_content := _try_to_read("/ro/usr/share/cma/version"):
            cma_infos["fw"] = fw_content[0]

        return cma_infos


class OMDConfigDiagnosticsElement(ABCDiagnosticsElementJSONDump):
    @override
    @property
    def ident(self) -> str:
        return "omd_config"

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

    def _collect_infos(self) -> DiagnosticsElementJSONResult:
        return get_omd_config()


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
        raise DiagnosticsElementError("No HW/SW Inventory node 'Software > Applications > Checkmk'")
    return json.dumps(serialize_tree(node), sort_keys=True, indent=4)


#   ---collect exiting files------------------------------------------------


class ABCCheckmkFilesDiagnosticsElement(ABCDiagnosticsElement):
    def __init__(self, rel_checkmk_files: list[str]) -> None:
        self.rel_checkmk_files = rel_checkmk_files
        self.file_map_config = self._file_map_config

    @property
    def _checkmk_files_map(self) -> CheckmkFilesMap:
        return self.file_map_config["map_generator"](
            self.file_map_config["base_folder"],
            self.file_map_config["component_folder"],
            list(os.walk(self.file_map_config["base_folder"])),
            None,
        )

    @property
    @abc.abstractmethod
    def _file_map_config(self) -> FileMapConfig:
        raise NotImplementedError()

    def _copy_and_decrypt(self, rel_filepath: Path, tmp_dump_folder: Path) -> Path | None:
        checkmk_files_map = self._checkmk_files_map

        filepath = checkmk_files_map.get(str(rel_filepath))
        if filepath is None or not filepath.exists():
            return None

        # Respect file path (2), otherwise the paths of same named files are forgotten (1).
        # We want to pack a folder hierarchy.

        filename = Path(filepath).name
        subfolder = Path(str(filepath).replace(str(cmk.utils.paths.omd_root) + "/", "")).parent

        # Create relative path in tmp tree
        tmp_folder = tmp_dump_folder.joinpath(subfolder)
        tmp_folder.mkdir(parents=True, exist_ok=True)

        # Decrypt if file is encrypted, else only copy
        encryption = CheckmkFileEncryption.none

        tmp_filepath = tmp_folder.joinpath(filename)
        file_info = CheckmkFileInfoByRelFilePathMap.get(str(rel_filepath))

        if file_info is not None:
            encryption = file_info.encryption

        if encryption == CheckmkFileEncryption.rot47:
            with Path(filepath).open("rb") as source:
                json_data = json.dumps(deserialize_dump(source.read()), sort_keys=True, indent=4)
                store.save_text_to_file(tmp_filepath, json_data)
        # We 'encrypt' only license thingies at the moment, so there is currently no need to
        # sanitize encrypted files
        elif str(rel_filepath) == "multisite.d/sites.mk":
            sites = store.load_from_mk_file(
                filepath, key="sites", default=livestatus.SiteConfigurations({}), lock=False
            )
            store.save_to_mk_file(
                tmp_filepath,
                key="sites",
                value={
                    siteid: livestatus.sanitize_site_configuration(config)
                    for siteid, config in sites.items()
                },
            )
        else:
            shutil.copy(str(filepath), str(tmp_filepath))

        return tmp_filepath

    @override
    def add_or_get_files(self, tmp_dump_folder: Path) -> DiagnosticsElementFilepaths:
        unknown_files = []

        for rel_filepath in self.rel_checkmk_files:
            tmp_filepath = self._copy_and_decrypt(Path(rel_filepath), tmp_dump_folder)

            if tmp_filepath is None:
                unknown_files.append(str(rel_filepath))
                continue

            yield tmp_filepath

        if unknown_files:
            raise DiagnosticsElementError("No such files: %s" % ", ".join(unknown_files))


class CheckmkConfigFilesDiagnosticsElement(ABCCheckmkFilesDiagnosticsElement):
    @override
    @property
    def ident(self) -> str:
        # Unused because we directly pack the .mk or .conf file
        return "checkmk_config_files"

    @override
    @property
    def _file_map_config(self) -> FileMapConfig:
        return FILE_MAP_CONFIG

    @override
    @property
    def title(self) -> str:
        return _("Checkmk Configuration Files")

    @override
    @property
    def description(self) -> str:
        return _("Configuration files ('*.mk' or '*.conf') from etc/checkmk: %s") % ", ".join(
            self.rel_checkmk_files
        )


class CheckmkLogFilesDiagnosticsElement(ABCCheckmkFilesDiagnosticsElement):
    @override
    @property
    def ident(self) -> str:
        # Unused because we directly pack the .log or .state file
        return "checkmk_log_files"

    @override
    @property
    def _file_map_config(self) -> FileMapConfig:
        return FILE_MAP_LOG

    @override
    @property
    def title(self) -> str:
        return _("Checkmk Log Files")

    @override
    @property
    def description(self) -> str:
        return _("Log files ('*.log' or '*.state') from var/log: %s") % ", ".join(
            self.rel_checkmk_files
        )


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
    def ident(self) -> str:
        # Unused because we directly pack the .mk or .conf file
        return "checkmk_directory"

    @override
    @property
    def title(self) -> str:
        return _("Files in %s") % self.directory

    @override
    @property
    def description(self) -> str:
        return _("Configuration files from %s") % str(self.directory)

    @override
    def add_or_get_files(self, tmp_dump_folder: Path) -> DiagnosticsElementFilepaths:
        abs_path = self.directory
        if self.rel:
            abs_path = cmk.utils.paths.omd_root / self.directory

        if not abs_path.exists():
            return

        for path, dirs, files in os.walk(abs_path):
            for file in files:
                source_file = Path(path).joinpath(file)

                if self.rel:
                    tmp_target_folder = tmp_dump_folder / Path(path).relative_to(
                        cmk.utils.paths.omd_root
                    )
                else:
                    tmp_target_folder = tmp_dump_folder / "os_root" / Path(path).relative_to("/")

                tmp_file = tmp_target_folder.joinpath(file)
                tmp_target_folder.mkdir(parents=True, exist_ok=True)

                if not tmp_file.exists():
                    shutil.copy(str(source_file), str(tmp_file))

                yield tmp_file


#   ---cee dumps------------------------------------------------------------


class CheckmkCoreFilesDiagnosticsElement(ABCCheckmkFilesDiagnosticsElement):
    @override
    @property
    def ident(self) -> str:
        # Unused because we directly pack the config, state and history file
        return "checkmk_core_files"

    @override
    @property
    def _file_map_config(self) -> FileMapConfig:
        return FILE_MAP_CORE

    @override
    @property
    def title(self) -> str:
        return _("Checkmk Core Files")

    @override
    @property
    def description(self) -> str:
        return _("Core files (config, state and history) from var/check_mk/core: %s") % ", ".join(
            self.rel_checkmk_files
        )


class CheckmkLicensingFilesDiagnosticsElement(ABCCheckmkFilesDiagnosticsElement):
    @override
    @property
    def ident(self) -> str:
        # Unused because we directly pack the config, state and history file
        return "checkmk_licensing_files"

    @override
    @property
    def _file_map_config(self) -> FileMapConfig:
        return FILE_MAP_LICENSING

    @override
    @property
    def title(self) -> str:
        return _("Checkmk Licensing Files")

    @override
    @property
    def description(self) -> str:
        return _(
            "Licensing files (data, config and logs) from var/check_mk/licensing, etc/check_mk/multisite.d and var/log: %s"
        ) % ", ".join(self.rel_checkmk_files)


class PerformanceGraphsDiagnosticsElement(ABCDiagnosticsElement):
    def __init__(self, checkmk_server_host: str) -> None:
        self.checkmk_server_host = checkmk_server_host

    @override
    @property
    def ident(self) -> str:
        return "performance_graphs"

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
    def add_or_get_files(self, tmp_dump_folder: Path) -> DiagnosticsElementFilepaths:
        checkmk_server_host = verify_checkmk_server_host(self.checkmk_server_host)
        response = self._get_response(checkmk_server_host, get_omd_config())

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

        filepath = tmp_dump_folder.joinpath(self.ident).with_suffix(".pdf")
        with filepath.open("wb") as f:
            f.write(response.content)

        yield filepath

    def _get_response(
        self, checkmk_server_host: str, omd_config: site.OMDConfig
    ) -> requests.Response:
        internal_secret = "InternalToken %s" % (SiteInternalSecret().secret.b64_str)
        url = "http://{}:{}/{}/check_mk/report.py?".format(
            omd_config["CONFIG_APACHE_TCP_ADDR"],
            omd_config["CONFIG_APACHE_TCP_PORT"],
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


class BIDataDiagnosticsElement(ABCDiagnosticsElement):
    @override
    @property
    def ident(self) -> str:
        return "bi_runtime_data"

    @override
    @property
    def title(self) -> str:
        return _("Business Intelligence runtime data")

    @override
    @property
    def description(self) -> str:
        return _(
            "Cached data from Business Intelligence. "
            "Contains states, downtimes, acknowledgements and service periods "
            "for all hosts/services included in a BI aggregation."
        )

    @override
    def add_or_get_files(self, tmp_dump_folder: Path) -> DiagnosticsElementFilepaths:
        tmpdir = tmp_dump_folder.joinpath("tmp/check_mk/bi_cache")
        tmpdir.mkdir(parents=True, exist_ok=True)

        shutil.copytree(cmk.utils.paths.tmp_dir.joinpath("bi_cache"), tmpdir, dirs_exist_ok=True)
        yield tmpdir


class CrashDumpsDiagnosticsElement(ABCDiagnosticsElement):
    @override
    @property
    def ident(self) -> str:
        return "crashdumps"

    @override
    @property
    def title(self) -> str:
        return _("The latest crash dumps of each type")

    @override
    @property
    def description(self) -> str:
        return _("Returns the latest crash dumps of each type as found in var/checkmk/crashes")

    @override
    def add_or_get_files(self, tmp_dump_folder: Path) -> DiagnosticsElementFilepaths:
        for category in make_crash_report_base_path(omd_root).glob("*"):
            tmpdir = tmp_dump_folder.joinpath("var/check_mk/crashes/%s" % category.name)
            tmpdir.mkdir(parents=True, exist_ok=True)

            sorted_dumps = sorted(category.glob("*"), key=lambda path: int(path.stat().st_mtime))

            if sorted_dumps:
                # Determine the latest file of that category
                dumpfile_path = sorted_dumps[-1]

                # Pack the dump into a .tar.gz, so it can easily be uploaded
                # to https://crash.checkmk.com/
                tarfile_path = tmpdir.joinpath(dumpfile_path.name).with_suffix(".tar.gz")

                with tarfile.open(name=tarfile_path, mode="w:gz") as tar:
                    for file in dumpfile_path.iterdir():
                        rel_path = str(file).replace(str(dumpfile_path) + "/", "")
                        tar.add(str(file), arcname=rel_path)

                yield tarfile_path


class CMCDumpDiagnosticsElement(ABCDiagnosticsElement):
    @override
    @property
    def ident(self) -> str:
        return "cmcdump"

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
    def add_or_get_files(self, tmp_dump_folder: Path) -> DiagnosticsElementFilepaths:
        command = [str(Path(cmk.utils.paths.omd_root).joinpath("bin/cmcdump"))]

        for dump_args in (None, "--config"):
            tmpdir = tmp_dump_folder.joinpath("var/check_mk/core")
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
                console.info(f"{_format_error(str(e))}")
                continue

            filepath = tmpdir.joinpath(f"{self.ident}{suffix}")
            with filepath.open("w") as f:
                f.write(output)

            yield filepath


class DCDDiagnosticsElement(ABCDiagnosticsElementTextDump):
    @property
    def ident(self) -> str:
        return "dcd"

    @property
    def title(self) -> str:
        return _("DCD cycles and batches.")

    @property
    def description(self) -> str:
        return _(
            "Returns the current state of DCD cycles and batches. "
            "Executes the commands cmk-dcd -Bv and cmk-dcd -Cv."
        )

    def _collect_infos(self) -> str:
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
