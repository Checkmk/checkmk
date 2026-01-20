#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from enum import auto, Enum

from cmk.ccc import tty


def format_warning(msg: str) -> str:
    return f"{tty.yellow} {msg}{tty.normal}"


class ExpiryVersion(Enum):
    """Just remove the enum values corresponding to outdated (branched off) Checkmk versions,
    and the linters will point you to all obsoleted update actions."""

    NEVER = auto()
    CMK_300 = auto()
