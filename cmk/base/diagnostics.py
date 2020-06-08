#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import errno
import abc
from typing import List, Optional, Dict, Any
import uuid
import tarfile
import json
from pathlib import Path
import tempfile
import platform
import urllib.parse
import requests

import livestatus

from cmk.utils.i18n import _
import cmk.utils.paths
import cmk.utils.version as cmk_version
import cmk.utils.store as store
from cmk.utils.log import console
import cmk.utils.packaging as packaging
import cmk.utils.site as site

from cmk.utils.diagnostics import (
    OPT_LOCAL_FILES,
    OPT_OMD_CONFIG,
    OPT_PERFORMANCE_GRAPHS,
    DiagnosticsOptionalParameters,
)

import cmk.base.obsolete_output as out

SUFFIX = ".tar.gz"


def create_diagnostics_dump(parameters):
    # type: (Optional[DiagnosticsOptionalParameters]) -> None
    dump = DiagnosticsDump(parameters)
    dump.create()
    out.output("Created diagnostics dump:\n")
    out.output("  '%s'\n" % _get_short_filepath(dump.tarfile_path))


def _get_short_filepath(filepath):
    # type: (Path) -> Path
    return filepath.relative_to(cmk.utils.paths.omd_root)


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

    def __init__(self, parameters=None):
        # type: (Optional[DiagnosticsOptionalParameters]) -> None
        self.fixed_elements = self._get_fixed_elements()
        self.optional_elements = self._get_optional_elements(parameters)
        self.elements = self.fixed_elements + self.optional_elements

        dump_folder = cmk.utils.paths.diagnostics_dir
        self.dump_folder = dump_folder
        self.tarfile_path = dump_folder.joinpath(str(uuid.uuid4())).with_suffix(SUFFIX)

    def _get_fixed_elements(self):
        # type: () -> List[ABCDiagnosticsElement]
        return [
            GeneralDiagnosticsElement(),
        ]

    def _get_optional_elements(self, parameters):
        # type: (Optional[DiagnosticsOptionalParameters]) -> List[ABCDiagnosticsElement]
        if parameters is None:
            return []

        optional_elements = []  # type: List[ABCDiagnosticsElement]
        if parameters.get(OPT_LOCAL_FILES):
            optional_elements.append(LocalFilesDiagnosticsElement())

        if parameters.get(OPT_OMD_CONFIG):
            optional_elements.append(OMDConfigDiagnosticsElement())

        if not cmk_version.is_raw_edition() and parameters.get(OPT_PERFORMANCE_GRAPHS):
            optional_elements.append(PerformanceGraphsDiagnosticsElement())

        return optional_elements

    def create(self):
        # type: () -> None
        self._create_dump_folder()
        self._create_tarfile()
        self._cleanup_dump_folder()

    def _create_dump_folder(self):
        # type: () -> None
        console.verbose("Create dump folder:\n")
        self.dump_folder.mkdir(parents=True, exist_ok=True)
        console.verbose("  '%s'\n" % _get_short_filepath(self.dump_folder))

    def _create_tarfile(self):
        # type: () -> None
        with tarfile.open(name=self.tarfile_path, mode='w:gz') as tar,\
             tempfile.TemporaryDirectory(dir=self.dump_folder) as tmp_dump_folder:
            for filepath in self._get_filepaths(Path(tmp_dump_folder)):
                tar.add(str(filepath), arcname=filepath.name)

    def _get_filepaths(self, tmp_dump_folder):
        # type: (Path) -> List[Path]
        out.output("Collect diagnostics information:\n")
        filepaths = []
        for element in self.elements:
            filepath = element.add_or_get_file(tmp_dump_folder)
            if filepath is None:
                console.verbose("  %s: %s\n" % (element.title, element.error))
                continue
            out.output("  %s: %s\n" % (element.title, element.description))
            filepaths.append(filepath)
        return filepaths

    def _cleanup_dump_folder(self):
        # type: () -> None
        dumps = sorted(
            [(dump.stat().st_mtime, dump) for dump in self.dump_folder.glob("*%s" % SUFFIX)],
            key=lambda t: t[0])[:-self._keep_num_dumps]

        console.verbose("Cleanup dump folder (remove old dumps, keep the last %s dumps):\n" %
                        self._keep_num_dumps)
        for _mtime, filepath in dumps:
            console.verbose("  '%s'\n" % _get_short_filepath(filepath))
            self._remove_file(filepath)

    def _remove_file(self, filepath):
        # type: (Path) -> None
        try:
            filepath.unlink()
        except OSError as e:
            if e.errno != errno.ENOENT:
                raise


#.
#   .--elements------------------------------------------------------------.
#   |                   _                           _                      |
#   |               ___| | ___ _ __ ___   ___ _ __ | |_ ___                |
#   |              / _ \ |/ _ \ '_ ` _ \ / _ \ '_ \| __/ __|               |
#   |             |  __/ |  __/ | | | | |  __/ | | | |_\__ \               |
#   |              \___|_|\___|_| |_| |_|\___|_| |_|\__|___/               |
#   |                                                                      |
#   '----------------------------------------------------------------------'


class ABCDiagnosticsElement(metaclass=abc.ABCMeta):
    def __init__(self):
        # Set an informative error message if an error occurs during
        # collecting information in ABCDiagnosticsElement.add_or_get_file.
        # In this case the filepath should be 'None' and this message is
        # shown on CL output.
        self.error = ""

    @abc.abstractproperty
    def ident(self):
        # type: () -> str
        raise NotImplementedError()

    @abc.abstractproperty
    def title(self):
        # type: () -> str
        raise NotImplementedError()

    @abc.abstractproperty
    def description(self):
        # type: () -> str
        raise NotImplementedError()

    @abc.abstractmethod
    def add_or_get_file(self, tmp_dump_folder):
        # type: (Path) -> Optional[Path]
        raise NotImplementedError()


class ABCDiagnosticsElementJSONDump(ABCDiagnosticsElement):
    def add_or_get_file(self, tmp_dump_folder):
        # type: (Path) -> Optional[Path]
        filepath = tmp_dump_folder.joinpath(self.ident).with_suffix(".json")
        store.save_text_to_file(filepath, json.dumps(self._collect_infos()))
        return filepath

    @abc.abstractmethod
    def _collect_infos(self):
        # type: () -> Dict[str, Any]
        raise NotImplementedError()


#   ---json dumps-----------------------------------------------------------


class GeneralDiagnosticsElement(ABCDiagnosticsElementJSONDump):
    @property
    def ident(self):
        # type: () -> str
        return "general"

    @property
    def title(self):
        # type: () -> str
        return _("General")

    @property
    def description(self):
        # type: () -> str
        return _("OS, Checkmk version and edition, Time, Core, "
                 "Python version and paths, Architecture")

    def _collect_infos(self):
        # type: () -> Dict[str, Any]
        version_infos = cmk_version.get_general_version_infos()
        version_infos["arch"] = platform.machine()
        return version_infos


class LocalFilesDiagnosticsElement(ABCDiagnosticsElementJSONDump):
    @property
    def ident(self):
        # type: () -> str
        return "local_files"

    @property
    def title(self):
        # type: () -> str
        return _("Local Files")

    @property
    def description(self):
        # type: () -> str
        return _("List of installed, unpacked, optional files below $OMD_ROOT/local. "
                 "This also includes information about installed MKPs.")

    def _collect_infos(self):
        # type: () -> Dict[str, Any]
        return packaging.get_all_package_infos()


class OMDConfigDiagnosticsElement(ABCDiagnosticsElementJSONDump):
    @property
    def ident(self):
        # type: () -> str
        return "omd_config"

    @property
    def title(self):
        # type: () -> str
        return _("OMD Config")

    @property
    def description(self):
        # type: () -> str
        return _("Apache mode and TCP address and port, Core, "
                 "Liveproxy daemon and livestatus TCP mode, "
                 "Event daemon config, Multiste authorisation, "
                 "NSCA mode, TMP filesystem mode")

    def _collect_infos(self):
        # type: () -> site.OMDConfig
        return site.get_omd_config()


#   ---other dumps----------------------------------------------------------


class PerformanceGraphsDiagnosticsElement(ABCDiagnosticsElement):
    @property
    def ident(self):
        # type: () -> str
        return "performance_graphs"

    @property
    def title(self):
        # type: () -> str
        return _("Performance Graphs of Checkmk Server")

    @property
    def description(self):
        # type: () -> str
        return _("CPU load and utilization, Number of threads, Kernel Performance, "
                 "OMD, Filesystem, Apache Status, TCP Connections of the time ranges "
                 "25 hours and 35 days")

    def add_or_get_file(self, tmp_dump_folder):
        # type: (Path) -> Optional[Path]
        checkmk_server_name = self._get_checkmk_server_name()
        if checkmk_server_name is None:
            self.error = "No Checkmk server found"
            return None

        response = self._get_response(checkmk_server_name)

        if response.status_code != 200:
            self.error = "HTTP error - %d (%s)" % (response.status_code, response.text)
            return None

        if "<html>" in response.text.lower():
            self.error = "Login failed - Invalid automation user or secret"
            return None

        # Verify if it's a PDF document: The header must begin with
        # "%PDF-" (hex: "25 50 44 46 2d")
        if response.content[:5].hex() != "255044462d":
            self.error = "Verification of PDF document header failed"
            return None

        filepath = tmp_dump_folder.joinpath(self.ident).with_suffix(".pdf")
        with filepath.open("wb") as f:
            f.write(response.content)

        return filepath

    def _get_checkmk_server_name(self):
        # type: () -> Optional[str]
        query = "GET hosts\nColumns: host_name\nFilter: host_labels = 'cmk/check_mk_server' 'yes'\n"
        result = livestatus.LocalConnection().query(query)
        try:
            return result[0][0]
        except IndexError:
            return None

    def _get_response(self, checkmk_server_name):
        # type: (str) -> requests.Response
        automation_secret = self._get_automation_secret()

        omd_config = site.get_omd_config()
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

        return requests.post(url, verify=False)

    def _get_automation_secret(self):
        # type: () -> str
        automation_secret_filepath = Path(
            cmk.utils.paths.var_dir).joinpath("web/automation/automation.secret")
        with automation_secret_filepath.open("r", encoding="utf-8") as f:
            return f.read().strip()
