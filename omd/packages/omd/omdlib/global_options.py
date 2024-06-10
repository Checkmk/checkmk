#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
from typing import NamedTuple


class GlobalOptions(NamedTuple):
    verbose: bool
    force: bool
    interactive: bool
    orig_working_directory: str


def default_global_options() -> GlobalOptions:
    return GlobalOptions(
        verbose=False,
        force=False,
        interactive=False,
        orig_working_directory=_get_orig_working_directory(),
    )


def _get_orig_working_directory() -> str:
    try:
        return os.getcwd()
    except FileNotFoundError:
        return "/"
