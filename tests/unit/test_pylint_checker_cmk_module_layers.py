#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import pytest
from pylint.lint import PyLinter

from tests.pylint.checker_cmk_module_layers import (
    _COMPONENTS,
    CMKModuleLayerChecker,
    get_absolute_importee,
    ModuleName,
    ModulePath,
)

CHECKER = CMKModuleLayerChecker(PyLinter())

COMPONENT_LIST = [c for c, _ in _COMPONENTS]


@pytest.mark.parametrize(
    "root_name, modname, level, is_package, abs_module",
    [
        ("cmk.checkengine.agent", "_base", 1, False, "cmk.checkengine._base"),
        # relative import in __init__
        ("cmk.checkengine", "agent", 1, True, "cmk.checkengine.agent"),
    ],
)
def test_get_absolute_importee(
    root_name: str, modname: str, level: int, is_package: bool, abs_module: str
) -> None:
    assert (
        get_absolute_importee(
            root_name=root_name,
            modname=modname,
            level=level,
            is_package=is_package,
        )
        == abs_module
    )


@pytest.mark.parametrize(
    "module_path, importer, importee, allowed",
    [
        # disallow cross component import
        ("cmk/base", "cmk.base", "cmk.gui", False),
        # allow component internal imprt
        ("cmk/gui", "cmk.gui.foo", "cmk.gui.bar", True),
        # `checkers` in `utils` is wrong but anywhere else is OK
        ("cmk/checkers", "cmk.checkengine.snmp", "cmk.utils", True),
        ("cmk/base", "cmk.base.sources", "cmk.checkengine", True),
        # disallow import of `snmplib` in `utils`
        ("cmk/utils", "cmk.utils.foo", "cmk.snmplib", False),
        ("cmk/base", "cmk.base.data_sources", "cmk.snmplib", True),
        # disallow import of `base` / `gui` in `automations`
        ("cmk/automations", "cmk.automations.x", "cmk.base.a", False),
        ("cmk/automations", "cmk.automations.y", "cmk.gui.b", False),
        # alow import of `automations` in `base` / `gui`
        ("cmk/base", "cmk.base.x", "cmk.automations.a", True),
        ("cmk/gui", "cmk.gui.y", "cmk.automations.b", True),
    ],
)
def test__is_import_allowed(module_path: str, importer: str, importee: str, allowed: bool) -> None:
    assert allowed is CHECKER._is_import_allowed(
        ModulePath(module_path),
        ModuleName(importer),
        ModuleName(importee),
    )
