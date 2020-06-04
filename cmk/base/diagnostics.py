#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import errno
import abc
from typing import List, Optional
import uuid
import tarfile
import json
from pathlib import Path
import tempfile

import cmk.utils.paths
import cmk.utils.version as cmk_version
import cmk.utils.store as store
from cmk.utils.log import console

import cmk.base.obsolete_output as out

SUFFIX = ".tar.gz"


def create_diagnostics_dump():
    # type: () -> None
    dump = DiagnosticsDump()
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

    def __init__(self):
        # type: () -> None
        self.fixed_elements = self._get_fixed_elements()
        self.optional_elements = self._get_optional_elements()
        self.elements = self.fixed_elements + self.optional_elements

        dump_folder = cmk.utils.paths.diagnostics_dir
        self.dump_folder = dump_folder
        self.tarfile_path = dump_folder.joinpath(str(uuid.uuid4())).with_suffix(SUFFIX)

    def _get_fixed_elements(self):
        # type: () -> List[ABCDiagnosticsElement]
        return [
            GeneralDiagnosticsElement(),
        ]

    def _get_optional_elements(self):
        # type: () -> List[ABCDiagnosticsElement]
        return []

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
                console.verbose("  %s: No information\n" % element.title)
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


class GeneralDiagnosticsElement(ABCDiagnosticsElement):
    @property
    def ident(self):
        # type: () -> str
        return "general"

    @property
    def title(self):
        # type: () -> str
        return "General"

    @property
    def description(self):
        # type: () -> str
        return "OS, Checkmk version and edition, Time, Core, Python version and paths"

    def add_or_get_file(self, tmp_dump_folder):
        # type: (Path) -> Optional[Path]
        filepath = tmp_dump_folder.joinpath(self.ident).with_suffix(".json")
        store.save_text_to_file(filepath, json.dumps(cmk_version.get_general_version_infos()))
        return filepath
