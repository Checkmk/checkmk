#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""This is an unsorted collection of small unrelated helper functions which are
usable in all components of the Web GUI of Check_MK

Please try to find a better place for the things you want to put here."""

import marshal
import urllib.parse
import uuid
from pathlib import Path
from typing import Any, Final, Sequence

import cmk.utils.paths
import cmk.utils.regex

from cmk.gui.log import logger


def is_allowed_url(url: str, cross_domain: bool = False, schemes: list[str] | None = None) -> bool:
    """Check if url is allowed

    >>> is_allowed_url("http://checkmk.com/")
    False
    >>> is_allowed_url("http://checkmk.com/", cross_domain=True, schemes=["http", "https"])
    True
    >>> is_allowed_url("/checkmk/", cross_domain=True, schemes=["http", "https"])
    True
    >>> is_allowed_url("//checkmk.com/", cross_domain=True)
    True
    >>> is_allowed_url("/foobar")
    True
    >>> is_allowed_url("//user:password@domain/", cross_domain=True)
    True
    >>> is_allowed_url("javascript:alert(1)")
    False
    >>> is_allowed_url("javascript:alert(1)", cross_domain=True, schemes=["javascript"])
    True
    >>> is_allowed_url('someXSSAttempt?"><script>alert(1)</script>')
    False
    """

    try:
        parsed = urllib.parse.urlparse(url)
    except ValueError:
        return False

    if not cross_domain and parsed.netloc != "":
        return False

    if schemes is None and parsed.scheme != "":
        return False
    if schemes is not None and parsed.scheme and parsed.scheme not in schemes:
        return False

    urlchar_regex = cmk.utils.regex.regex(cmk.utils.regex.URL_CHAR_REGEX)
    for part in parsed:
        if not part:
            continue
        if not urlchar_regex.match(part):
            return False

    return True


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
_failed_plugins: dict[str, list[tuple[str, BaseException]]] = {}


# Load all files below share/check_mk/web/plugins/WHAT into a specified context
# (global variables). Also honors the local-hierarchy for OMD
# TODO: This is kept for pre 1.6.0i1 plugins
def load_web_plugins(forwhat: str, globalvars: dict) -> None:
    for plugins_path in [
        Path(cmk.utils.paths.web_dir, "plugins", forwhat),
        cmk.utils.paths.local_web_dir / "plugins" / forwhat,
    ]:
        if not plugins_path.exists():
            continue

        for file_path in sorted(plugins_path.iterdir()):
            try:
                if file_path.suffix == ".py" and not file_path.with_suffix(".pyc").exists():
                    with file_path.open(encoding="utf-8") as f:
                        exec(f.read(), globalvars)

                elif file_path.suffix == ".pyc":
                    with file_path.open("rb") as pyc:
                        code_bytes = pyc.read()[8:]
                    code = marshal.loads(code_bytes)
                    exec(code, globalvars)

            except Exception as e:
                logger.exception("Failed to load plugin %s: %s", file_path, e)
                add_failed_plugin(forwhat, str(file_path), e)


def add_failed_plugin(main_module_name: str, plugin_name: str, e: BaseException) -> None:
    _failed_plugins.setdefault(main_module_name, []).append((plugin_name, e))


def get_failed_plugins() -> Sequence[tuple[str, str, BaseException]]:
    return [
        (gui_part, file_name, exception)
        for gui_part, errors in _failed_plugins.items()
        for file_name, exception in errors
    ]
