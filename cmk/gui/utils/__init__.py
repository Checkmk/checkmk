#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""This is an unsorted collection of small unrelated helper functions which are
usable in all components of the Web GUI of Check_MK

Please try to find a better place for the things you want to put here."""

import sys
import re
import uuid
import marshal
import itertools
from typing import Text, Optional, Union, Any, List, Dict, Tuple  # pylint: disable=unused-import
import six

if sys.version_info[0] >= 3:
    from pathlib import Path  # pylint: disable=import-error
else:
    from pathlib2 import Path  # pylint: disable=import-error

import cmk.utils.paths

from cmk.gui.i18n import _
from cmk.gui.log import logger
from cmk.gui.exceptions import MKUserError


def num_split(s):
    # type: (Union[str, Text]) -> Tuple[Union[int, str, Text], ...]
    """Splits a word into sequences of numbers and non-numbers.

    Creates a tuple from these where the number are converted into int datatype.
    That way a naturual sort can be implemented.
    """
    parts = []  # type: List[Union[int, str, Text]]
    for part in re.split(r'(\d+)', s):
        try:
            parts.append(int(part))
        except ValueError:
            parts.append(part)

    return tuple(parts)


def cmp_num_split(a, b):
    # type: (str, str) -> int
    """Compare two strings, separate numbers and non-numbers from before."""
    return (num_split(a) > num_split(b)) - (num_split(a) < num_split(b))


def key_num_split(a):
    # type: (Union[str, Text]) -> Tuple[Union[int, str, Text], ...]
    """Return a key from a string, separate numbers and non-numbers from before."""
    return num_split(a)


def is_allowed_url(url):
    # type: (str) -> bool
    """Checks whether or not the given URL is a URL it is allowed to redirect the user to"""
    # Also prevent using of "javascript:" URLs which could used to inject code
    parsed = six.moves.urllib.parse.urlparse(url)

    # Don't allow the user to set a URL scheme
    if parsed.scheme != "":
        return False

    # Don't allow the user to set a network location
    if parsed.netloc != "":
        return False

    # Don't allow bad characters in path
    if not re.match(r"[/a-z0-9_\.-]*$", parsed.path):
        return False

    return True


def validate_start_url(value, varprefix):
    # type: (str, str) -> None
    if not is_allowed_url(value):
        raise MKUserError(
            varprefix,
            _("The given value is not allowed. You may only configure "
              "relative URLs like <tt>dashboard.py?name=my_dashboard</tt>."))


def cmp_version(a, b):
    # type: (Optional[str], Optional[str]) -> int
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
def savefloat(f):
    # type: (Any) -> float
    try:
        return float(f)
    except (TypeError, ValueError):
        return 0.0


# TODO: Remove this helper function. Replace with explicit checks and covnersion
# in using code.
def saveint(x):
    # type: (Any) -> int
    try:
        return int(x)
    except (TypeError, ValueError):
        return 0


# We should use /dev/random here for cryptographic safety. But
# that involves the great problem that the system might hang
# because of loss of entropy. So we hope /dev/urandom is enough.
# Furthermore we filter out non-printable characters. The byte
# 0x00 for example does not make it through HTTP and the URL.
def get_random_string(size, from_ascii=48, to_ascii=90):
    # type: (int, int, int) -> str
    """Generate a random string (no cryptographic safety)"""
    secret = ""
    urandom = open("/dev/urandom")
    while len(secret) < size:
        c = urandom.read(1)
        if ord(c) >= from_ascii and ord(c) <= to_ascii:
            secret += c
    return secret


def gen_id():
    # type: () -> str
    """Generates a unique id"""
    try:
        return open('/proc/sys/kernel/random/uuid').read().strip()
    except IOError:
        # On platforms where the above file does not exist we try to
        # use the python uuid module which seems to be a good fallback
        # for those systems.
        return str(uuid.uuid4())


# This may not be moved to g, because this needs to be request independent
_failed_plugins = {}  # type: Dict[str, List[Tuple[str, Exception]]]


# Load all files below share/check_mk/web/plugins/WHAT into a specified context
# (global variables). Also honors the local-hierarchy for OMD
# TODO: This is kept for pre 1.6.0i1 plugins
def load_web_plugins(forwhat, globalvars):
    # type: (str, Dict) -> None
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
                    exec (_drop_comments(file_path.open().read()), globalvars)

                elif file_path.suffix == ".pyc":
                    code_bytes = file_path.open("rb").read()[8:]
                    code = marshal.loads(code_bytes)
                    exec(code, globalvars)  # yapf: disable

            except Exception as e:
                logger.exception("Failed to load plugin %s: %s", file_path, e)
                _failed_plugins[forwhat].append((str(file_path), e))


def _drop_comments(content):
    # type: (str) -> str
    if six.PY3:
        return content

    # Files opened with Pathlib handler are by default unicode encoded,
    # which is what we want. We constantly use exec to load modules or user
    # defined scripts. In python2, it is not possible to exec a unicode
    # string, which in itself defines an encoding. Minimal example
    # exec(u'# coding=utf8')
    # Thus we just drop all comment lines

    return "\n".join(x for x in content.split('\n') if not x.lstrip().startswith("#"))


def get_failed_plugins():
    # type: () -> List[Tuple[str, Exception]]
    return list(itertools.chain(*list(_failed_plugins.values())))
