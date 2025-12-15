#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from .fields import CONNECTION_MODE_FIELD
from .registration import PERMISSION_SECTION_AGENT_REGISTRATION, register

__all__ = [
    "CONNECTION_MODE_FIELD",
    "PERMISSION_SECTION_AGENT_REGISTRATION",
    "register",
]
