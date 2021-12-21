#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import sys
from pathlib import Path
from typing import Iterator

import pytest

from cmk.utils.plugin_loader import load_plugins_with_exceptions


@pytest.fixture(autouse=True)
def add_tmp_path_to_sys_path(tmp_path: Path) -> Iterator[Path]:
    sys.path.insert(0, str(tmp_path))
    try:
        yield tmp_path
    finally:
        sys.path.pop(0)


@pytest.fixture(name="package_type", params=["package", "namespace"])
def fixture_package_type(request) -> str:
    return request.param


@pytest.fixture(name="tmp_package")
def fixture_tmp_package(tmp_path: Path, package_type: str) -> str:
    package_name = f"test_plugin_loader_{package_type}"
    base = tmp_path.joinpath(package_name)
    base.joinpath("plugins/abc/level1").mkdir(parents=True)

    if package_type == "package":
        base.joinpath("__init__.py").touch()
        base.joinpath("plugins/__init__.py").touch()
        base.joinpath("plugins/abc/__init__.py").touch()
        base.joinpath("plugins/abc/level1/__init__.py").touch()
    elif package_type != "namespace":
        raise ValueError(package_type)

    level0 = base.joinpath("plugins/abc")
    level0.joinpath("plugin.py").touch()

    level1 = base.joinpath("plugins/abc/level1")
    level1.joinpath("plugin.py").touch()
    return package_name


def test_load_plugins_with_exceptions(tmp_package: str) -> None:
    assert list(load_plugins_with_exceptions(f"{tmp_package}.plugins.abc")) == []
    imported = [n for n in sys.modules if n.startswith(tmp_package)]
    assert sorted(imported) == sorted(
        [
            tmp_package,
            f"{tmp_package}.plugins",
            f"{tmp_package}.plugins.abc",
            f"{tmp_package}.plugins.abc.level1",
            f"{tmp_package}.plugins.abc.level1.plugin",
            f"{tmp_package}.plugins.abc.plugin",
        ]
    )

    for name in imported:
        del sys.modules[name]


@pytest.fixture(name="exc_package")
def fixture_exc_package(tmp_path: Path, package_type: str) -> str:
    package_name = "test_plugin_loader_exc"
    base = tmp_path.joinpath(package_name)
    base.mkdir()

    if package_type == "package":
        base.joinpath("__init__.py").touch()
    elif package_type != "namespace":
        raise ValueError(package_type)

    with base.joinpath("ding.py").open("w") as f:
        f.write("@A@RARAR")
    with base.joinpath("dong.py").open("w") as f:
        f.write("x = 1")
    return package_name


def test_load_plugins_with_exceptions_handle_exception(exc_package: str) -> None:
    package_name = exc_package
    errors = list(load_plugins_with_exceptions(package_name))
    assert len(errors) == 1
    assert errors[0][0] == "ding"
    assert isinstance(errors[0][1], SyntaxError)

    imported = [n for n in sys.modules if n.startswith(package_name)]
    assert sorted(imported) == sorted(
        [
            package_name,
            f"{package_name}.dong",
        ]
    )

    for name in imported:
        del sys.modules[name]


@pytest.fixture(name="import_error_package")
def fixture_import_error_package(tmp_path: Path, package_type: str) -> str:
    package_name = "test_plugin_loader_import_error"
    base = tmp_path.joinpath(package_name)
    level0 = base.joinpath("level0")
    level0.mkdir(parents=True)

    if package_type == "package":
        base.joinpath("__init__.py").touch()
        level0.joinpath("__init__.py").touch()
    elif package_type != "namespace":
        raise ValueError(package_type)

    with level0.joinpath("ding.py").open("w") as f:
        f.write("import dingeliding")
    with level0.joinpath("dong.py").open("w") as f:
        f.write("x = 1")

    return package_name


def test_load_plugins_with_exceptions_handle_import_error(import_error_package: str) -> None:
    package_name = import_error_package
    errors = list(load_plugins_with_exceptions(package_name))
    assert len(errors) == 1
    assert errors[0][0] == "level0.ding"
    assert isinstance(errors[0][1], ModuleNotFoundError)

    imported = [n for n in sys.modules if n.startswith(package_name)]
    assert sorted(imported) == sorted(
        [
            package_name,
            f"{package_name}.level0",
            f"{package_name}.level0.dong",
        ]
    )

    for name in imported:
        del sys.modules[name]
