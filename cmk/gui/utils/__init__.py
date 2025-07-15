#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""This is an unsorted collection of small unrelated helper functions which are
usable in all components of the web GUI of Check_MK

Please try to find a better place for the things you want to put here."""

import marshal
import uuid
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import cmk.utils.paths

from cmk.gui.log import logger


# TODO: Remove this helper function. Replace with explicit checks and covnersion
# in using code.
def savefloat(f: Any) -> float:
    try:
        return float(f)
    except (TypeError, ValueError):
        return 0.0


# TODO: Remove this helper function. Replace with explicit checks and covnersion
# in using code.
def saveint(x: Any) -> int:
    try:
        return int(x)
    except (TypeError, ValueError):
        return 0


def gen_id() -> str:
    """Generates a unique id"""
    return str(uuid.uuid4())


# This may not be moved to g, because this needs to be request independent
# TODO: Move to cmk.gui.modules once load_web_plugins is dropped
_failed_plugins: dict[Path, tuple[str, str, BaseException]] = {}


# Load all files below share/check_mk/web/plugins/WHAT into a specified context
# (global variables). Also honors the local-hierarchy for OMD
# TODO: This is kept for pre 1.6.0i1 plugins
def load_web_plugins(forwhat: str, globalvars: dict) -> None:
    for plugins_path in [
        cmk.utils.paths.web_dir / "plugins" / forwhat,
        cmk.utils.paths.local_web_dir / "plugins" / forwhat,
    ]:
        if not plugins_path.exists():
            continue

        for file_path in sorted(plugins_path.iterdir()):
            if file_path.suffix not in (".py", ".pyc"):
                continue

            try:
                if file_path.suffix == ".py" and not file_path.with_suffix(".pyc").exists():
                    with file_path.open(encoding="utf-8") as f:
                        exec(compile(f.read(), file_path, "exec"), globalvars)  # nosec B102 # BNS:aee528

                elif file_path.suffix == ".pyc":
                    with file_path.open("rb") as pyc:
                        code_bytes = pyc.read()[8:]
                    code = marshal.loads(code_bytes)  # nosec B302 # BNS:4607da
                    exec(code, globalvars)  # nosec B102 # BNS:aee528

            except Exception as e:
                logger.exception("Failed to load plug-in %s: %s", file_path, e)
                add_failed_plugin(file_path.with_suffix(".py"), forwhat, file_path.stem, e)


def add_failed_plugin(
    path: Path, main_module_name: str, plugin_name: str, e: BaseException
) -> None:
    _failed_plugins[path] = main_module_name, plugin_name, e


def get_failed_plugins() -> Sequence[tuple[Path, str, str, BaseException]]:
    return [
        (path, subcomponent, module_name, exc)
        for path, (subcomponent, module_name, exc) in _failed_plugins.items()
    ]


def remove_failed_plugin(entry: Path) -> None:
    _drop = _failed_plugins.pop(entry, None)


# TODO: Find a better place without introducing any cycles.
def cmp_service_name_equiv(r: str) -> int:
    if r == "Check_MK":
        return -6
    if r == "Check_MK Agent":
        return -5
    if r == "Check_MK Discovery":
        return -4
    if r == "Check_MK inventory":
        return -3  # FIXME: Remove old name one day
    if r == "Check_MK HW/SW Inventory":
        return -2
    return 0
