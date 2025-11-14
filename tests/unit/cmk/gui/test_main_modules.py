#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"
# mypy: disable-error-code="no-untyped-def"


import importlib
import sys
from pathlib import Path

import pytest

import cmk.utils.paths


def _plugin_path(main_module_name: str) -> Path:
    return cmk.utils.paths.local_web_dir / "plugins" / main_module_name


def write_local_plugin(namespace: str) -> None:
    plugin_file = _plugin_path(namespace) / "test_plugin.py"
    plugin_file.parent.mkdir(parents=True, exist_ok=True)
    with plugin_file.open("w") as f:
        f.write('ding = "dong"\n')


def test_load_legacy_dashboard_plugin() -> None:
    write_local_plugin("dashboard")
    main_module = importlib.import_module("cmk.gui.dashboard")
    assert "ding" not in main_module.__dict__
    try:
        main_module.register()
        assert main_module.ding == "dong"
    finally:
        del main_module.__dict__["ding"]


def test_load_legacy_wato_plugin() -> None:
    write_local_plugin("wato")
    main_module = importlib.import_module("cmk.gui.wato")
    assert "ding" not in main_module.__dict__
    try:
        main_module.register()
        assert main_module.ding == "dong"
    finally:
        del main_module.__dict__["ding"]


def test_load_legacy_watolib_plugin() -> None:
    write_local_plugin("watolib")
    wato_module = importlib.import_module("cmk.gui.wato")
    main_module = importlib.import_module("cmk.gui.watolib")
    assert "ding" not in main_module.__dict__
    try:
        wato_module.register()
        assert main_module.ding == "dong"
    finally:
        del main_module.__dict__["ding"]


def test_load_legacy_views_plugin() -> None:
    write_local_plugin("views")
    main_module = importlib.import_module("cmk.gui.views")
    assert "ding" not in main_module.__dict__
    try:
        main_module.register()
        assert main_module.ding == "dong"
    finally:
        del main_module.__dict__["ding"]


@pytest.fixture(
    name="plugin_module_dir",
    params=[
        "wato",
        "wato",
        "watolib",
        "sidebar",
        "dashboard",
        "visuals",
        "config",
        "views",
        "views/icons",
    ],
)
def fixture_plugin_module_dir(request):
    return request.param


def test_plugins_loaded(plugin_module_dir: str) -> None:
    loaded_module_names = [
        module_name
        for module_name in sys.modules
        # None entries are only an import optimization of cPython and can be removed:
        # https://www.python.org/dev/peps/pep-0328/#relative-imports-and-indirection-entries-in-sys-modules
        if module_name.startswith("cmk.gui.plugins.")
        or module_name.startswith("cmk.gui.nonfree.pro.plugins.")
        or module_name.startswith("cmk.gui.nonfree.ultimatemt.plugins.")
    ]

    plugin_module_name = plugin_module_dir.replace("/", ".")
    assert [
        n
        for n in loaded_module_names
        if (
            n.startswith("cmk.gui.plugins." + plugin_module_name)
            or n.startswith("cmk.gui.nonfree.pro.plugins." + plugin_module_name)  #
            or n.startswith("cmk.gui.nonfree.ultimatemt.plugins." + plugin_module_name)  #
        )
    ]
