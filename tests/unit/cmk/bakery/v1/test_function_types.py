#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import re
from collections.abc import Generator
from pathlib import Path
from typing import Any

import pytest

from cmk.bakery.v1 import (
    create_bakery_plugin,
    FileGenerator,
    OS,
    Plugin,
    RpmStep,
    Scriptlet,
    ScriptletGenerator,
    WindowsConfigGenerator,
    WindowsGlobalConfigEntry,
)


def test_bakery_plugin_name() -> None:
    with pytest.raises(TypeError) as exc_info_type:
        create_bakery_plugin(name=b"dummy")  # type: ignore[arg-type]
    assert re.search("BakeryPluginName.*str", str(exc_info_type.value))

    with pytest.raises(ValueError) as exc_info_value:
        create_bakery_plugin(name="")
    assert re.search("empty", str(exc_info_value.value))

    with pytest.raises(ValueError) as exc_info_value:
        create_bakery_plugin(name="dümmy")
    assert re.search("Invalid character.*ü", str(exc_info_value.value))


def right_files_function() -> Generator[Plugin, None, None]:
    yield Plugin(base_os=OS.LINUX, source=Path("dummy"))


def right_scriptlets_function() -> Generator[Scriptlet, None, None]:
    yield Scriptlet(step=RpmStep.POST, lines=[])


def right_windows_config_function() -> Generator[WindowsGlobalConfigEntry, None, None]:
    yield WindowsGlobalConfigEntry(name="dummy", content=False)


def wrong_artifact_function() -> Generator[
    Plugin | Scriptlet | WindowsGlobalConfigEntry, None, None
]:
    yield Plugin(base_os=OS.LINUX, source=Path("dummy"))
    yield Scriptlet(step=RpmStep.POST, lines=[])
    yield WindowsGlobalConfigEntry(name="dummy", content=False)


def test_artifact_function_yielded_values() -> None:
    wrong_bakery_plugin = create_bakery_plugin(
        name="dummy",
        files_function=wrong_artifact_function,  # type: ignore[arg-type]
        scriptlets_function=wrong_artifact_function,  # type: ignore[arg-type]
        windows_config_function=wrong_artifact_function,  # type: ignore[arg-type]
    )

    right_bakery_plugin = create_bakery_plugin(
        name="dummy",
        files_function=right_files_function,
        scriptlets_function=right_scriptlets_function,
        windows_config_function=right_windows_config_function,
    )

    empty_bakery_plugin = create_bakery_plugin(name="dummy")

    list(right_bakery_plugin.files_function())
    list(right_bakery_plugin.scriptlets_function())
    list(right_bakery_plugin.windows_config_function())

    list(empty_bakery_plugin.files_function())
    list(empty_bakery_plugin.scriptlets_function())
    list(empty_bakery_plugin.windows_config_function())

    with pytest.raises(TypeError) as exc_info:
        list(wrong_bakery_plugin.files_function())
    assert re.search(
        "files_function.*Plugin, PluginConfig, SystemBinary, SystemConfig.*Scriptlet",
        str(exc_info.value),
    )

    with pytest.raises(TypeError) as exc_info:
        list(wrong_bakery_plugin.scriptlets_function())
    assert re.search("scriptlets_function.*Scriptlet.*Plugin", str(exc_info.value))

    with pytest.raises(TypeError) as exc_info:
        list(wrong_bakery_plugin.windows_config_function())
    assert re.search(
        "windows_config_function.*WindowsConfigEntry, WindowsConfigItems, "
        "WindowsGlobalConfigEntry, WindowsSystemConfigEntry.*Plugin",
        str(exc_info.value),
    )


def files_function_with_aghash(conf: Any, aghash: str) -> FileGenerator:
    yield Plugin(base_os=OS.LINUX, source=Path("dummy"))


def scriptlets_function_with_dummy(conf: Any, aghash: str, dummy: Any) -> ScriptletGenerator:
    yield Scriptlet(step=RpmStep.POST, lines=[])


def windows_config_function_with_hurz(conf: Any, aghash: str, hurz: Any) -> WindowsConfigGenerator:
    yield WindowsGlobalConfigEntry(name="dummy", content=False)


def test_artifact_function_arguments() -> None:
    with pytest.raises(ValueError) as exc_info:
        create_bakery_plugin(
            name="dummy",
            files_function=files_function_with_aghash,
        )
    assert re.search("Unsupported.*aghash.*files_function", str(exc_info.value))

    with pytest.raises(ValueError) as exc_info:
        create_bakery_plugin(
            name="dummy",
            scriptlets_function=scriptlets_function_with_dummy,
        )
    assert re.search("Unsupported.*dummy.*scriptlets_function", str(exc_info.value))

    with pytest.raises(ValueError) as exc_info:
        create_bakery_plugin(
            name="dummy",
            windows_config_function=windows_config_function_with_hurz,
        )
    assert re.search("Unsupported.*hurz.*windows_config_function", str(exc_info.value))


def test_artifact_function_generator() -> None:
    with pytest.raises(TypeError) as exc_info:
        create_bakery_plugin(
            name="dummy",
            files_function=123,  # type: ignore[arg-type]
        )
    assert re.search("files_function.*generator function", str(exc_info.value))

    with pytest.raises(TypeError) as exc_info:
        create_bakery_plugin(
            name="dummy",
            scriptlets_function=(
                lambda: [Scriptlet(step=RpmStep.POST, lines=[])]  # type: ignore[arg-type, return-value]
            ),
        )
    assert re.search("scriptlets_function.*generator function", str(exc_info.value))

    with pytest.raises(TypeError) as exc_info:
        create_bakery_plugin(
            name="dummy",
            windows_config_function=lambda: "dummy",  # type: ignore[arg-type, return-value]
        )
    assert re.search("windows_config_function.*generator function", str(exc_info.value))
