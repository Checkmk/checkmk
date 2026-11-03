#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""The names of MIBs and the results of compiling them

This is kept separate from the MIB compiler in cmk.ec.mib_compiler, so that users of the results
do not need to load the MIB compiler.
"""

from dataclasses import dataclass
from typing import NewType

MibName = NewType("MibName", str)
"""The name of a MIB module, e.g. "SNMPv2-SMI", which its definition starts with"""


@dataclass(frozen=True, kw_only=True)
class MibStatus:
    """The status of a MIB after a compilation, e.g. "compiled", with the error of a failed one

    Unlike the statuses of pysmi, it needs no pysmi, so only the MIB compiler does."""

    status: str
    error: str = ""
