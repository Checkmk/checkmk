#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from typing import Final, Literal

DEFAULT_TRANSFER_STATE: Final[Mapping[str, Literal[0, 1, 2, 3]]] = {
    "aborted": 2,
    "failed": 2,
    "hard_aborted": 2,
    "queued": 0,
    "success": 0,
    "transferring": 0,
}

DEFAULT_UNHEALTHY_STATE: Final[Literal[0, 1, 2, 3]] = 2
