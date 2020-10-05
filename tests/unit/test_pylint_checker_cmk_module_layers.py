#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=protected-access

import itertools
import pytest  # type: ignore[import]

from testlib.pylint_checker_cmk_module_layers import (
    CMKModuleLayerChecker,
    _COMPONENTS,
    Component,
    ModuleName,
    ModulePath,
)

CHECKER = CMKModuleLayerChecker()

COMPONENT_LIST = [c for c, _ in _COMPONENTS]


@pytest.mark.parametrize("component", COMPONENT_LIST)
def test_utils_import_ok(component):
    for importee in ("cmk", "cmk.utils", "cmk.utils.anything"):
        assert CHECKER._is_import_allowed(
            ModulePath("_not/relevant_"),
            ModuleName(f"{component}.foo"),
            ModuleName(importee),
        )


@pytest.mark.parametrize(
    "importer, importee",
    list(itertools.product(COMPONENT_LIST, COMPONENT_LIST)),
)
def test_cross_component_not_ok(importer, importee):
    is_ok = (importee in {"cmk.fetchers", "cmk.snmplib"} and
             importer in {"cmk.base", "cmk.fetchers"} or importer == importee)
    assert is_ok is CHECKER._is_import_allowed(
        ModulePath("_not/relevant_"),
        ModuleName(f"{importer}.foo"),
        ModuleName(importee),
    )


@pytest.mark.parametrize(
    "module_path, importer, importee, allowed",
    [
        # `fetchers` in `utils` is wrong but anywhere else is OK
        ("cmk/fetchers", "cmk.fetchers.snmp", "cmk.utils", True),
        # FIXME: this result is correct, but this case will not be covered in real scenario,
        # b/c cmk.utils is not listed in components.
        ("cmk/utils", "cmk.utils.foo", "cmk.fetchers", False),
        ("cmk/base", "cmk.base.checkers", "cmk.fetchers", True),
        # disallow import of `snmplib` in `utils`
        ("cmk/utils", "cmk.utils.foo", "cmk.snmplib", False),
        ("cmk/base", "cmk.base.data_sources", "cmk.snmplib", True),
        # another broken one:
        ("cmk/base", "cmk.base.config", "cmk.gui.plugins", False),
    ])
def test__is_import_allowed(module_path, importer, importee, allowed):
    assert allowed is CHECKER._is_import_allowed(
        ModulePath(module_path),
        ModuleName(importer),
        ModuleName(importee),
    )
