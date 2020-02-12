#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""This is an unsorted collection of small unrelated helper functions which are
usable in all components of Check_MK

Please try to find a better place for the things you want to put here."""

import itertools
import sys
import time
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union  # pylint: disable=unused-import

if sys.version_info[0] >= 3:
    from pathlib import Path  # pylint: disable=import-error
else:
    from pathlib2 import Path  # pylint: disable=import-error

if sys.version_info[0] >= 3:
    from inspect import getfullargspec as _getargspec  # pylint: disable=no-name-in-module
else:
    from inspect import getargspec as _getargspec  # pylint: disable=no-name-in-module

from cmk.utils.exceptions import MKGeneralException


def quote_shell_string(s):
    # type: (str) -> str
    """Quote string for use as arguments on the shell"""
    return "'" + s.replace("'", "'\"'\"'") + "'"


# TODO: Change to better name like: quote_pnp_string()
def pnp_cleanup(s):
    # type: (str) -> str
    """Quote a string (host name or service description) in PNP4Nagios format

    Because it is used as path element, this needs to be handled as "str" in Python 2 and 3
    """
    return s \
        .replace(' ', '_') \
        .replace(':', '_') \
        .replace('/', '_') \
        .replace('\\', '_')


def key_config_paths(a):
    # type: (Path) -> Tuple[Tuple[str, ...], int, Tuple[str, ...]]
    """Key function for Check_MK configuration file paths

    Helper functions that determines the sort order of the
    configuration files. The following two rules are implemented:

    1. *.mk files in the same directory will be read
       according to their lexical order.
    2. subdirectories in the same directory will be
       scanned according to their lexical order.
    3. subdirectories of a directory will always be read *after*
       the *.mk files in that directory.
    """
    pa = a.parts
    return pa[:-1], len(pa), pa


def total_size(o, handlers=None):
    #type: (Any, Optional[Dict]) -> int
    """ Returns the approximate memory footprint an object and all of its contents.

    Automatically finds the contents of the following builtin containers and
    their subclasses:  tuple, list, dict, set and frozenset.
    To search other containers, add handlers to iterate over their contents:

        handlers = {SomeContainerClass: iter,
                    OtherContainerClass: OtherContainerClass.get_elements}

    """
    if handlers is None:
        handlers = {}

    dict_handler = lambda d: itertools.chain.from_iterable(d.items())
    all_handlers = {
        tuple: iter,
        list: iter,
        dict: dict_handler,
        set: iter,
        frozenset: iter,
    }
    all_handlers.update(handlers)  # user handlers take precedence
    seen = set()  # type: Set[int]
    default_size = sys.getsizeof(0)  # estimate sizeof object without __sizeof__

    def sizeof(o):
        # type: (Any) -> int
        if id(o) in seen:  # do not double count the same object
            return 0
        seen.add(id(o))
        s = sys.getsizeof(o, default_size)

        for typ, handler in all_handlers.items():
            if isinstance(o, typ):
                s += sum(map(sizeof, handler(o)))
                break
        return s

    return sizeof(o)


# Works with Check_MK version (without tailing .cee and/or .demo)
def is_daily_build_version(v):
    # type: (str) -> bool
    return len(v) == 10 or '-' in v


# Works with Check_MK version (without tailing .cee and/or .demo)
def branch_of_daily_build(v):
    # type: (str) -> str
    if len(v) == 10:
        return "master"
    return v.split('-')[0]


def cachefile_age(path):
    # type: (Union[Path, str]) -> float
    if not isinstance(path, Path):
        path = Path(path)

    try:
        return time.time() - path.stat().st_mtime
    except Exception as e:
        raise MKGeneralException("Cannot determine age of cache file %s: %s" % (path, e))


def getfuncargs(func):
    # type: (Callable) -> List[str]
    # pylint is too dumb to see that we do NOT use the deprecated variant. :-P
    return _getargspec(func).args  # pylint: disable=deprecated-method


def make_kwargs_for(function, **kwargs):
    # type: (Callable, **Any) -> Dict[str, Any]
    return {
        arg_indicator: arg  #
        for arg_name in getfuncargs(function)
        for arg_indicator, arg in kwargs.items()
        if arg_name == arg_indicator
    }
