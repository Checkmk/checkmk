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
    diagnostics_dump._create_dump_folders()

    assert diagnostics_dump.dump_folder.exists()
    assert diagnostics_dump.tmp_dump_folder.exists()
    assert diagnostics_dump.dump_folder.name == "NO_SITE"
    assert diagnostics_dump.tmp_dump_folder.name == "tmp"
    assert diagnostics_dump.tmp_dump_folder.parent.name == "NO_SITE"

    diagnostics_dump._create_tarfile()

    assert len(list(diagnostics_dump.dump_folder.glob("*.tar.gz"))) == 1
    assert len(list(diagnostics_dump.dump_folder.iterdir())) == 2
    assert len(diagnostics_dump.fixed_elements) <= len(
        list(diagnostics_dump.tmp_dump_folder.iterdir())) <= len(diagnostics_dump.elements)


def test_diagnostics_cleanup_dump_folders(monkeypatch, tmp_path):
    diagnostics_dump = diagnostics.DiagnosticsDump()
    diagnostics_dump._create_dump_folders()

    # Fake existing diagnostics elements
    for nr in range(10):
        diagnostics_dump.tmp_dump_folder.joinpath("dummy-%s" % nr).touch()

    # Fake existing tarfiles
    for nr in range(10):
        diagnostics_dump.dump_folder.joinpath("dummy-%s.tar.gz" % nr).touch()

    # 10 tarfiles + tmp folder
    assert len(list(diagnostics_dump.dump_folder.iterdir())) >= 11

    diagnostics_dump._cleanup_tmp_dump_folder()
    diagnostics_dump._cleanup_dump_folder()

    assert len(list(diagnostics_dump.dump_folder.iterdir())) == 5
    assert not diagnostics_dump.tmp_dump_folder.exists()


#.
#   .--elements------------------------------------------------------------.
#   |                   _                           _                      |
#   |               ___| | ___ _ __ ___   ___ _ __ | |_ ___                |
#   |              / _ \ |/ _ \ '_ ` _ \ / _ \ '_ \| __/ __|               |
#   |             |  __/ |  __/ | | | | |  __/ | | | |_\__ \               |
#   |              \___|_|\___|_| |_| |_|\___|_| |_|\__|___/               |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def test_version_diagnostics_element(monkeypatch, tmp_path):
    tmppath = Path(tmp_path).joinpath("tmp")

    version_diagnostics_element = diagnostics.GeneralDiagnosticsElement()
    assert version_diagnostics_element.ident == "general"

    filepath = version_diagnostics_element.add_or_get_file(tmppath)
    assert filepath == tmppath.joinpath("general.json")
    assert version_diagnostics_element.description == "General: OS, Checkmk version and edition, Time, Core, Python version and paths"

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
