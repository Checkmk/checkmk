#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import abc
import errno
import json
import os
import platform
import shutil
import tarfile
import tempfile
import textwrap
import traceback
import urllib.parse
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

import livestatus

import cmk.utils.packaging as packaging
import cmk.utils.paths
import cmk.utils.site as site
import cmk.utils.store as store
import cmk.utils.structured_data as structured_data
import cmk.utils.tty as tty
import cmk.utils.version as cmk_version
from cmk.utils.diagnostics import (
    CheckmkFilesMap,
    DiagnosticsElementCSVResult,
    DiagnosticsElementFilepaths,
    DiagnosticsElementJSONResult,
    DiagnosticsOptionalParameters,
    get_checkmk_config_files_map,
    get_checkmk_log_files_map,
    get_local_files_csv,
    OPT_CHECKMK_CONFIG_FILES,
    OPT_CHECKMK_LOG_FILES,
    OPT_CHECKMK_OVERVIEW,
    OPT_LOCAL_FILES,
    OPT_OMD_CONFIG,
    OPT_PERFORMANCE_GRAPHS,
)
from cmk.utils.i18n import _
from cmk.utils.log import console

import cmk.base.config as config
import cmk.base.section as section

SUFFIX = ".tar.gz"


def create_diagnostics_dump(parameters: Optional[DiagnosticsOptionalParameters]) -> None:
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
    return "%s%s" % (_GAP, str(filepath.relative_to(cmk.utils.paths.omd_root)))


def _format_title(title: str) -> str:
    return "%s%s%s%s:" % (_GAP, tty.green, title, tty.normal)


def _format_description(description: str) -> str:
    return textwrap.fill(
        description,
        width=52,
        initial_indent=2 * _GAP,
        subsequent_indent=2 * _GAP,
    )


def _format_error(error):
    return "%s%s - %s" % (2 * _GAP, tty.error, error)


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

    def __init__(self, parameters: Optional[DiagnosticsOptionalParameters] = None) -> None:
        self.fixed_elements = self._get_fixed_elements()
        self.optional_elements = self._get_optional_elements(parameters)
        self.elements = self.fixed_elements + self.optional_elements

        dump_folder = cmk.utils.paths.diagnostics_dir
        self.dump_folder = dump_folder
        self.tarfile_path = dump_folder.joinpath(str(uuid.uuid4())).with_suffix(SUFFIX)
        self.tarfile_created = False

    def _get_fixed_elements(self) -> "List[ABCDiagnosticsElement]":
        return [
            GeneralDiagnosticsElement(),
            PerfDataDiagnosticsElement(),
            HWDiagnosticsElement(),
            EnvironmentDiagnosticsElement(),
            FilesSizeCSVDiagnosticsElement(),
        ]

    def _get_optional_elements(
            self,
            parameters: Optional[DiagnosticsOptionalParameters]) -> "List[ABCDiagnosticsElement]":
        if parameters is None:
            return []

        optional_elements: List[ABCDiagnosticsElement] = []
        if parameters.get(OPT_LOCAL_FILES):
            optional_elements.append(LocalFilesJSONDiagnosticsElement())
            optional_elements.append(LocalFilesCSVDiagnosticsElement())

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

        if not cmk_version.is_raw_edition() and parameters.get(OPT_PERFORMANCE_GRAPHS):
            optional_elements.append(PerformanceGraphsDiagnosticsElement())

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
                dir=self.dump_folder) as tmp_dump_folder:
            for filepath in self._get_filepaths(Path(tmp_dump_folder)):
                rel_path = str(filepath).replace(str(tmp_dump_folder), "")
                tar.add(str(filepath), arcname=rel_path)
                self.tarfile_created = True

    def _get_filepaths(self, tmp_dump_folder: Path) -> List[Path]:
        section.section_step("Collect diagnostics information", verbose=False)

        collectors = Collectors()

        filepaths = []
        for element in self.elements:
            console.info("%s\n", _format_title(element.title))
            console.info("%s\n", _format_description(element.description))

            try:
                for filepath in element.add_or_get_files(tmp_dump_folder, collectors):
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
        )[:-self._keep_num_dumps]

        section.section_step("Cleanup dump folder",
                             add_info="keep last %d dumps" % self._keep_num_dumps)
        for _mtime, filepath in dumps:
            console.verbose("%s\n", _format_filepath(filepath))
            self._remove_file(filepath)

    def _remove_file(self, filepath: Path) -> None:
        try:
            filepath.unlink()
        except OSError as e:
            if e.errno != errno.ENOENT:
                raise


# .
#   .--collectors----------------------------------------------------------.
#   |                        _ _           _                               |
#   |               ___ ___ | | | ___  ___| |_ ___  _ __ ___               |
#   |              / __/ _ \| | |/ _ \/ __| __/ _ \| '__/ __|              |
#   |             | (_| (_) | | |  __/ (__| || (_) | |  \__ \              |
#   |              \___\___/|_|_|\___|\___|\__\___/|_|  |___/              |
#   |                                                                      |
#   '----------------------------------------------------------------------


class Collectors:
    def __init__(self):
        self._omd_config_collector = OMDConfigCollector()
        self._checkmk_server_name_collector = CheckmkServerNameCollector()

    def get_omd_config(self) -> site.OMDConfig:
        return self._omd_config_collector.get_infos()

    def get_checkmk_server_name(self) -> Optional[str]:
        return self._checkmk_server_name_collector.get_infos()


class ABCCollector(metaclass=abc.ABCMeta):
    """Collects information which are used by several elements"""
    def __init__(self):
        self._has_collected = False
        self._infos = None

    def get_infos(self) -> Any:
        if not self._has_collected:
            self._infos = self._collect_infos()
            self._has_collected = True
        return self._infos

    @abc.abstractmethod
    def _collect_infos(self) -> Any:
        raise NotImplementedError()


class OMDConfigCollector(ABCCollector):
    def _collect_infos(self) -> site.OMDConfig:
        return site.get_omd_config()


class CheckmkServerNameCollector(ABCCollector):
    def _collect_infos(self) -> Optional[str]:
        query = (
            "GET services\nColumns: host_name\nFilter: service_description ~ OMD %s performance\n" %
            cmk_version.omd_site())
        result = livestatus.LocalConnection().query(query)
        try:
            return result[0][0]
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


class ABCDiagnosticsElement(metaclass=abc.ABCMeta):
    @abc.abstractproperty
    def ident(self) -> str:
        raise NotImplementedError()

    @abc.abstractproperty
    def title(self) -> str:
        raise NotImplementedError()

    @abc.abstractproperty
    def description(self) -> str:
        raise NotImplementedError()

    @abc.abstractmethod
    def add_or_get_files(self, tmp_dump_folder: Path,
                         collectors: Collectors) -> DiagnosticsElementFilepaths:
        # Please note the case if there are more than one filepath results. A Python generator
        # is executed until the first raise. Then it will be stopped and all generator states
        # are gone. Correctly calculated filepaths till then are yielded.
        # (Example: CheckmkConfigFilesDiagnosticsElement: collect errors and raise at the end)
        raise NotImplementedError()


class ABCDiagnosticsElementJSONDump(ABCDiagnosticsElement):
    def add_or_get_files(self, tmp_dump_folder: Path,
                         collectors: Collectors) -> DiagnosticsElementFilepaths:
        infos = self._collect_infos(collectors)
        if not infos:
            raise DiagnosticsElementError("No information")

        filepath = tmp_dump_folder.joinpath(self.ident).with_suffix(".json")
        store.save_text_to_file(filepath, json.dumps(infos, sort_keys=True, indent=4))
        yield filepath

    @abc.abstractmethod
    def _collect_infos(self, collectors: Collectors) -> DiagnosticsElementJSONResult:
        raise NotImplementedError()


class ABCDiagnosticsElementCSVDump(ABCDiagnosticsElement):
    def add_or_get_files(self, tmp_dump_folder: Path,
                         collectors: Collectors) -> DiagnosticsElementFilepaths:
        infos = self._collect_infos(collectors)
        if not infos:
            raise DiagnosticsElementError("No information")

        filepath = tmp_dump_folder.joinpath(self.ident).with_suffix(".csv")
        store.save_text_to_file(filepath, infos)
        yield filepath

    @abc.abstractmethod
    def _collect_infos(self, collectors: Collectors) -> DiagnosticsElementCSVResult:
        raise NotImplementedError()


#   ---csv dumps-----------------------------------------------------------


class LocalFilesCSVDiagnosticsElement(ABCDiagnosticsElementCSVDump):
    @property
    def ident(self) -> str:
        return "local_files"

    @property
    def title(self) -> str:
        return _("Local Files")

    @property
    def description(self) -> str:
        return _("List of installed, unpacked, optional files below $OMD_ROOT/local. "
                 "This also includes information about installed MKPs.")

    def _collect_infos(self, collectors: Collectors) -> DiagnosticsElementCSVResult:
        package_infos = packaging.get_all_package_infos()
        return get_local_files_csv(package_infos)


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

    def _collect_infos(self, collectors: Collectors) -> DiagnosticsElementCSVResult:
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
        return _("OS, Checkmk version and edition, Time, Core, "
                 "Python version and paths, Architecture")

    def _collect_infos(self, collectors: Collectors) -> DiagnosticsElementJSONResult:
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

    def _collect_infos(self, collectors: Collectors) -> DiagnosticsElementJSONResult:
        # Get the runtime performance data from livestatus
        query = "GET status\nColumnHeaders: on"
        result = livestatus.LocalConnection().query(query)
        performance_data = {
            key: result[1][i]
            for i in range(0, len(result[0]))
            if (key := result[0][i]) not in ["license_usage_history"]
        }

        if cmk_version.get_general_version_infos()["core"] == "cmc":
            # CEE: Get information about the helper processes from config
            performance_data.update({
                "cmc_check_helpers": config.cmc_check_helpers,
                "cmc_cmk_helpers": config.cmc_cmk_helpers,
                "cmc_fetcher_helpers": config.cmc_fetcher_helpers,
                "cmc_checker_helpers": config.cmc_checker_helpers,
                "cmc_real_time_helpers": config.cmc_real_time_helpers,
            })

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

    def _collect_infos(self, collectors: Collectors) -> DiagnosticsElementJSONResult:
        # Get the information from the proc files

        hw_info: DiagnosticsElementJSONResult = {}

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

    def _get_proc_content(self, filepath: Path) -> List[str]:
        with open(filepath) as f:
            return f.read().splitlines()

    def _meminfo_proc_parser(self, content: List[str]) -> Dict[str, str]:
        info: Dict[str, str] = {}

        for line in content:
            if line == "":
                continue

            key, value = [w.strip() for w in line.split(":", 1)]
            info[key.replace(" ", "_")] = value

        return info

    def _cpuinfo_proc_parser(self, content: List[str]) -> Dict[str, str]:
        cpu_info: Dict[str, Any] = {}
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

        # Parse content
        for line in content:
            if line == "":
                continue

            key, value = [w.strip() for w in line.split(":", 1)]
            key = key.replace(" ", "_")

            if key not in _KEYS_TO_IGNORE:
                cpu_info[key] = value
            if key == "processor":
                num_processors += 1

        cpu_info["num_processors"] = str(num_processors)

        return cpu_info

    def _load_avg_proc_parser(self, content: List[str]) -> Dict[str, str]:
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

    def _collect_infos(self, collectors: Collectors) -> DiagnosticsElementJSONResult:
        # Get the environment variables

        return dict(os.environ)


class LocalFilesJSONDiagnosticsElement(ABCDiagnosticsElementJSONDump):
    @property
    def ident(self) -> str:
        return "local_files"

    @property
    def title(self) -> str:
        return _("Local Files")

    @property
    def description(self) -> str:
        return _("List of installed, unpacked, optional files below $OMD_ROOT/local. "
                 "This also includes information about installed MKPs.")

    def _collect_infos(self, collectors: Collectors) -> DiagnosticsElementJSONResult:
        return packaging.get_all_package_infos()


class OMDConfigDiagnosticsElement(ABCDiagnosticsElementJSONDump):
    @property
    def ident(self) -> str:
        return "omd_config"

    @property
    def title(self) -> str:
        return _("OMD Config")

    @property
    def description(self) -> str:
        return _("Apache mode and TCP address and port, Core, "
                 "Liveproxy daemon and livestatus TCP mode, "
                 "Event daemon config, Multiste authorisation, "
                 "NSCA mode, TMP filesystem mode")

    def _collect_infos(self, collectors: Collectors) -> DiagnosticsElementJSONResult:
        return collectors.get_omd_config()


class CheckmkOverviewDiagnosticsElement(ABCDiagnosticsElementJSONDump):
    @property
    def ident(self) -> str:
        return "checkmk_overview"

    @property
    def title(self) -> str:
        return _("Checkmk Overview of Checkmk Server")

    @property
    def description(self) -> str:
        return _("Checkmk Agent, Number, version and edition of sites, Cluster host; "
                 "Number of hosts, services, CMK Helper, Live Helper, "
                 "Helper usage; State of daemons: Apache, Core, Crontag, "
                 "DCD, Liveproxyd, MKEventd, MKNotifyd, RRDCached "
                 "(Agent plugin mk_inventory needs to be installed)")

    def _collect_infos(self, collectors: Collectors) -> DiagnosticsElementJSONResult:
        checkmk_server_name = collectors.get_checkmk_server_name()
        if checkmk_server_name is None:
            raise DiagnosticsElementError("No Checkmk server found")

        filepath = Path(cmk.utils.paths.inventory_output_dir + "/" + checkmk_server_name)
        if not filepath.exists():
            raise DiagnosticsElementError("No HW/SW inventory tree of '%s' found" %
                                          checkmk_server_name)

        infos = {}
        tree = structured_data.StructuredDataTree().load_from(filepath)
        attrs = tree.get_sub_attributes(["software", "applications", "check_mk"])
        if attrs:
            infos.update(attrs.get_raw_tree())

        node = tree.get_sub_container(["software", "applications", "check_mk"])
        if node:
            infos.update(node.get_raw_tree())

        if not infos:
            raise DiagnosticsElementError(
                "No HW/SW inventory node 'Software > Applications > Checkmk'")
        return infos


#   ---collect exiting files------------------------------------------------


class ABCCheckmkFilesDiagnosticsElement(ABCDiagnosticsElement):
    def __init__(self, rel_checkmk_files: List[str]) -> None:
        self.rel_checkmk_files = rel_checkmk_files

    @abc.abstractproperty
    def _checkmk_files_map(self) -> CheckmkFilesMap:
        raise NotImplementedError

    def add_or_get_files(self, tmp_dump_folder: Path,
                         collectors: Collectors) -> DiagnosticsElementFilepaths:
        checkmk_files_map = self._checkmk_files_map
        unknown_files = []
        for rel_filepath in self.rel_checkmk_files:
            filepath = checkmk_files_map.get(rel_filepath)
            if filepath is None or not filepath.exists():
                unknown_files.append(rel_filepath)
                continue

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
            self.rel_checkmk_files)

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
            self.rel_checkmk_files)

    @property
    def _checkmk_files_map(self) -> CheckmkFilesMap:
        return get_checkmk_log_files_map()


#   ---cee dumps------------------------------------------------------------


class PerformanceGraphsDiagnosticsElement(ABCDiagnosticsElement):
    @property
    def ident(self) -> str:
        return "performance_graphs"

    @property
    def title(self) -> str:
        return _("Performance Graphs of Checkmk Server")

    @property
    def description(self) -> str:
        return _("CPU load and utilization, Number of threads, Kernel Performance, "
                 "OMD, Filesystem, Apache Status, TCP Connections of the time ranges "
                 "25 hours and 35 days")

    def add_or_get_files(self, tmp_dump_folder: Path,
                         collectors: Collectors) -> DiagnosticsElementFilepaths:
        checkmk_server_name = collectors.get_checkmk_server_name()
        if checkmk_server_name is None:
            raise DiagnosticsElementError("No Checkmk server found")

        response = self._get_response(checkmk_server_name, collectors)

        if response.status_code != 200:
            raise DiagnosticsElementError("HTTP error - %d (%s)" %
                                          (response.status_code, response.text))

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

    def _get_response(self, checkmk_server_name: str, collectors: Collectors) -> requests.Response:
        automation_secret = self._get_automation_secret()

        omd_config = collectors.get_omd_config()
        url = "http://%s:%s/%s/check_mk/report.py?" % (
            omd_config["CONFIG_APACHE_TCP_ADDR"],
            omd_config["CONFIG_APACHE_TCP_PORT"],
            cmk_version.omd_site(),
        ) + urllib.parse.urlencode([
            ("_username", "automation"),
            ("_secret", automation_secret),
            ("host", checkmk_server_name),
            ("name", "host_performance_graphs"),
        ])

        return requests.post(url)

    def _get_automation_secret(self) -> str:
        automation_secret_filepath = Path(
            cmk.utils.paths.var_dir).joinpath("web/automation/automation.secret")
        with automation_secret_filepath.open("r", encoding="utf-8") as f:
            return f.read().strip()
