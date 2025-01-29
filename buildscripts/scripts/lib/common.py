#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""
Common parts of buildscripts scripts
"""

import argparse
from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from os import chdir, getcwd
from pathlib import Path

import yaml


def flatten(list_to_flatten: Iterable[Iterable[str] | str]) -> Iterable[str]:
    # This is a workaround the fact that yaml cannot "extend" a predefined node which is a list:
    # https://stackoverflow.com/questions/19502522/extend-an-array-in-yaml
    return [h for elem in list_to_flatten for h in ([elem] if isinstance(elem, str) else elem)]


def strtobool(val: str | bool) -> bool:
    """Convert a string representation of truth to true (1) or false (0).
    Raises ArgumentTypeError if 'val' is anything else.

    distutils.util.strtobool() no longer part of the standard library in 3.12

    https://github.com/python/cpython/blob/v3.11.2/Lib/distutils/util.py#L308
    """
    if isinstance(val, bool):
        return val
    val = val.lower()
    if val in ("y", "yes", "t", "true", "on", "1"):
        return True
    if val in ("n", "no", "f", "false", "off", "0"):
        return False
    raise argparse.ArgumentTypeError("Boolean value expected.")


def load_editions_file(filename: str | Path) -> dict:
    with open(filename) as editions_file:
        return yaml.safe_load(editions_file)


@contextmanager
def cwd(path: str | Path) -> Iterator[None]:
    oldpwd = getcwd()
    chdir(path)
    try:
        yield
    finally:
        chdir(oldpwd)
