#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import abc
import json
import os
import platform
import shutil
import subprocess
import tarfile
import tempfile
import textwrap
import traceback
import urllib.parse
import uuid
from collections.abc import Iterator, Mapping
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Any

import requests

import livestatus

import cmk.utils.paths
import cmk.utils.site as site
import cmk.utils.store as store
import cmk.utils.tty as tty
import cmk.utils.version as cmk_version
from cmk.utils.crypto.secrets import AutomationUserSecret
from cmk.utils.diagnostics import (
    CheckmkFilesMap,
    DiagnosticsElementCSVResult,
    DiagnosticsElementFilepaths,
    DiagnosticsElementJSONResult,
    DiagnosticsOptionalParameters,
    get_checkmk_config_files_map,
    get_checkmk_core_files_map,
    get_checkmk_licensing_files_map,
    get_checkmk_log_files_map,
    OPT_CHECKMK_CONFIG_FILES,
    OPT_CHECKMK_CORE_FILES,
    OPT_CHECKMK_LICENSING_FILES,
    OPT_CHECKMK_LOG_FILES,
    OPT_CHECKMK_OVERVIEW,
    OPT_LOCAL_FILES,
    OPT_OMD_CONFIG,
    OPT_PERFORMANCE_GRAPHS,
)
from cmk.utils.i18n import _
from cmk.utils.log import console, section
from cmk.utils.site import omd_site
from cmk.utils.structured_data import load_tree
from cmk.utils.type_defs import HostName, UserId

if cmk_version.is_enterprise_edition():
    from cmk.base.cee.diagnostics import (  # type: ignore[import]  # pylint: disable=no-name-in-module,import-error
        cmc_specific_attrs,
    )
else:

    def cmc_specific_attrs() -> Mapping[str, int]:
        return {}


SUFFIX = ".tar.gz"


def create_diagnostics_dump(parameters: DiagnosticsOptionalParameters | None) -> None:
    dump = DiagnosticsDump(parameters)
    dump.create()

    section.section_step("Creating diagnostics dump", verbose=False)
    if dump.tarfile_created:
        console.info("%s\n", _format_filepath(dump.tarfile_path))
    else:
        console.info("%s%s\n", _GAP, "No dump")


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


def _format_error(error):
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

    _keep_num_dumps = 5

    def __init__(self, parameters: DiagnosticsOptionalParameters | None = None) -> None:
        self.fixed_elements = self._get_fixed_elements()
        self.optional_elements = self._get_optional_elements(parameters)
        self.elements = self.fixed_elements + self.optional_elements

        dump_folder = cmk.utils.paths.diagnostics_dir
        self.dump_folder = dump_folder
        _file_name = "sddump_%s" % str(uuid.uuid4())
        self.tarfile_path = dump_folder.joinpath(_file_name).with_suffix(SUFFIX)
        self.tarfile_created = False

    def _get_fixed_elements(self) -> list[ABCDiagnosticsElement]:
        return [
            GeneralDiagnosticsElement(),
            PerfDataDiagnosticsElement(),
            HWDiagnosticsElement(),
            EnvironmentDiagnosticsElement(),
            FilesSizeCSVDiagnosticsElement(),
        ]

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

        if parameters.get(OPT_CHECKMK_OVERVIEW):
            optional_elements.append(CheckmkOverviewDiagnosticsElement())

        rel_checkmk_config_files = parameters.get(OPT_CHECKMK_CONFIG_FILES)
        if rel_checkmk_config_files:
            optional_elements.append(CheckmkConfigFilesDiagnosticsElement(rel_checkmk_config_files))

        rel_checkmk_log_files = parameters.get(OPT_CHECKMK_LOG_FILES)
        if rel_checkmk_log_files:
            optional_elements.append(CheckmkLogFilesDiagnosticsElement(rel_checkmk_log_files))

        # CEE options
        if not cmk_version.is_raw_edition():
            rel_checkmk_core_files = parameters.get(OPT_CHECKMK_CORE_FILES)
            if rel_checkmk_core_files:
                optional_elements.append(CheckmkCoreFilesDiagnosticsElement(rel_checkmk_core_files))
                optional_elements.append(CMCDumpDiagnosticsElement())

            if parameters.get(OPT_PERFORMANCE_GRAPHS):
                optional_elements.append(PerformanceGraphsDiagnosticsElement())

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
        console.verbose("%s\n", _format_filepath(self.dump_folder))
        self.dump_folder.mkdir(parents=True, exist_ok=True)

    def _create_tarfile(self) -> None:
        with tarfile.open(name=self.tarfile_path, mode="w:gz") as tar, tempfile.TemporaryDirectory(
            dir=self.dump_folder
        ) as tmp_dump_folder:
            for filepath in self._get_filepaths(Path(tmp_dump_folder)):
                rel_path = str(filepath).replace(str(tmp_dump_folder), "")
                tar.add(str(filepath), arcname=rel_path)
                self.tarfile_created = True

    def _get_filepaths(self, tmp_dump_folder: Path) -> list[Path]:
        section.section_step("Collect diagnostics information", verbose=False)

        filepaths = []
        for element in self.elements:
            console.info("%s\n", _format_title(element.title))
            console.info("%s\n", _format_description(element.description))

            try:
                for filepath in element.add_or_get_files(tmp_dump_folder):
                    filepaths.append(filepath)

            except DiagnosticsElementError as e:
                console.info("%s\n", _format_error(str(e)))
                continue

            except Exception:
                console.info("%s\n", _format_error(traceback.format_exc()))
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
            console.verbose("%s\n", _format_filepath(filepath))
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


@lru_cache
def get_omd_config() -> site.OMDConfig:
    return site.get_omd_config()


@lru_cache
def get_checkmk_server_name() -> HostName | None:
    result = livestatus.LocalConnection().query(
        f"GET services\nColumns: host_name\nFilter: service_description ~ OMD {omd_site()} performance\n"
    )
    try:
        return HostName(result[0][0])
    except IndexError:
        return None


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
    def add_or_get_files(self, tmp_dump_folder: Path) -> Iterator[Path]:
        filepath = tmp_dump_folder.joinpath(self.ident)
        store.save_text_to_file(filepath, self._collect_infos())
        yield filepath

    @abc.abstractmethod
    def _collect_infos(self) -> str:
        raise NotImplementedError()


class ABCDiagnosticsElementJSONDump(ABCDiagnosticsElement):
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
    @property
    def ident(self) -> str:
        return "file_size"

    @property
    def title(self) -> str:
        return _("File Size")

    @property
    def description(self) -> str:
        return _("List of all files in the site including their size")

    def _collect_infos(self) -> DiagnosticsElementCSVResult:
        csv_data = []
        csv_data.append("size;path")
        for path, _dirs, files in os.walk(cmk.utils.paths.omd_root):
            for f in files:
                fp = os.path.join(path, f)
                if not os.path.islink(fp):
                    csv_data.append("%d;%s" % (os.path.getsize(fp), str(fp)))
        return "\n".join(csv_data)


#   ---json dumps-----------------------------------------------------------


class GeneralDiagnosticsElement(ABCDiagnosticsElementJSONDump):
    @property
    def ident(self) -> str:
        return "general"

    @property
    def title(self) -> str:
        return _("General")

    @property
    def description(self) -> str:
        return _(
            "OS, Checkmk version and edition, Time, Core, Python version and paths, Architecture"
        )

    def _collect_infos(self) -> DiagnosticsElementJSONResult:
        version_infos = cmk_version.get_general_version_infos()
        version_infos["arch"] = platform.machine()
        time_obj = datetime.fromtimestamp(version_infos.get("time", 0))
        version_infos["time_human_readable"] = time_obj.isoformat(sep=" ")
        return version_infos


class PerfDataDiagnosticsElement(ABCDiagnosticsElementJSONDump):
    @property
    def ident(self) -> str:
        return "perfdata"

    @property
    def title(self) -> str:
        return _("Performance Data")

    @property
    def description(self) -> str:
        return _("Performance Data related to sizing, e.g. number of helpers, hosts, services")

    def _collect_infos(self) -> DiagnosticsElementJSONResult:
        # Get the runtime performance data from livestatus
        query = "GET status\nColumnHeaders: on"
        result = livestatus.LocalConnection().query(query)
        performance_data = {
            key: result[1][i]
            for i in range(0, len(result[0]))
            if (key := result[0][i]) not in ["license_usage_history"]
        }

        performance_data.update(cmc_specific_attrs())

        return performance_data


class HWDiagnosticsElement(ABCDiagnosticsElementJSONDump):
    @property
    def ident(self) -> str:
        return "hwinfo"

    @property
    def title(self) -> str:
        return _("HW Information")

    @property
    def description(self) -> str:
        return _("Hardware information of the Checkmk Server")

    def _collect_infos(self) -> DiagnosticsElementJSONResult:
        # Get the information from the proc files

        hw_info: dict[str, dict[str, str]] = {}

        for procfile, parser in [
            ("meminfo", self._meminfo_proc_parser),
            ("loadavg", self._load_avg_proc_parser),
            ("cpuinfo", self._cpuinfo_proc_parser),
        ]:
            filepath = Path("/proc").joinpath(procfile)
            try:
                content = self._get_proc_content(filepath)
            except FileNotFoundError:
                continue

            hw_info[procfile] = parser(content)

        return hw_info

    def _get_proc_content(self, filepath: Path) -> list[str]:
        with open(filepath) as f:
            return f.read().splitlines()

    def _meminfo_proc_parser(self, content: list[str]) -> dict[str, str]:
        info: dict[str, str] = {}

        for line in content:
            if line == "":
                continue

            key, value = (w.strip() for w in line.split(":", 1))
            info[key.replace(" ", "_")] = value

        return info

    def _cpuinfo_proc_parser(self, content: list[str]) -> dict[str, str]:
        cpu_info: dict[str, Any] = {}
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

        cpu_info["num_processors"] = str(num_processors)
        return cpu_info

    def _load_avg_proc_parser(self, content: list[str]) -> dict[str, str]:
        return dict(zip(["loadavg_1", "loadavg_5", "loadavg_15"], content[0].split()))


class EnvironmentDiagnosticsElement(ABCDiagnosticsElementJSONDump):
    @property
    def ident(self) -> str:
        return "environment"

    @property
    def title(self) -> str:
        return _("Environment Variables")

    @property
    def description(self) -> str:
        return _("Variables set in the site user's environment")

    def _collect_infos(self) -> DiagnosticsElementJSONResult:
        # Get the environment variables

        return dict(os.environ)


class MKPFindTextDiagnosticsElement(ABCDiagnosticsElementTextDump):
    @property
    def ident(self) -> str:
        return "mkp_find_all.json"

    @property
    def title(self) -> str:
        return _("Extension package files")

    @property
    def description(self) -> str:
        return _(
            "Output of `mkp find --all --json`. "
            "See the corresponding commandline help for more details."
        )

    def _collect_infos(self) -> str:
        return subprocess.check_output(["mkp", "find", "--all", "--json"], text=True)


class MKPShowTextDiagnosticsElement(ABCDiagnosticsElementTextDump):
    @property
    def ident(self) -> str:
        return "mkp_show_all.json"

    @property
    def title(self) -> str:
        return _("Extension package files")

    @property
    def description(self) -> str:
        return _(
            "Output of `mkp show-all --json`. "
            "See the corresponding commandline help for more details."
        )

    def _collect_infos(self) -> str:
        return subprocess.check_output(["mkp", "show-all", "--json"], text=True)


class MKPListTextDiagnosticsElement(ABCDiagnosticsElementTextDump):
    @property
    def ident(self) -> str:
        return "mkp_list.json"

    @property
    def title(self) -> str:
        return _("Extension package files")

    @property
    def description(self) -> str:
        return _(
            "Output of `mkp list --json`. "
            "See the corresponding commandline help for more details."
        )

    def _collect_infos(self) -> str:
        return subprocess.check_output(["mkp", "list", "--json"], text=True)


class OMDConfigDiagnosticsElement(ABCDiagnosticsElementJSONDump):
    @property
    def ident(self) -> str:
        return "omd_config"

    @property
    def title(self) -> str:
        return _("OMD Config")

    @property
    def description(self) -> str:
        return _(
            "Apache mode and TCP address and port, Core, "
            "Liveproxy daemon and livestatus TCP mode, "
            "Event daemon config, Multiste authorisation, "
            "NSCA mode, TMP filesystem mode"
        )

    def _collect_infos(self) -> DiagnosticsElementJSONResult:
        return get_omd_config()


class CheckmkOverviewDiagnosticsElement(ABCDiagnosticsElementJSONDump):
    @property
    def ident(self) -> str:
        return "checkmk_overview"

    @property
    def title(self) -> str:
        return _("Checkmk Overview of Checkmk Server")

    @property
    def description(self) -> str:
        return _(
            "Checkmk Agent, Number, version and edition of sites, Cluster host; "
            "Number of hosts, services, CMK Helper, Live Helper, "
            "Helper usage; State of daemons: Apache, Core, Crontag, "
            "DCD, Liveproxyd, MKEventd, MKNotifyd, RRDCached "
            "(Agent plugin mk_inventory needs to be installed)"
        )

    def _collect_infos(self) -> DiagnosticsElementJSONResult:
        checkmk_server_name = get_checkmk_server_name()
        if checkmk_server_name is None:
            raise DiagnosticsElementError("No Checkmk server found")

        try:
            tree = load_tree(Path(cmk.utils.paths.inventory_output_dir) / checkmk_server_name)
        except FileNotFoundError:
            raise DiagnosticsElementError(
                "No HW/SW inventory tree of '%s' found" % checkmk_server_name
            )

        if (
            node := tree.get_node(("software", "applications", "check_mk"))
        ) is None or node.is_empty():
            raise DiagnosticsElementError(
                "No HW/SW inventory node 'Software > Applications > Checkmk'"
            )
        return node.serialize()


#   ---collect exiting files------------------------------------------------


class ABCCheckmkFilesDiagnosticsElement(ABCDiagnosticsElement):
    def __init__(self, rel_checkmk_files: list[str]) -> None:
        self.rel_checkmk_files = rel_checkmk_files

    @property
    @abc.abstractmethod
    def _checkmk_files_map(self) -> CheckmkFilesMap:
        raise NotImplementedError

    def add_or_get_files(self, tmp_dump_folder: Path) -> DiagnosticsElementFilepaths:
        checkmk_files_map = self._checkmk_files_map
        unknown_files = []
        for rel_filepath in self.rel_checkmk_files:
            filepath = checkmk_files_map.get(rel_filepath)
            if filepath is None or not filepath.exists():
                unknown_files.append(rel_filepath)
                continue

            # Respect file path (2), otherwise the paths of same named files are forgotten (1).
            # We want to pack a folder hierarchy.

            filename = Path(filepath).name
            subfolder = Path(str(filepath).replace(str(cmk.utils.paths.omd_root) + "/", "")).parent

            # Create relative path in tmp tree
            tmp_folder = tmp_dump_folder.joinpath(subfolder)
            tmp_folder.mkdir(parents=True, exist_ok=True)

            tmp_filepath = shutil.copy(str(filepath), str(tmp_folder.joinpath(filename)))

            yield Path(tmp_filepath)

        if unknown_files:
            raise DiagnosticsElementError("No such files: %s" % ", ".join(unknown_files))


class CheckmkConfigFilesDiagnosticsElement(ABCCheckmkFilesDiagnosticsElement):
    @property
    def ident(self) -> str:
        # Unused because we directly pack the .mk or .conf file
        return "checkmk_config_files"

    @property
    def title(self) -> str:
        return _("Checkmk Configuration Files")

    @property
    def description(self) -> str:
        return _("Configuration files ('*.mk' or '*.conf') from etc/checkmk: %s") % ", ".join(
            self.rel_checkmk_files
        )

    @property
    def _checkmk_files_map(self) -> CheckmkFilesMap:
        return get_checkmk_config_files_map()


class CheckmkLogFilesDiagnosticsElement(ABCCheckmkFilesDiagnosticsElement):
    @property
    def ident(self) -> str:
        # Unused because we directly pack the .log or .state file
        return "checkmk_log_files"

    @property
    def title(self) -> str:
        return _("Checkmk Log Files")

    @property
    def description(self) -> str:
        return _("Log files ('*.log' or '*.state') from var/log: %s") % ", ".join(
            self.rel_checkmk_files
        )

    @property
    def _checkmk_files_map(self) -> CheckmkFilesMap:
        return get_checkmk_log_files_map()


#   ---cee dumps------------------------------------------------------------


class CheckmkCoreFilesDiagnosticsElement(ABCCheckmkFilesDiagnosticsElement):
    @property
    def ident(self) -> str:
        # Unused because we directly pack the config, state and history file
        return "checkmk_core_files"

    @property
    def title(self) -> str:
        return _("Checkmk Core Files")

    @property
    def description(self) -> str:
        return _("Core files (config, state and history) from var/check_mk/core: %s") % ", ".join(
            self.rel_checkmk_files
        )

    @property
    def _checkmk_files_map(self) -> CheckmkFilesMap:
        return get_checkmk_core_files_map()


class CheckmkLicensingFilesDiagnosticsElement(ABCCheckmkFilesDiagnosticsElement):
    @property
    def ident(self) -> str:
        # Unused because we directly pack the config, state and history file
        return "checkmk_licensing_files"

    @property
    def title(self) -> str:
        return _("Checkmk Licensing Files")

    @property
    def description(self) -> str:
        return _(
            "Licensing files (data and logs) from var/check_mk/licensing and var/log: %s"
        ) % ", ".join(self.rel_checkmk_files)

    @property
    def _checkmk_files_map(self) -> CheckmkFilesMap:
        return get_checkmk_licensing_files_map()


class PerformanceGraphsDiagnosticsElement(ABCDiagnosticsElement):
    @property
    def ident(self) -> str:
        return "performance_graphs"

    @property
    def title(self) -> str:
        return _("Performance Graphs of Checkmk Server")

    @property
    def description(self) -> str:
        return _(
            "CPU load and utilization, Number of threads, Kernel Performance, "
            "OMD, Filesystem, Apache Status, TCP Connections of the time ranges "
            "25 hours and 35 days"
        )

    def add_or_get_files(self, tmp_dump_folder: Path) -> DiagnosticsElementFilepaths:
        checkmk_server_name = get_checkmk_server_name()
        if checkmk_server_name is None:
            raise DiagnosticsElementError("No Checkmk server found")

        response = self._get_response(checkmk_server_name, get_omd_config())

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
        self, checkmk_server_name: str, omd_config: site.OMDConfig
    ) -> requests.Response:
        automation_secret = AutomationUserSecret(UserId("automation")).read()

        url = "http://{}:{}/{}/check_mk/report.py?".format(
            omd_config["CONFIG_APACHE_TCP_ADDR"],
            omd_config["CONFIG_APACHE_TCP_PORT"],
            omd_site(),
        ) + urllib.parse.urlencode(
            [
                ("_username", "automation"),
                ("_secret", automation_secret),
                ("host", checkmk_server_name),
                ("name", "host_performance_graphs"),
            ]
        )

        return requests.post(url)  # nosec B113


class CMCDumpDiagnosticsElement(ABCDiagnosticsElement):
    @property
    def ident(self) -> str:
        return "cmcdump"

    @property
    def title(self) -> str:
        return _("Config and state dumps of the CMC")

    @property
    def description(self) -> str:
        return _(
            "Configuration, status, and status history data of the CMC (Checkmk Microcore); "
            "cmcdump output of the status and config."
        )

    def add_or_get_files(self, tmp_dump_folder: Path) -> DiagnosticsElementFilepaths:
        command = [str(Path(cmk.utils.paths.omd_root).joinpath("bin/cmcdump"))]

        for dump_args in (None, "config"):
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
                console.info("%s\n", _format_error(str(e)))
                continue

            filepath = tmpdir.joinpath(f"{self.ident}{suffix}")
            with filepath.open("w") as f:
                f.write(output)

            yield filepath
