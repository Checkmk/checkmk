#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=protected-access

import itertools
import pytest  # type: ignore[import]

from testlib.pylint_checker_cmk_module_layers import (
    _get_absolute_importee,
    CMKModuleLayerChecker,
    _COMPONENTS,
    Component,
    _in_component,
    ModuleName,
    ModulePath,
)

CHECKER = CMKModuleLayerChecker()

COMPONENT_LIST = [c for c, _ in _COMPONENTS]


@pytest.mark.parametrize(
    "root_name, modname, level, is_package, abs_module",
    [
        ("cmk.core_helpers.agent", "_base", 1, False, "cmk.core_helpers._base"),
        # relative import in __init__
        ("cmk.core_helpers", "agent", 1, True, "cmk.core_helpers.agent"),
    ])
def test__get_absolute_importee(root_name: str, modname: str, level: int, is_package: bool,
                                abs_module: str):
    assert _get_absolute_importee(
        root_name=root_name,
        modname=modname,
        level=level,
        is_package=is_package,
    ) == abs_module


@pytest.mark.parametrize("component", COMPONENT_LIST)
def test_utils_import_ok(component):
    for importee in ("cmk", "cmk.utils", "cmk.utils.anything"):
        is_ok = not _in_component(ModuleName(component), Component("cmk.base.plugins.agent_based"))
        assert is_ok is CHECKER._is_import_allowed(
            ModulePath("_not/relevant_"),
            ModuleName(f"{component}.foo"),
            ModuleName(importee),
        )


@pytest.mark.parametrize(
    "module_path, importer, importee, allowed",
    [
        # disallow cross component import
        ("cmk/base", "cmk.base", "cmk.gui", False),
        # allow component internal imprt
        ("cmk/gui", "cmk.gui.foo", "cmk.gui.bar", True),
        # utils not ok in agent based plugins
        ("_nevermind_", "cmk.base.plugins.agent_based.utils.foo", "cmk.utils.debug", False),
        # `fetchers` in `utils` is wrong but anywhere else is OK
        ("cmk/fetchers", "cmk.fetchers.snmp", "cmk.utils", True),
        ("cmk/utils", "cmk.utils.foo", "cmk.fetchers", False),
        ("cmk/base", "cmk.base.checkers", "cmk.fetchers", True),
        # disallow import of `snmplib` in `utils`
        ("cmk/utils", "cmk.utils.foo", "cmk.snmplib", False),
        ("cmk/base", "cmk.base.data_sources", "cmk.snmplib", True),
        # disallow import of one plugin in another
        ("cmk/base/plugins/agent_based", "cmk.base.plugins.agent_based.foo",
         "cmk.base.plugins.agent_based.bar", False),
    ])
def test__is_import_allowed(module_path, importer, importee, allowed):
    assert allowed is CHECKER._is_import_allowed(
        ModulePath(module_path),
        ModuleName(importer),
        ModuleName(importee),
    )
