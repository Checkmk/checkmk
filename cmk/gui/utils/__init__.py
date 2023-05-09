#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""This is an unsorted collection of small unrelated helper functions which are
usable in all components of the Web GUI of Check_MK

Please try to find a better place for the things you want to put here."""

import re
import uuid
import marshal
import itertools
from pathlib import Path
from typing import (
    Any,
    Callable,
    Dict,
    Iterable,
    List,
    Optional,
    Tuple,
    Union,
)

from six import ensure_str

import cmk.utils.paths
import cmk.utils.regex
from cmk.utils.urls import is_allowed_url
from cmk.gui.hooks import request_memoize

from cmk.gui.i18n import _
from cmk.gui.log import logger
from cmk.gui.exceptions import MKUserError


@request_memoize(maxsize=100000)
def num_split(s: str) -> Tuple[Union[int, str], ...]:
    """Splits a word into sequences of numbers and non-numbers.

    Creates a tuple from these where the number are converted into int datatype.
    That way a naturual sort can be implemented.
    """
    parts: List[Union[int, str]] = []
    for part in re.split(r'(\d+)', s):
        try:
            parts.append(int(part))
        except ValueError:
            parts.append(part)

    return tuple(parts)


@request_memoize(maxsize=100000)
def cmp_num_split(a: str, b: str) -> int:
    """Compare two strings, separate numbers and non-numbers from before."""
    return (num_split(a) > num_split(b)) - (num_split(a) < num_split(b))


def key_num_split(a: str) -> Tuple[Union[int, str], ...]:
    """Return a key from a string, separate numbers and non-numbers from before."""
    return num_split(a)


def validate_start_url(value: str, varprefix: str) -> None:
    if not is_allowed_url(value):
        raise MKUserError(
            varprefix,
            _("The given value is not allowed. You may only configure "
              "relative URLs like <tt>dashboard.py?name=my_dashboard</tt>."))


def cmp_version(a: Optional[str], b: Optional[str]) -> int:
    """Compare two version numbers with each other
    Allow numeric version numbers, but also characters.
    """
    if a is None or b is None:
        if a is None:
            a = ""
        if b is None:
            b = ""
        return (a > b) - (a < b)
    aa = list(map(num_split, a.split(".")))
    bb = list(map(num_split, b.split(".")))
    return (aa > bb) - (aa < bb)


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


# We should use /dev/random here for cryptographic safety. But
# that involves the great problem that the system might hang
# because of loss of entropy. So we hope /dev/urandom is enough.
# Furthermore we filter out non-printable characters. The byte
# 0x00 for example does not make it through HTTP and the URL.
def get_random_string(size: int, from_ascii: int = 48, to_ascii: int = 90) -> str:
    """Generate a random string (no cryptographic safety)"""
    secret = ""
    with Path("/dev/urandom").open("rb") as urandom:
        while len(secret) < size:
            c = urandom.read(1)
            if ord(c) >= from_ascii and ord(c) <= to_ascii:
                secret += ensure_str(c)
    return secret


def gen_id() -> str:
    """Generates a unique id"""
    try:
        with Path("/proc/sys/kernel/random/uuid").open("r", encoding="utf-8") as f:
            return ensure_str(f.read().strip())
    except IOError:
        # On platforms where the above file does not exist we try to
        # use the python uuid module which seems to be a good fallback
        # for those systems.
        return str(uuid.uuid4())


# This may not be moved to g, because this needs to be request independent
_failed_plugins: Dict[str, List[Tuple[str, Exception]]] = {}


# Load all files below share/check_mk/web/plugins/WHAT into a specified context
# (global variables). Also honors the local-hierarchy for OMD
# TODO: This is kept for pre 1.6.0i1 plugins
def load_web_plugins(forwhat: str, globalvars: Dict) -> None:
    _failed_plugins[forwhat] = []

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
                    exec(code, globalvars)  # yapf: disable

            except Exception as e:
                logger.exception("Failed to load plugin %s: %s", file_path, e)
                _failed_plugins[forwhat].append((str(file_path), e))


def get_failed_plugins() -> List[Tuple[str, Exception]]:
    return list(itertools.chain(*list(_failed_plugins.values())))


def validate_regex(value: str, varname: Optional[str]) -> None:
    try:
        re.compile(value)
    except re.error:
        raise MKUserError(
            varname,
            _('Your search statement is not valid. You need to provide a regular '
              'expression (regex). For example you need to use <tt>\\\\</tt> instead of <tt>\\</tt> '
              'if you like to search for a single backslash.'))

    # livestatus uses re2 and re can not validate posix pattern, so we have to
    # check for lookaheads here
    lookahead_pattern = r'\((\?!|\?=|\?<)'

    if re.search(lookahead_pattern, value):
        raise MKUserError(
            varname, _('Your search statement is not valid. You can not use a lookahead here.'))


def unique_default_name_suggestion(template: str, used_names: Iterable[str]) -> str:
    used_names_set = set(used_names)
    nr = 1
    while True:
        suggestion = "%s_%d" % (template.replace(" ", "_"), nr)
        if suggestion not in used_names_set:
            return suggestion
        nr += 1


def validate_id(
    mode: str,
    existing_entries: Dict[str, Any],
) -> Callable[[Dict[str, Any], str], None,]:
    """ Validate ID of newly created or cloned pagetype or visual """
    def _validate(properties: Dict[str, Any], varprefix: str) -> None:
        name = properties["name"]
        if existing_entries.get(name) and mode in ["create", "clone"]:
            raise MKUserError(
                varprefix + "_p_name",
                _("You already have an element with the ID <b>%s</b>") % name,
            )

    return _validate
