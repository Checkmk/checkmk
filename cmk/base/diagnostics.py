#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import errno
import abc
from typing import (  # pylint: disable=unused-import
    List, Optional,
)
import uuid
import tarfile
import json
from pathlib import Path  # pylint: disable=unused-import

import six

import cmk.utils.paths
import cmk.utils.version as cmk_version
import cmk.utils.store as store

import cmk.base.console as console

SUFFIX = ".tar.gz"


def create_diagnostics_dump():
    # type: () -> None
    DiagnosticsDump().create()


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

        dump_folder = cmk.utils.paths.diagnostics_dir.joinpath(cmk_version.omd_site())
        # TODO use context manager for temporary folders
        self.dump_folder = dump_folder
        self.tmp_dump_folder = dump_folder.joinpath("tmp")
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
        self._create_dump_folders()
        self._create_tarfile()
        self._cleanup_tmp_dump_folder()
        self._cleanup_dump_folder()

    def _create_dump_folders(self):
        # type: () -> None
        console.verbose("Create dump folders:\n")
        self.dump_folder.mkdir(parents=True, exist_ok=True)
        console.verbose("  '%s'\n" % self._get_short_filepath(self.dump_folder))
        self.tmp_dump_folder.mkdir(parents=True, exist_ok=True)
        console.verbose("  '%s'\n" % self._get_short_filepath(self.tmp_dump_folder))

    def _create_tarfile(self):
        # type: () -> None
        filepaths = self._get_filepaths()

        console.verbose("Pack temporary files:\n")
        with tarfile.open(name=self.tarfile_path, mode='w:gz') as tar:
            for filepath in filepaths:
                console.verbose("  '%s'\n" % self._get_short_filepath(filepath))
                tar.add(str(filepath))

        console.output("Created diagnostics dump:\n")
        console.output("  '%s'\n" % self._get_short_filepath(self.tarfile_path))

    def _get_filepaths(self):
        # type: () -> List[Path]
        console.output("Collect diagnostics files:\n")
        filepaths = []
        for element in self.elements:
            filepath = element.add_or_get_file(self.tmp_dump_folder)
            if filepath is None:
                console.output("  %s: No informations\n" % element.ident)
                continue
            filepaths.append(filepath)
        return filepaths

    def _cleanup_tmp_dump_folder(self):
        # type: () -> None
        console.verbose("Remove temporary files:\n")
        for filepath in self.tmp_dump_folder.iterdir():
            console.verbose("  '%s'\n" % self._get_short_filepath(filepath))
            self._remove_file(filepath)

        console.verbose("Remove temporary dump folder:\n")
        console.verbose("  '%s'\n" % self._get_short_filepath(self.tmp_dump_folder))
        try:
            self.tmp_dump_folder.rmdir()
        except OSError as e:
            if e.errno != errno.ENOTEMPTY:
                raise

    def _cleanup_dump_folder(self):
        # type: () -> None
        dumps = sorted(
            [(dump.stat().st_mtime, dump) for dump in self.dump_folder.glob("*%s" % SUFFIX)],
            key=lambda t: t[0])[:-self._keep_num_dumps]

        console.verbose("Cleanup dump folder (remove old dumps, keep the last %s dumps):\n" %
                        self._keep_num_dumps)
        for _mtime, filepath in dumps:
            console.verbose("  '%s'\n" % self._get_short_filepath(filepath))
            self._remove_file(filepath)

    def _remove_file(self, filepath):
        # type: (Path) -> None
        try:
            filepath.unlink()
        except OSError as e:
            if e.errno != errno.ENOENT:
                raise

    def _get_short_filepath(self, filepath):
        # type: (Path) -> Path
        return filepath.relative_to(cmk.utils.paths.omd_root)


#.
#   .--elements------------------------------------------------------------.
#   |                   _                           _                      |
#   |               ___| | ___ _ __ ___   ___ _ __ | |_ ___                |
#   |              / _ \ |/ _ \ '_ ` _ \ / _ \ '_ \| __/ __|               |
#   |             |  __/ |  __/ | | | | |  __/ | | | |_\__ \               |
#   |              \___|_|\___|_| |_| |_|\___|_| |_|\__|___/               |
#   |                                                                      |
#   '----------------------------------------------------------------------'


class ABCDiagnosticsElement(six.with_metaclass(abc.ABCMeta, object)):
    @abc.abstractproperty
    def ident(self):
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

    def add_or_get_file(self, tmp_dump_folder):
        # type: (Path) -> Optional[Path]
        console.output(
            "  General: OS, Checkmk version and edition, Time, Core, Python version and paths\n")
        filepath = tmp_dump_folder.joinpath(self.ident)
        store.save_text_to_file(filepath, json.dumps(cmk_version.get_general_version_infos()))
        return filepath
