#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import abc
import json
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
from collections.abc import Iterator, Mapping
from datetime import datetime
from functools import cache
from pathlib import Path
from typing import Any

import requests

import livestatus

import cmk.ccc.version as cmk_version
from cmk.ccc import site, store, tty
from cmk.ccc.hostaddress import HostName
from cmk.ccc.i18n import _
from cmk.ccc.site import omd_site

import cmk.utils.paths
from cmk.utils.diagnostics import (
    CheckmkFileEncryption,
    CheckmkFileInfoByRelFilePathMap,
    CheckmkFilesMap,
    DiagnosticsElementCSVResult,
    DiagnosticsElementFilepaths,
    DiagnosticsElementJSONResult,
    DiagnosticsOptionalParameters,
    get_checkmk_config_files_map,
    get_checkmk_core_files_map,
    get_checkmk_licensing_files_map,
    get_checkmk_log_files_map,
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
from cmk.utils.structured_data import (
    InventoryStore,
    SDNodeName,
    SDRawTree,
    serialize_tree,
)

from cmk.base.config import LoadedConfigFragment

if cmk_version.edition(cmk.utils.paths.omd_root) in [
    cmk_version.Edition.CEE,
    cmk_version.Edition.CME,
    cmk_version.Edition.CCE,
    cmk_version.Edition.CSE,
]:
    from cmk.base.cee.diagnostics import (  # type: ignore[import-not-found, import-untyped, unused-ignore]
        cmc_specific_attrs,  # type: ignore[import,unused-ignore]
    )
else:

    def cmc_specific_attrs(loaded_config: LoadedConfigFragment) -> Mapping[str, int]:
        return {}


SUFFIX = ".tar.gz"


def create_diagnostics_dump(
    loaded_config: LoadedConfigFragment, parameters: DiagnosticsOptionalParameters | None
) -> None:
    dump = DiagnosticsDump(loaded_config, parameters)
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

    _keep_num_dumps = 10

    def __init__(
        self,
        loaded_config: LoadedConfigFragment,
        parameters: DiagnosticsOptionalParameters | None = None,
    ) -> None:
        self.fixed_elements = self._get_fixed_elements(loaded_config)
        self.optional_elements = self._get_optional_elements(parameters)
        self.elements = self.fixed_elements + self.optional_elements

        dump_folder = cmk.utils.paths.diagnostics_dir
        self.dump_folder = dump_folder
        _file_name = "sddump_%s" % str(uuid.uuid4())
        self.tarfile_path = dump_folder.joinpath(_file_name).with_suffix(SUFFIX)
        self.tarfile_created = False

    def _get_fixed_elements(
        self, loaded_config: LoadedConfigFragment
    ) -> list[ABCDiagnosticsElement]:
        return [
            GeneralDiagnosticsElement(),
            PerfDataDiagnosticsElement(loaded_config),
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
            optional_elements.append(
                CheckmkOverviewDiagnosticsElement(
                    InventoryStore(cmk.utils.paths.omd_root),
                    parameters.get(OPT_CHECKMK_OVERVIEW, ""),
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

        # CEE options
        if cmk_version.edition(cmk.utils.paths.omd_root) is not cmk_version.Edition.CRE:
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
    @property
    def ident(self) -> str:
        return "dpkg_packages"

    @property
    def title(self) -> str:
        return _("Dpkg packages information")

    @property
    def description(self) -> str:
        return _("Output of `dpkg -l`. See the corresponding commandline help for more details.")

    def _collect_infos(self) -> DiagnosticsElementCSVResult:
        if not (dpkg_binary := shutil.which("dpkg")):
            return ""

        dpkg_output = subprocess.check_output([dpkg_binary, "-l"], text=True)
        return "\n".join(
            [";".join(l.split(maxsplit=4)) for l in dpkg_output.split("\n") if len(l.split()) > 4]
        )


class RpmCSVDiagnosticsElement(ABCDiagnosticsElementCSVDump):
    @property
    def ident(self) -> str:
        return "rpm_packages"

    @property
    def title(self) -> str:
        return _("Rpm packages information")

    @property
    def description(self) -> str:
        return _("Output of `rpm -qa`. See the corresponding commandline help for more details.")

    def _collect_infos(self) -> DiagnosticsElementCSVResult:
        if not (rpm_binary := shutil.which("rpm")):
            return ""

        try:
            output = subprocess.check_output(
                [rpm_binary, "-qa", "--queryformat", r"%{NAME};%{VERSION};%{RELEASE};%{ARCH}\n"],
                text=True,
                stderr=subprocess.STDOUT,
            )

        except subprocess.CalledProcessError:
            return ""

        return "\n".join(sorted(output.split("\n")))


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
    def __init__(self, load_config: LoadedConfigFragment) -> None:
        self._loaded_config = load_config

    @property
    def ident(self) -> str:
        return "perfdata"

    @property
    def title(self) -> str:
        return _("Performance data")

    @property
    def description(self) -> str:
        return _("Performance data related to sizing, e.g. number of helpers, hosts, services")

    def _collect_infos(self) -> DiagnosticsElementJSONResult:
        # Get the runtime performance data from livestatus
        query = "GET status\nColumnHeaders: on"
        result = livestatus.LocalConnection().query(query)
        performance_data = {
            key: result[1][i]
            for i in range(0, len(result[0]))
            if (key := result[0][i]) not in ["license_usage_history"]
        }

        performance_data.update(cmc_specific_attrs(self._loaded_config))

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
    @property
    def ident(self) -> str:
        return "vendorinfo"

    @property
    def title(self) -> str:
        return _("Vendor Information")

    @property
    def description(self) -> str:
        return _("HW Vendor information of the Checkmk Server")

    def _collect_infos(self) -> DiagnosticsElementJSONResult:
        return collect_infos_vendor(Path("/sys/class/dmi/id"))


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


class PipFreezeDiagnosticsElement(ABCDiagnosticsElementJSONDump):
    @property
    def ident(self) -> str:
        return "pip_freeze"

    @property
    def title(self) -> str:
        return _("pip freeze output")

    @property
    def description(self) -> str:
        return _("The installed Python modules and their versions")

    def _collect_infos(self) -> DiagnosticsElementJSONResult:
        # Execute pip freeze and convert to JSON

        lines = subprocess.check_output(["pip3", "freeze", "--all"], text=True).split("\n")
        return {l.split("==")[0]: l.split("==")[1] for l in lines if "==" in l}


class MKPFindTextDiagnosticsElement(ABCDiagnosticsElementJSONDump):
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

    def _collect_infos(self) -> DiagnosticsElementJSONResult:
        try:
            return json.loads(
                subprocess.check_output(["mkp", "find", "--all", "--json"], text=True)
            )
        except subprocess.CalledProcessError as e:
            console.info(f"{_format_error(str(e.stderr))}\n")
            return {}


class MKPShowTextDiagnosticsElement(ABCDiagnosticsElementJSONDump):
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

    def _collect_infos(self) -> DiagnosticsElementJSONResult:
        try:
            return json.loads(subprocess.check_output(["mkp", "show-all", "--json"], text=True))
        except subprocess.CalledProcessError as e:
            console.info(f"{_format_error(str(e.stderr))}\n")
            return {}


class MKPListTextDiagnosticsElement(ABCDiagnosticsElementJSONDump):
    @property
    def ident(self) -> str:
        return "mkp_list.json"

    @property
    def title(self) -> str:
        return _("Extension package files")

    @property
    def description(self) -> str:
        return _(
            "Output of `mkp list --json`. See the corresponding commandline help for more details."
        )

    def _collect_infos(self) -> DiagnosticsElementJSONResult:
        try:
            return json.loads(subprocess.check_output(["mkp", "list", "--json"], text=True))
        except subprocess.CalledProcessError as e:
            console.info(f"{_format_error(str(e.stderr))}\n")
            return {}


class SELinuxJSONDiagnosticsElement(ABCDiagnosticsElementJSONDump):
    @property
    def ident(self) -> str:
        return "selinux"

    @property
    def title(self) -> str:
        return _("SELinux information")

    @property
    def description(self) -> str:
        return _("Output of `sestatus`. See the corresponding commandline help for more details.")

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
    @property
    def ident(self) -> str:
        return "appliance"

    @property
    def title(self) -> str:
        return _("Checkmk Appliance information")

    @property
    def description(self) -> str:
        return _("Information about the Appliance hardware and firmware version.")

    def _collect_infos(self) -> DiagnosticsElementJSONResult:
        cma_infos: dict[str, str | dict[str, str]] = {}

        if hw_content := _try_to_read("/etc/cma/hw"):
            cma_infos["hw"] = dict([l.replace("'", "").split("=") for l in hw_content if "=" in l])

        if fw_content := _try_to_read("/ro/usr/share/cma/version"):
            cma_infos["fw"] = fw_content[0]

        return cma_infos


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
    def __init__(self, inventory_store: InventoryStore, checkmk_server_host: str) -> None:
        self.inventory_store = inventory_store
        self.checkmk_server_host = checkmk_server_host

    @property
    def ident(self) -> str:
        return "checkmk_overview"

    @property
    def title(self) -> str:
        return _("Checkmk Overview of Checkmk Server")

    @property
    def description(self) -> str:
        return _(
            "Checkmk Agent, Number, version and edition of sites, cluster host; "
            "number of hosts, services, CMK Helper, Live Helper, "
            "Helper usage; state of daemons: Apache, Core, Crontab, "
            "DCD, Liveproxyd, MKEventd, MKNotifyd, RRDCached "
            "(Agent plug-in mk_inventory needs to be installed)"
        )

    def _collect_infos(self) -> SDRawTree:
        checkmk_server_host = verify_checkmk_server_host(self.checkmk_server_host)
        try:
            tree = self.inventory_store.load_inventory_tree(host_name=checkmk_server_host)
        except FileNotFoundError:
            raise DiagnosticsElementError(
                "No HW/SW Inventory tree of '%s' found" % checkmk_server_host
            )

        if not (
            node := tree.get_tree(
                (
                    SDNodeName("software"),
                    SDNodeName("applications"),
                    SDNodeName("check_mk"),
                )
            )
        ):
            raise DiagnosticsElementError(
                "No HW/SW Inventory node 'Software > Applications > Checkmk'"
            )
        return serialize_tree(node)


#   ---collect exiting files------------------------------------------------


class ABCCheckmkFilesDiagnosticsElement(ABCDiagnosticsElement):
    def __init__(self, rel_checkmk_files: list[str]) -> None:
        self.rel_checkmk_files = rel_checkmk_files

    @property
    @abc.abstractmethod
    def _checkmk_files_map(self) -> CheckmkFilesMap:
        raise NotImplementedError

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
            "Licensing files (data, config and logs) from var/check_mk/licensing, etc/check_mk/multisite.d and var/log: %s"
        ) % ", ".join(self.rel_checkmk_files)

    @property
    def _checkmk_files_map(self) -> CheckmkFilesMap:
        return get_checkmk_licensing_files_map()


class PerformanceGraphsDiagnosticsElement(ABCDiagnosticsElement):
    def __init__(self, checkmk_server_host: str) -> None:
        self.checkmk_server_host = checkmk_server_host

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
    @property
    def ident(self) -> str:
        return "bi_runtime_data"

    @property
    def title(self) -> str:
        return _("Business Intelligence runtime data")

    @property
    def description(self) -> str:
        return _(
            "Cached data from Business Intelligence. "
            "contains states, downtimes, acknowledgements and service periods "
            "for all hosts/services included in a BI aggregation."
        )

    def add_or_get_files(self, tmp_dump_folder: Path) -> DiagnosticsElementFilepaths:
        tmpdir = tmp_dump_folder.joinpath("tmp/check_mk/bi_cache")
        tmpdir.mkdir(parents=True, exist_ok=True)

        shutil.copytree(cmk.utils.paths.tmp_dir.joinpath("bi_cache"), tmpdir, dirs_exist_ok=True)
        yield tmpdir


class CrashDumpsDiagnosticsElement(ABCDiagnosticsElement):
    @property
    def ident(self) -> str:
        return "crashdumps"

    @property
    def title(self) -> str:
        return _("The latest crash dumps of each type")

    @property
    def description(self) -> str:
        return _("Returns the latest crash dumps of each type as found in var/checkmk/crashes")

    def add_or_get_files(self, tmp_dump_folder: Path) -> DiagnosticsElementFilepaths:
        for category in cmk.utils.paths.crash_dir.glob("*"):
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
    @property
    def ident(self) -> str:
        return "cmcdump"

    @property
    def title(self) -> str:
        return _("Config and state dumps of the CMC")

    @property
    def description(self) -> str:
        return _(
            "Configuration, status, and status history data of the CMC (Checkmk Micro Core); "
            "cmcdump output of the status and config."
        )

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
