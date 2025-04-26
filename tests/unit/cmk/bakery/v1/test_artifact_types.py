#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import re
from pathlib import Path

import pytest

from cmk.bakery.v1 import (
    OS,
    Plugin,
    PluginConfig,
    RpmStep,
    Scriptlet,
    SystemBinary,
    SystemConfig,
    WindowsConfigEntry,
    WindowsConfigItems,
    WindowsGlobalConfigEntry,
    WindowsSystemConfigEntry,
)


def test_plugin() -> None:
    with pytest.raises(TypeError) as exc_info:
        Plugin(
            base_os=OS.LINUX,
            source=Path("some/source"),
            interval="1234",  # type: ignore[arg-type]
            timeout=1234,
        )
    assert re.search("interval.*int", str(exc_info.value))
    assert "int" in str(exc_info.value)

    Plugin(base_os=OS.LINUX, source=Path("some/source"), interval=1234, timeout=1234)


def test_plugin_config() -> None:
    def get_lines():
        yield "dummy"

    with pytest.raises(TypeError) as exc_info:
        PluginConfig(
            base_os=OS.WINDOWS,
            lines=list(get_lines()),
            target=Path("some/target"),
            include_header="yes",  # type: ignore[arg-type]
        )
    assert re.search("include_header.*bool", str(exc_info.value))

    with pytest.raises(TypeError) as exc_info:
        PluginConfig(
            base_os=OS.WINDOWS,
            lines=get_lines(),
            target=Path("some/target"),
            include_header=True,
        )
    assert re.search("lines.*list", str(exc_info.value))

    PluginConfig(
        base_os=OS.WINDOWS,
        lines=list(get_lines()),
        target=Path("some/target"),
        include_header=True,
    )


def test_system_binary() -> None:
    with pytest.raises(TypeError) as exc_info:
        SystemBinary(
            base_os="solaris",  # type: ignore[arg-type]
            source=Path("some/source"),
        )
    assert re.search("base_os.*OS", str(exc_info.value))

    SystemBinary(
        base_os=OS.SOLARIS,
        source=Path("some/source"),
    )


def test_system_config() -> None:
    with pytest.raises(TypeError) as exc_info:
        SystemConfig(
            base_os=OS.WINDOWS,
            lines=["dummy", 1234],  # type: ignore[list-item]
            target=Path("some/target"),
            include_header=True,
        )
    assert re.search("lines.*str.*index 1", str(exc_info.value))

    SystemConfig(
        base_os=OS.WINDOWS,
        lines=["dummy", "1234"],
        target=Path("some/target"),
        include_header=True,
    )


def test_scriptlet() -> None:
    with pytest.raises(TypeError) as exc_info:
        Scriptlet(
            step="postinstall",  # type: ignore[arg-type]
            lines=["dummy", "dummy"],
        )

    assert re.search("step.*Step", str(exc_info.value))

    Scriptlet(
        step=RpmStep.POST,
        lines=["dummy", "dummy"],
    )


def test_windows_config_entry_wrong_type() -> None:
    with pytest.raises(TypeError) as exc_info:
        WindowsConfigEntry(
            path="config, path",  # type: ignore[arg-type]
            content="dummy",
        )
    assert re.search("path.*list", str(exc_info.value))

    with pytest.raises(TypeError) as exc_info:
        WindowsConfigEntry(
            path=["proper", "path", "name"],
            content=OS.LINUX,  # type: ignore[arg-type]
        )
    assert re.search("content.*bool.*dict.*int.*list.*str", str(exc_info.value))

    WindowsConfigEntry(
        path=["proper", "path", "name"],
        content="dummy",
    )


def test_windows_config_entry_wrong_value() -> None:
    with pytest.raises(ValueError) as exc_info:
        WindowsConfigEntry(
            path=["name"],
            content="dummy",
        )
    assert re.search("Minimum.*2", str(exc_info.value))

    with pytest.raises(ValueError) as exc_info:
        WindowsConfigEntry(
            path=["too", "long", "path", "name"],
            content="dummy",
        )
    assert re.search("Maximum.*3", str(exc_info.value))


def test_windows_config_items() -> None:
    with pytest.raises(TypeError) as exc_info:
        WindowsConfigItems(
            path=["proper", "path", "name"],
            content="dummy",  # type: ignore[arg-type]
        )
    assert re.search("content.*list", str(exc_info.value))

    with pytest.raises(TypeError) as exc_info:
        WindowsConfigItems(
            path=["proper", "path", "name"],
            content=["dummy", 123, None],  # type: ignore[list-item]
        )
    assert re.search("index.*2.*content", str(exc_info.value))

    WindowsConfigItems(
        path=["proper", "path", "name"],
        content=["dummy"],
    )


def test_windows_global_config_entry() -> None:
    with pytest.raises(TypeError) as exc_info:
        WindowsGlobalConfigEntry(
            name="dummy",
            content=None,  # type: ignore[arg-type]
        )
    assert re.search("content.*bool.*dict.*int.*list.*str", str(exc_info.value))

    WindowsGlobalConfigEntry(
        name="dummy",
        content=False,
    )


def test_windows_system_config_entry() -> None:
    with pytest.raises(TypeError) as exc_info:
        WindowsSystemConfigEntry(
            name=b"dummy",  # type: ignore[arg-type]
            content={"dummy": [123, 123]},
        )
    assert re.search("name.*str", str(exc_info.value))

    WindowsSystemConfigEntry(
        name="dummy",
        content={"dummy": [123, 123]},
    )
