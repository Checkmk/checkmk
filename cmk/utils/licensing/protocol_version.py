#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from typing import Literal

from cmk.ccc.version import Edition, edition

from cmk.utils.paths import omd_root


def get_licensing_protocol_version() -> Literal[
    "1.0", "1.1", "1.2", "1.3", "1.4", "1.5", "2.0", "2.1", "3.0", "3.1"
]:
    """Returns the current licensing protocol version."""
    if edition(omd_root) == Edition.CSE:
        return "3.1"
    return "3.1"
