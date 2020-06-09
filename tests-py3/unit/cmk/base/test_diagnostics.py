#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from pathlib import Path
import shutil

import cmk.utils.paths
import cmk.utils.packaging as packaging

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


def test_diagnostics_dump_create():
    diagnostics_dump = diagnostics.DiagnosticsDump()
    diagnostics_dump._create_dump_folder()

    assert isinstance(diagnostics_dump.dump_folder, Path)

    assert diagnostics_dump.dump_folder.exists()
    assert diagnostics_dump.dump_folder.name == "diagnostics"

    diagnostics_dump._create_tarfile()

    tarfiles = diagnostics_dump.dump_folder.iterdir()
    assert len(list(tarfiles)) == 1
    assert all(tarfile.suffix == ".tar.gz" for tarfile in tarfiles)


def test_diagnostics_cleanup_dump_folder():
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


def test_diagnostics_element_general():
    diagnostics_element = diagnostics.GeneralDiagnosticsElement()
    assert diagnostics_element.ident == "general"
    assert diagnostics_element.title == "General"
    assert diagnostics_element.description == ("OS, Checkmk version and edition, Time, Core, "
                                               "Python version and paths, Architecture")


def test_diagnostics_element_general_content(tmp_path):
    diagnostics_element = diagnostics.GeneralDiagnosticsElement()
    tmppath = Path(tmp_path).joinpath("tmp")
    filepath = diagnostics_element.add_or_get_file(tmppath)

    assert isinstance(filepath, Path)
    assert filepath == tmppath.joinpath("general.json")

    info_keys = [
        "time",
        "os",
        "version",
        "edition",
        "core",
        "python_version",
        "python_paths",
        "arch",
    ]
    content = json.loads(filepath.open().read())

    assert sorted(content.keys()) == sorted(info_keys)


def test_diagnostics_element_local_files():
    diagnostics_element = diagnostics.LocalFilesDiagnosticsElement()
    assert diagnostics_element.ident == "local_files"
    assert diagnostics_element.title == "Local Files"
    assert diagnostics_element.description == (
        "List of installed, unpacked, optional files below $OMD_ROOT/local. "
        "This also includes information about installed MKPs.")


def test_diagnostics_element_local_files_content(tmp_path):
    diagnostics_element = diagnostics.LocalFilesDiagnosticsElement()

    def create_test_package(name):
        check_dir = cmk.utils.paths.local_checks_dir
        check_dir.mkdir(parents=True, exist_ok=True)

        with check_dir.joinpath(name).open("w", encoding="utf-8") as f:
            f.write(u"test-check\n")

        package_info = packaging.get_initial_package_info(name)
        package_info["files"] = {
            "checks": [name],
        }

        packaging.create_package(package_info)

    packaging.package_dir().mkdir(parents=True, exist_ok=True)
    name = "test-package"
    create_test_package(name)

    tmppath = Path(tmp_path).joinpath("tmp")
    filepath = diagnostics_element.add_or_get_file(tmppath)

    assert isinstance(filepath, Path)
    assert filepath == tmppath.joinpath("local_files.json")

    info_keys = [
        "installed",
        "unpackaged",
        "parts",
        "optional_packages",
    ]
    content = json.loads(filepath.open().read())

    assert sorted(content.keys()) == sorted(info_keys)

    installed_keys = [name]
    assert sorted(content['installed'].keys()) == sorted(installed_keys)
    assert content["installed"][name]['files'] == {'checks': [name]}

    unpackaged_keys = [
        'agent_based',
        'agents',
        'alert_handlers',
        'bin',
        'checkman',
        'checks',
        'doc',
        'ec_rule_packs',
        'inventory',
        'lib',
        'locales',
        'mibs',
        'notifications',
        'pnp-templates',
        'web',
    ]
    assert sorted(content["unpackaged"].keys()) == sorted(unpackaged_keys)
    for key in unpackaged_keys:
        assert content["unpackaged"][key] == []

    parts_keys = [
        'agent_based',
        'agents',
        'alert_handlers',
        'bin',
        'checkman',
        'checks',
        'doc',
        'ec_rule_packs',
        'inventory',
        'lib',
        'locales',
        'mibs',
        'notifications',
        'pnp-templates',
        'web',
    ]
    assert sorted(content["parts"].keys()) == sorted(parts_keys)
    part_keys = [
        'files',
        'path',
        'permissions',
        'title',
    ]
    for key in parts_keys:
        assert sorted(content["parts"][key].keys()) == sorted(part_keys)
        if key == "checks":
            assert content["parts"][key]['files'] == [name]
            assert content["parts"][key]['permissions'] == [420]
        else:
            assert content["parts"][key]['files'] == []
            assert content["parts"][key]['permissions'] == []

    assert content["optional_packages"] == {}

    shutil.rmtree(str(packaging.package_dir()))
