#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from pathlib import Path

import cmk.base.diagnostics as diagnostics

#   .--dump----------------------------------------------------------------.
#   |                         _                                            |
#   |                      __| |_   _ _ __ ___  _ __                       |
#   |                     / _` | | | | '_ ` _ \| '_ \                      |
#   |                    | (_| | |_| | | | | | | |_) |                     |
#   |                     \__,_|\__,_|_| |_| |_| .__/                      |
#   |                                          |_|                         |
#   '----------------------------------------------------------------------'


def test_diagnostics_dump_elements():
    fixed_element_classes = set([
        diagnostics.GeneralDiagnosticsElement,
    ])
    element_classes = set(type(e) for e in diagnostics.DiagnosticsDump().elements)
    assert fixed_element_classes.issubset(element_classes)


def test_diagnostics_dump_create(monkeypatch, tmp_path):
    diagnostics_dump = diagnostics.DiagnosticsDump()
    diagnostics_dump._create_dump_folder()

    assert diagnostics_dump.dump_folder.exists()
    assert diagnostics_dump.dump_folder.name == "diagnostics"

    diagnostics_dump._create_tarfile()

    tarfiles = diagnostics_dump.dump_folder.iterdir()
    assert len(list(tarfiles)) == 1
    assert all(tarfile.suffix == ".tar.gz" for tarfile in tarfiles)


def test_diagnostics_cleanup_dump_folder(monkeypatch, tmp_path):
    diagnostics_dump = diagnostics.DiagnosticsDump()
    diagnostics_dump._create_dump_folder()

    # Fake existing tarfiles
    for nr in range(10):
        diagnostics_dump.dump_folder.joinpath("dummy-%s.tar.gz" % nr).touch()

    diagnostics_dump._cleanup_dump_folder()

    tarfiles = diagnostics_dump.dump_folder.iterdir()
    assert len(list(tarfiles)) == diagnostics_dump._keep_num_dumps
    assert all(tarfile.suffix == ".tar.gz" for tarfile in tarfiles)


#.
#   .--elements------------------------------------------------------------.
#   |                   _                           _                      |
#   |               ___| | ___ _ __ ___   ___ _ __ | |_ ___                |
#   |              / _ \ |/ _ \ '_ ` _ \ / _ \ '_ \| __/ __|               |
#   |             |  __/ |  __/ | | | | |  __/ | | | |_\__ \               |
#   |              \___|_|\___|_| |_| |_|\___|_| |_|\__|___/               |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def test_diagnostics_element_general(monkeypatch, tmp_path):
    tmppath = Path(tmp_path).joinpath("tmp")

    version_diagnostics_element = diagnostics.GeneralDiagnosticsElement()
    assert version_diagnostics_element.ident == "general"
    assert version_diagnostics_element.title == "General"

    filepath = version_diagnostics_element.add_or_get_file(tmppath)
    assert filepath == tmppath.joinpath("general.json")
    assert version_diagnostics_element.description == "OS, Checkmk version and edition, Time, Core, Python version and paths"

    info_keys = [
        "time",
        "os",
        "version",
        "edition",
        "core",
        "python_version",
        "python_paths",
    ]
    assert sorted(json.loads(filepath.open().read()).keys()) == sorted(info_keys)
