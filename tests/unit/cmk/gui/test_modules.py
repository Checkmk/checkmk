#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import importlib
import sys
from pathlib import Path

import pytest

import cmk.utils.paths

from cmk.gui import modules


def _plugin_path(main_module_name: str) -> Path:
    return cmk.utils.paths.local_web_dir / "plugins" / main_module_name


@pytest.fixture(
    name="main_module_name",
    params=[
        "cron",
        "dashboard",
        "metrics",
        "sidebar",
        "userdb",
        "views",
        "visuals",
        "wato",
        "watolib",
        "webapi",
    ],
)
def fixture_main_module_name(request):
    return request.param


@pytest.fixture(name="local_plugin")
def fixture_local_plugin(main_module_name):
    plugin_file = _plugin_path(main_module_name) / "test_plugin.py"
    plugin_file.parent.mkdir(parents=True, exist_ok=True)
    with plugin_file.open("w") as f:
        f.write('ding = "dong"\n')


@pytest.mark.usefixtures("local_plugin")
def test_load_local_plugin(main_module_name):
    main_module = importlib.import_module(f"cmk.gui.{main_module_name}")
    assert "ding" not in main_module.__dict__

    try:
        modules.call_load_plugins_hooks()
        assert main_module.ding == "dong"  # type: ignore[attr-defined]
    finally:
        del main_module.__dict__["ding"]


@pytest.fixture(
    name="plugin_module_dir",
    params=[
        "wato",
        "wato",
        "watolib",
        "sidebar",
        "userdb",
        "webapi",
        "main_modules",
        "dashboard",
        "visuals",
        "cron",
        "config",
        "bi",
        "openapi",
        "openapi/endpoints",
        "views",
        "views/perfometers",
        "views/icons",
        "metrics",
    ],
)
def fixture_plugin_module_dir(request):
    return request.param


def test_plugins_loaded(plugin_module_dir):
    if plugin_module_dir == "bi":
        raise pytest.skip("No plugin at the moment")

    loaded_module_names = [
        name  #
        for name, module in sys.modules.items()
        # None entries are only an import optimization of cPython and can be removed:
        # https://www.python.org/dev/peps/pep-0328/#relative-imports-and-indirection-entries-in-sys-modules
        if module is not None
        and (
            name.startswith("cmk.gui.plugins.")
            or name.startswith("cmk.gui.cee.plugins.")  #
            or name.startswith("cmk.gui.cme.plugins.")  #
        )
    ]

    plugin_module_name = plugin_module_dir.replace("/", ".")
    assert [
        n
        for n in loaded_module_names
        if (
            n.startswith("cmk.gui.plugins." + plugin_module_name)
            or n.startswith("cmk.gui.cee.plugins." + plugin_module_name)  #
            or n.startswith("cmk.gui.cme.plugins." + plugin_module_name)  #
        )
    ]


# Needed later for local module import tests
# @pytest.fixture()
# def simple_plugin(plugin_module_dir):
#    plugin_file = cmk.utils.paths.local_gui_plugins_dir / plugin_module_dir / "test_plugin.py"
#    plugin_file.parent.mkdir(parents=True, exist_ok=True)
#    with plugin_file.open("w") as f:
#        f.write("ding = \"dong\"\n")
#
#
# @pytest.mark.usefixtures("simple_plugin")
# def test_load_gui_plugin(plugin_module_dir):
#    main_module = importlib.import_module(f"cmk.gui.{plugin_module_dir.replace('/', '.')}")
#    assert "ding" not in main_module.__dict__
#    modules.call_load_plugins_hooks()
#    assert main_module.ding == "dong"  # type: ignore[attr-defined]
