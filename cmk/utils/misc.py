#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""This is an unsorted collection of small unrelated helper functions which are
usable in all components of Check_MK

Please try to find a better place for the things you want to put here."""

from pathlib import Path


# TODO: Change to better name like: quote_pnp_string()
def pnp_cleanup(s: str) -> str:
    """Quote a string (host name or service name) in PNP4Nagios format

    Because it is used as path element, this needs to be handled as "str" in Python 2 and 3
    """
    return s.replace(" ", "_").replace(":", "_").replace("/", "_").replace("\\", "_")


def key_config_paths(a: Path) -> tuple[tuple[str, ...], int, tuple[str, ...]]:
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
